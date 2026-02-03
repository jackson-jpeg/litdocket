"""
Case Intelligence API Endpoints

AI-powered case analysis, health scoring, predictions, and recommendations.
"""

import logging
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from app.models.case import Case
from app.models.case_intelligence import (
    CaseHealthScore,
    CasePrediction,
    JudgeProfile,
    CaseEvent,
    DiscoveryRequest,
    CaseFact,
    BriefDraft,
)
from app.models.case_recommendation import CaseRecommendation
from app.models.deadline import Deadline
from app.services.case_intelligence_service import CaseIntelligenceService
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SettlementRequest(BaseModel):
    claimed_damages: Optional[float] = None
    liability_strength: int = 50
    documentation_quality: int = 50
    opposing_resources: int = 50
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None

router = APIRouter(prefix="/case-intelligence", tags=["Case Intelligence"])


# ============================================================
# Health Score Endpoints
# ============================================================

@router.get("/cases/{case_id}/health")
async def get_case_health_score(
    case_id: str,
    recalculate: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the health score for a case.

    Returns the latest calculated health score, or calculates a new one
    if recalculate=true or no score exists.
    """
    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get latest health score
    latest_score = db.query(CaseHealthScore).filter(
        CaseHealthScore.case_id == case_id
    ).order_by(CaseHealthScore.calculated_at.desc()).first()

    if recalculate or not latest_score:
        service = CaseIntelligenceService(db)
        latest_score = await service.calculate_health_score(case_id, str(current_user.id))

    return {
        "case_id": case_id,
        "overall_score": latest_score.overall_score,
        "scores": {
            "deadline_compliance": latest_score.deadline_compliance_score,
            "document_completeness": latest_score.document_completeness_score,
            "discovery_progress": latest_score.discovery_progress_score,
            "timeline_health": latest_score.timeline_health_score,
        },
        "risk_score": latest_score.risk_score,
        "risk_factors": latest_score.risk_factors,
        "recommendations": latest_score.recommendations,
        "calculated_at": latest_score.calculated_at.isoformat() if latest_score.calculated_at else None
    }


@router.get("/dashboard")
async def get_intelligence_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the AI intelligence dashboard overview.

    Returns aggregated health scores, at-risk cases, and recommendations
    across all user cases.
    """
    try:
        # Get all active cases
        cases = db.query(Case).filter(
            Case.user_id == str(current_user.id),
            Case.status.in_(['active', 'discovery', 'trial', 'pending'])
        ).all()

        case_ids = [c.id for c in cases]

        # Get latest health scores for each case using a single query with window function
        # This avoids N+1 queries by fetching all latest scores at once
        health_scores = {}
        if case_ids:
            from sqlalchemy import func as sa_func
            from sqlalchemy.orm import aliased

            # Subquery to get the max calculated_at for each case
            latest_scores_subq = db.query(
                CaseHealthScore.case_id,
                sa_func.max(CaseHealthScore.calculated_at).label('max_calculated_at')
            ).filter(
                CaseHealthScore.case_id.in_(case_ids)
            ).group_by(CaseHealthScore.case_id).subquery()

            # Join to get the full records for the latest scores
            latest_scores = db.query(CaseHealthScore).join(
                latest_scores_subq,
                (CaseHealthScore.case_id == latest_scores_subq.c.case_id) &
                (CaseHealthScore.calculated_at == latest_scores_subq.c.max_calculated_at)
            ).all()

            health_scores = {score.case_id: score for score in latest_scores}

        # Calculate aggregates
        scores_list = list(health_scores.values())
        avg_health = sum(s.overall_score for s in scores_list) / len(scores_list) if scores_list else 0

        # Find at-risk cases (score < 60)
        at_risk_cases = [
            {
                "case_id": case_id,
                "case_title": next((c.title for c in cases if c.id == case_id), "Unknown"),
                "health_score": score.overall_score,
                "top_risk": score.risk_factors[0] if score.risk_factors else None
            }
            for case_id, score in health_scores.items()
            if score.overall_score < 60
        ]

        # Aggregate recommendations (deduplicated by action)
        all_recommendations = []
        seen_actions = set()
        for score in scores_list:
            for rec in (score.recommendations or []):
                action = rec.get('action', '')
                if action not in seen_actions:
                    seen_actions.add(action)
                    all_recommendations.append(rec)

        # Sort by priority
        all_recommendations.sort(key=lambda x: x.get('priority', 99))

        return {
            "summary": {
                "total_cases": len(cases),
                "cases_with_scores": len(scores_list),
                "average_health_score": round(avg_health, 1),
                "at_risk_count": len(at_risk_cases),
                "healthy_count": sum(1 for s in scores_list if s.overall_score >= 70)
            },
            "at_risk_cases": at_risk_cases[:10],
            "top_recommendations": all_recommendations[:10],
            "score_distribution": {
                "critical": sum(1 for s in scores_list if s.overall_score < 40),
                "warning": sum(1 for s in scores_list if 40 <= s.overall_score < 60),
                "fair": sum(1 for s in scores_list if 60 <= s.overall_score < 80),
                "good": sum(1 for s in scores_list if s.overall_score >= 80)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate intelligence dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to load intelligence dashboard. Please try again shortly."
        )


# ============================================================
# Prediction Endpoints
# ============================================================

@router.post("/cases/{case_id}/predict")
async def predict_case_outcome(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI prediction for case outcome.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    service = CaseIntelligenceService(db)
    prediction = await service.predict_case_outcome(case_id, str(current_user.id))

    return {
        "case_id": case_id,
        "prediction_type": prediction.prediction_type,
        "predicted_outcome": prediction.predicted_value,
        "confidence": float(prediction.confidence) if prediction.confidence else None,
        "settlement_range": {
            "low": prediction.lower_bound,
            "high": prediction.upper_bound
        } if prediction.lower_bound else None,
        "influencing_factors": prediction.influencing_factors,
        "predicted_at": prediction.predicted_at.isoformat() if prediction.predicted_at else None
    }


@router.get("/cases/{case_id}/predictions")
async def get_case_predictions(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all predictions for a case.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    predictions = db.query(CasePrediction).filter(
        CasePrediction.case_id == case_id
    ).order_by(CasePrediction.predicted_at.desc()).all()

    return [
        {
            "id": p.id,
            "type": p.prediction_type,
            "value": p.predicted_value,
            "confidence": float(p.confidence) if p.confidence else None,
            "range": {"low": p.lower_bound, "high": p.upper_bound} if p.lower_bound else None,
            "factors": p.influencing_factors,
            "predicted_at": p.predicted_at.isoformat() if p.predicted_at else None
        }
        for p in predictions
    ]


# ============================================================
# Timeline Endpoints
# ============================================================

@router.get("/cases/{case_id}/timeline")
async def get_case_timeline(
    case_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    event_types: Optional[str] = None,  # Comma-separated
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get case timeline events.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    service = CaseIntelligenceService(db)
    types_list = event_types.split(',') if event_types else None

    events = service.get_case_timeline(
        case_id,
        str(current_user.id),
        datetime.combine(start_date, datetime.min.time()) if start_date else None,
        datetime.combine(end_date, datetime.max.time()) if end_date else None,
        types_list
    )

    return [
        {
            "id": e.id,
            "type": e.event_type,
            "subtype": e.event_subtype,
            "title": e.title,
            "description": e.description,
            "date": e.event_date.isoformat() if e.event_date else None,
            "end_date": e.end_date.isoformat() if e.end_date else None,
            "status": e.status,
            "priority": e.priority,
            "location": e.location,
            "participants": e.participants
        }
        for e in events
    ]


@router.post("/cases/{case_id}/timeline/sync")
async def sync_timeline_from_deadlines(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sync case timeline from existing deadlines.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    service = CaseIntelligenceService(db)
    created_count = service.sync_timeline_from_deadlines(case_id, str(current_user.id))

    return {
        "case_id": case_id,
        "events_created": created_count
    }


@router.post("/cases/{case_id}/timeline/events")
async def create_case_event(
    case_id: str,
    event_type: str,
    title: str,
    event_date: datetime,
    event_subtype: Optional[str] = None,
    description: Optional[str] = None,
    end_date: Optional[datetime] = None,
    priority: str = "standard",
    location: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new case event.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    import uuid
    event = CaseEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        user_id=str(current_user.id),
        event_type=event_type,
        event_subtype=event_subtype,
        title=title,
        description=description,
        event_date=event_date,
        end_date=end_date,
        priority=priority,
        location=location
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "id": event.id,
        "type": event.event_type,
        "title": event.title,
        "date": event.event_date.isoformat()
    }


# ============================================================
# Discovery Endpoints
# ============================================================

@router.get("/cases/{case_id}/discovery")
async def get_case_discovery(
    case_id: str,
    direction: Optional[str] = None,  # incoming, outgoing
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get discovery requests for a case.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    query = db.query(DiscoveryRequest).filter(
        DiscoveryRequest.case_id == case_id,
        DiscoveryRequest.user_id == str(current_user.id)
    )

    if direction:
        query = query.filter(DiscoveryRequest.direction == direction)
    if status:
        query = query.filter(DiscoveryRequest.status == status)

    requests = query.order_by(DiscoveryRequest.response_due_date).all()

    return [
        {
            "id": r.id,
            "type": r.request_type,
            "number": r.request_number,
            "direction": r.direction,
            "from_party": r.from_party,
            "to_party": r.to_party,
            "title": r.title,
            "served_date": r.served_date.isoformat() if r.served_date else None,
            "response_due_date": r.response_due_date.isoformat() if r.response_due_date else None,
            "response_received_date": r.response_received_date.isoformat() if r.response_received_date else None,
            "status": r.status,
            "items_count": len(r.items) if r.items else 0
        }
        for r in requests
    ]


@router.post("/cases/{case_id}/discovery")
async def create_discovery_request(
    case_id: str,
    request_type: str,
    direction: str,
    title: str,
    from_party: Optional[str] = None,
    to_party: Optional[str] = None,
    served_date: Optional[date] = None,
    response_due_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new discovery request.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get next request number
    existing_count = db.query(DiscoveryRequest).filter(
        DiscoveryRequest.case_id == case_id,
        DiscoveryRequest.request_type == request_type,
        DiscoveryRequest.direction == direction
    ).count()

    import uuid
    request = DiscoveryRequest(
        id=str(uuid.uuid4()),
        case_id=case_id,
        user_id=str(current_user.id),
        request_type=request_type,
        request_number=existing_count + 1,
        direction=direction,
        title=title,
        from_party=from_party,
        to_party=to_party,
        served_date=served_date,
        response_due_date=response_due_date
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return {
        "id": request.id,
        "type": request.request_type,
        "number": request.request_number,
        "title": request.title
    }


# ============================================================
# Facts Endpoints
# ============================================================

@router.get("/cases/{case_id}/facts")
async def get_case_facts(
    case_id: str,
    fact_type: Optional[str] = None,
    importance: Optional[str] = None,
    verified_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get extracted facts for a case.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    query = db.query(CaseFact).filter(
        CaseFact.case_id == case_id,
        CaseFact.user_id == str(current_user.id)
    )

    if fact_type:
        query = query.filter(CaseFact.fact_type == fact_type)
    if importance:
        query = query.filter(CaseFact.importance == importance)
    if verified_only:
        query = query.filter(CaseFact.verified == True)

    facts = query.order_by(CaseFact.extracted_at.desc()).all()

    return [
        {
            "id": f.id,
            "type": f.fact_type,
            "text": f.fact_text,
            "normalized_value": f.normalized_value,
            "importance": f.importance,
            "is_disputed": f.is_disputed,
            "confidence": float(f.extraction_confidence) if f.extraction_confidence else None,
            "verified": f.verified,
            "source_document_id": f.source_document_id,
            "source_excerpt": f.source_excerpt
        }
        for f in facts
    ]


@router.post("/cases/{case_id}/facts/extract")
async def extract_facts_from_document(
    case_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Extract facts from a document using AI.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    service = CaseIntelligenceService(db)
    facts = await service.extract_case_facts(case_id, str(current_user.id), document_id)

    return {
        "case_id": case_id,
        "document_id": document_id,
        "facts_extracted": len(facts),
        "facts": [
            {
                "id": f.id,
                "type": f.fact_type,
                "text": f.fact_text,
                "confidence": float(f.extraction_confidence) if f.extraction_confidence else None
            }
            for f in facts
        ]
    }


# ============================================================
# Judge Analytics Endpoints
# ============================================================

@router.get("/judges")
async def search_judges(
    query: str,
    jurisdiction_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search for judges.
    """
    q = db.query(JudgeProfile).filter(
        JudgeProfile.name.ilike(f"%{query}%")
    )

    if jurisdiction_id:
        q = q.filter(JudgeProfile.jurisdiction_id == jurisdiction_id)

    judges = q.limit(20).all()

    return [
        {
            "id": j.id,
            "name": j.name,
            "court": j.court,
            "avg_ruling_time_days": j.avg_ruling_time_days,
            "motion_stats": j.motion_stats
        }
        for j in judges
    ]


@router.get("/judges/{judge_id}")
async def get_judge_profile(
    judge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed judge profile with analytics.
    """
    judge = db.query(JudgeProfile).filter(JudgeProfile.id == judge_id).first()

    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")

    return {
        "id": judge.id,
        "name": judge.name,
        "court": judge.court,
        "chambers_info": judge.chambers_info,
        "statistics": {
            "avg_ruling_time_days": judge.avg_ruling_time_days,
            "avg_case_duration_months": judge.avg_case_duration_months,
            "motion_stats": judge.motion_stats,
            "case_type_experience": judge.case_type_experience
        },
        "preferences": judge.preferences,
        "notable_rulings": judge.notable_rulings,
        "last_updated": judge.last_updated.isoformat() if judge.last_updated else None
    }


@router.post("/cases/{case_id}/judge")
async def set_case_judge(
    case_id: str,
    judge_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Set or update the judge for a case and get insights.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Update case judge
    case.judge = judge_name
    db.commit()

    # Get or create judge profile
    service = CaseIntelligenceService(db)
    profile = await service.get_judge_insights(judge_name)

    return {
        "case_id": case_id,
        "judge_name": judge_name,
        "judge_profile_id": profile.id if profile else None,
        "insights": {
            "avg_ruling_time": profile.avg_ruling_time_days if profile else None,
            "preferences": profile.preferences if profile else None,
            "motion_stats": profile.motion_stats if profile else None
        }
    }


# ============================================================
# Brief Drafting Endpoints
# ============================================================

@router.get("/cases/{case_id}/briefs")
async def get_case_briefs(
    case_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get brief drafts for a case.
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    query = db.query(BriefDraft).filter(
        BriefDraft.case_id == case_id,
        BriefDraft.user_id == str(current_user.id)
    )

    if status:
        query = query.filter(BriefDraft.status == status)

    briefs = query.order_by(BriefDraft.created_at.desc()).all()

    return [
        {
            "id": b.id,
            "document_type": b.document_type,
            "title": b.title,
            "status": b.status,
            "version": b.version,
            "sections_count": len(b.sections) if b.sections else 0,
            "citations_count": len(b.citations) if b.citations else 0,
            "created_at": b.created_at.isoformat() if b.created_at else None
        }
        for b in briefs
    ]


@router.post("/cases/{case_id}/briefs/generate")
async def generate_brief_draft(
    case_id: str,
    document_type: str,
    title: str,
    instructions: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate an AI-assisted brief draft.
    """
    from app.services.ai_service import AIService
    import uuid
    import json

    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get case facts for context
    facts = db.query(CaseFact).filter(
        CaseFact.case_id == case_id
    ).limit(30).all()

    # Build generation prompt
    context = {
        "case_type": case.case_type,
        "jurisdiction": case.jurisdiction,
        "parties": case.parties,
        "facts": [{"type": f.fact_type, "text": f.fact_text} for f in facts]
    }

    ai_service = AIService()
    prompt = f"""Draft a {document_type} for the following case:

Case Type: {case.case_type}
Jurisdiction: {case.jurisdiction}
Parties: {json.dumps(case.parties) if case.parties else 'Not specified'}

Key Facts:
{json.dumps([f['text'] for f in context['facts'][:15]], indent=2)}

Additional Instructions: {instructions or 'None provided'}

Please draft a professional legal {document_type} with the following sections:
1. INTRODUCTION
2. STATEMENT OF FACTS
3. LEGAL ARGUMENT
4. CONCLUSION

Format your response as JSON:
{{
    "sections": [
        {{"heading": "INTRODUCTION", "content": "..."}},
        {{"heading": "STATEMENT OF FACTS", "content": "..."}},
        {{"heading": "LEGAL ARGUMENT", "content": "..."}},
        {{"heading": "CONCLUSION", "content": "..."}}
    ],
    "citations": [
        {{"citation": "Case Name, Citation", "quote": "Relevant quote"}}
    ]
}}"""

    try:
        response = await ai_service.analyze_with_claude(prompt)

        # Parse response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            draft_data = json.loads(response[json_start:json_end])
        else:
            draft_data = {
                "sections": [{"heading": "DRAFT", "content": response}],
                "citations": []
            }

        # Create brief draft
        brief = BriefDraft(
            id=str(uuid.uuid4()),
            case_id=case_id,
            user_id=str(current_user.id),
            document_type=document_type,
            title=title,
            sections=draft_data.get("sections", []),
            citations=draft_data.get("citations", []),
            generation_prompt=prompt,
            generation_context=context,
            status="draft"
        )

        db.add(brief)
        db.commit()
        db.refresh(brief)

        return {
            "id": brief.id,
            "title": brief.title,
            "document_type": brief.document_type,
            "sections": brief.sections,
            "citations": brief.citations,
            "status": brief.status
        }

    except Exception as e:
        logger.error(f"Brief generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Settlement Calculator Endpoints
# ============================================================

@router.post("/cases/{case_id}/settlement/calculate")
async def calculate_settlement(
    case_id: str,
    request: SettlementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate AI-powered settlement recommendation based on case factors.
    """
    from app.services.ai_service import AIService
    import json

    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get case facts and health score for context
    facts = db.query(CaseFact).filter(CaseFact.case_id == case_id).limit(20).all()
    health_score = db.query(CaseHealthScore).filter(
        CaseHealthScore.case_id == case_id
    ).order_by(CaseHealthScore.calculated_at.desc()).first()

    # Build context
    context = {
        "case_type": request.case_type or case.case_type,
        "jurisdiction": request.jurisdiction or case.jurisdiction,
        "claimed_damages": request.claimed_damages,
        "liability_strength": request.liability_strength,
        "documentation_quality": request.documentation_quality,
        "opposing_resources": request.opposing_resources,
        "facts": [{"type": f.fact_type, "text": f.fact_text} for f in facts[:15]],
        "health_score": health_score.overall_score if health_score else None
    }

    prompt = f"""Analyze this litigation case and provide settlement recommendations.

Case Details:
- Type: {context['case_type'] or 'Unknown'}
- Jurisdiction: {context['jurisdiction'] or 'Unknown'}
- Claimed Damages: ${context['claimed_damages'] or 'Not specified'}
- Liability Strength: {context['liability_strength']}%
- Documentation Quality: {context['documentation_quality']}%
- Opposing Party Resources: {context['opposing_resources']}%
- Case Health Score: {context['health_score'] or 'Not calculated'}

Key Facts:
{json.dumps([f['text'] for f in context['facts'][:10]], indent=2)}

Provide a comprehensive settlement analysis in JSON format:
{{
    "recommended_range": {{
        "low": 75000,
        "mid": 125000,
        "high": 200000
    }},
    "confidence": 0.75,
    "factors": [
        {{
            "name": "Strong Documentation",
            "impact": "positive|negative|neutral",
            "weight": 0.25,
            "description": "Well-documented case with clear evidence"
        }}
    ],
    "comparable_settlements": [
        {{
            "amount": 150000,
            "case_type": "Similar case type",
            "jurisdiction": "Same jurisdiction",
            "outcome": "Settled before trial"
        }}
    ],
    "negotiation_strategy": {{
        "initial_demand": 250000,
        "walkaway_point": 50000,
        "key_leverage_points": ["Strong evidence", "Clear liability"],
        "potential_concessions": ["Payment timeline", "Non-monetary terms"]
    }},
    "risk_assessment": {{
        "trial_win_probability": 0.65,
        "expected_trial_verdict": 175000,
        "litigation_costs_estimate": 50000,
        "time_to_trial_months": 18
    }},
    "recommendation": "Based on the case strength and comparable settlements, recommend pursuing settlement in the $100,000-$150,000 range."
}}"""

    try:
        ai_service = AIService()
        response = await ai_service.analyze_with_claude(prompt)

        # Parse response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            settlement_data = json.loads(response[json_start:json_end])
        else:
            # Provide default structure if parsing fails
            base_amount = request.claimed_damages or 100000
            settlement_data = {
                "recommended_range": {
                    "low": int(base_amount * 0.3),
                    "mid": int(base_amount * 0.5),
                    "high": int(base_amount * 0.75)
                },
                "confidence": 0.5,
                "factors": [],
                "comparable_settlements": [],
                "negotiation_strategy": {
                    "initial_demand": int(base_amount * 0.8),
                    "walkaway_point": int(base_amount * 0.25),
                    "key_leverage_points": [],
                    "potential_concessions": []
                },
                "risk_assessment": {
                    "trial_win_probability": 0.5,
                    "expected_trial_verdict": int(base_amount * 0.6),
                    "litigation_costs_estimate": 25000,
                    "time_to_trial_months": 12
                },
                "recommendation": "Insufficient data for detailed analysis. Consider gathering more case information."
            }

        return settlement_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse settlement analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse settlement analysis")
    except Exception as e:
        logger.error(f"Settlement calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Action Plan Endpoints (Enhanced Recommendations)
# ============================================================

@router.get("/cases/{case_id}/action-plan")
async def get_case_action_plan(
    case_id: str,
    include_completed: bool = False,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the enhanced action plan for a case.

    Returns prioritized, actionable recommendations with full context
    including rule citations, consequences, and suggested tools.
    """
    import uuid
    from datetime import timedelta

    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get existing recommendations
    query = db.query(CaseRecommendation).filter(
        CaseRecommendation.case_id == case_id,
        CaseRecommendation.user_id == str(current_user.id)
    )

    if not include_completed:
        query = query.filter(CaseRecommendation.status.in_(['pending', 'in_progress']))

    existing_recs = query.order_by(
        CaseRecommendation.priority.asc(),
        CaseRecommendation.urgency_level.desc()
    ).limit(limit).all()

    # If we have enough recent recommendations, return them
    if existing_recs and len(existing_recs) >= 3:
        # Check if any are stale (> 1 hour old)
        recent_enough = all(
            r.created_at and (datetime.utcnow() - r.created_at).total_seconds() < 3600
            for r in existing_recs[:5]
        )
        if recent_enough:
            return _format_action_plan(case_id, existing_recs)

    # Generate fresh recommendations
    now = datetime.utcnow()
    new_recommendations = []
    priority = 1

    # =====================================================================
    # RULE 1: Fatal/Critical Deadlines Within 7 Days
    # =====================================================================
    urgent_deadlines = db.query(Deadline).filter(
        Deadline.case_id == case_id,
        Deadline.user_id == str(current_user.id),
        Deadline.deadline_date.between(now.date(), now.date() + timedelta(days=7)),
        Deadline.priority.in_(['fatal', 'critical']),
        Deadline.status.notin_(['completed', 'cancelled'])
    ).order_by(Deadline.deadline_date.asc()).all()

    for deadline in urgent_deadlines:
        days_until = (deadline.deadline_date - now.date()).days if deadline.deadline_date else None

        # Check if recommendation already exists
        existing = db.query(CaseRecommendation).filter(
            CaseRecommendation.case_id == case_id,
            CaseRecommendation.triggered_by_deadline_id == deadline.id,
            CaseRecommendation.status == 'pending'
        ).first()

        if existing:
            continue

        consequence = "Case dismissal or default judgment" if deadline.priority == 'fatal' else "Court sanctions or adverse ruling"

        rec = CaseRecommendation(
            id=str(uuid.uuid4()),
            case_id=case_id,
            user_id=str(current_user.id),
            priority=priority,
            action=f"Complete '{deadline.title}' - {days_until} day(s) remaining",
            reasoning=f"This is a {deadline.priority} deadline that requires immediate attention.",
            category="deadlines",
            triggered_by_deadline_id=deadline.id,
            rule_citations=[deadline.rule_citation] if deadline.rule_citation else [],
            consequence_if_ignored=consequence,
            urgency_level="critical" if deadline.priority == 'fatal' else "high",
            days_until_consequence=days_until,
            suggested_tools=[
                {"tool": "deadline-calculator", "action": "Verify deadline calculation"},
                {"tool": "ai-assistant", "action": f"Draft {deadline.title}"}
            ],
            suggested_document_types=[deadline.title] if 'response' in deadline.title.lower() or 'answer' in deadline.title.lower() else [],
            expires_at=deadline.deadline_date,
            status='pending'
        )
        db.add(rec)
        new_recommendations.append(rec)
        priority += 1

    # =====================================================================
    # RULE 2: Overdue Deadlines
    # =====================================================================
    overdue_deadlines = db.query(Deadline).filter(
        Deadline.case_id == case_id,
        Deadline.user_id == str(current_user.id),
        Deadline.deadline_date < now.date(),
        Deadline.status.notin_(['completed', 'cancelled'])
    ).all()

    if overdue_deadlines:
        fatal_overdue = [d for d in overdue_deadlines if d.priority == 'fatal']

        if fatal_overdue:
            # Check for existing
            existing = db.query(CaseRecommendation).filter(
                CaseRecommendation.case_id == case_id,
                CaseRecommendation.category == "risk",
                CaseRecommendation.action.like("%URGENT: Fatal deadline%"),
                CaseRecommendation.status == 'pending'
            ).first()

            if not existing:
                rec = CaseRecommendation(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    user_id=str(current_user.id),
                    priority=0,  # Highest priority
                    action=f"URGENT: Fatal deadline '{fatal_overdue[0].title}' is OVERDUE",
                    reasoning="A fatal deadline has passed. Immediate action required to prevent case dismissal or default.",
                    category="risk",
                    triggered_by_deadline_id=fatal_overdue[0].id,
                    rule_citations=[fatal_overdue[0].rule_citation] if fatal_overdue[0].rule_citation else [],
                    consequence_if_ignored="Case dismissal, default judgment, or malpractice exposure",
                    urgency_level="critical",
                    days_until_consequence=0,
                    suggested_tools=[
                        {"tool": "ai-assistant", "action": "Draft motion for extension or relief from default"}
                    ],
                    suggested_document_types=["Motion for Extension of Time", "Motion to Set Aside Default"],
                    status='pending'
                )
                db.add(rec)
                new_recommendations.append(rec)

    # =====================================================================
    # RULE 3: Pending Discovery Responses Due Soon
    # =====================================================================
    pending_discovery = db.query(DiscoveryRequest).filter(
        DiscoveryRequest.case_id == case_id,
        DiscoveryRequest.user_id == str(current_user.id),
        DiscoveryRequest.direction == "incoming",
        DiscoveryRequest.status == "pending",
        DiscoveryRequest.response_due_date < now.date() + timedelta(days=14)
    ).all()

    if pending_discovery:
        existing = db.query(CaseRecommendation).filter(
            CaseRecommendation.case_id == case_id,
            CaseRecommendation.category == "discovery",
            CaseRecommendation.status == 'pending'
        ).first()

        if not existing:
            rec = CaseRecommendation(
                id=str(uuid.uuid4()),
                case_id=case_id,
                user_id=str(current_user.id),
                priority=priority,
                action=f"Prepare {len(pending_discovery)} discovery response(s) due within 14 days",
                reasoning="Discovery responses require timely completion to avoid sanctions.",
                category="discovery",
                rule_citations=["Fla. R. Civ. P. 1.340", "Fla. R. Civ. P. 1.350"],
                consequence_if_ignored="Motion to compel, sanctions, or adverse inference",
                urgency_level="high",
                days_until_consequence=14,
                suggested_tools=[
                    {"tool": "ai-assistant", "action": "Draft discovery responses"},
                    {"tool": "document-analyzer", "action": "Review relevant documents"}
                ],
                status='pending'
            )
            db.add(rec)
            new_recommendations.append(rec)
            priority += 1

    # =====================================================================
    # RULE 4: Case Health Recommendations
    # =====================================================================
    latest_health = db.query(CaseHealthScore).filter(
        CaseHealthScore.case_id == case_id
    ).order_by(CaseHealthScore.calculated_at.desc()).first()

    if latest_health:
        if latest_health.deadline_compliance_score and latest_health.deadline_compliance_score < 70:
            existing = db.query(CaseRecommendation).filter(
                CaseRecommendation.case_id == case_id,
                CaseRecommendation.action.like("%deadline compliance%"),
                CaseRecommendation.status == 'pending'
            ).first()

            if not existing:
                rec = CaseRecommendation(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    user_id=str(current_user.id),
                    priority=priority,
                    action="Review and improve deadline compliance",
                    reasoning=f"Current deadline compliance score is {latest_health.deadline_compliance_score}%. Improving compliance reduces risk of adverse rulings.",
                    category="compliance",
                    urgency_level="medium",
                    suggested_tools=[
                        {"tool": "calendar", "action": "Review upcoming deadlines"},
                        {"tool": "deadline-calculator", "action": "Verify all deadline calculations"}
                    ],
                    status='pending'
                )
                db.add(rec)
                new_recommendations.append(rec)
                priority += 1

        if latest_health.document_completeness_score and latest_health.document_completeness_score < 50:
            existing = db.query(CaseRecommendation).filter(
                CaseRecommendation.case_id == case_id,
                CaseRecommendation.action.like("%Upload%document%"),
                CaseRecommendation.status == 'pending'
            ).first()

            if not existing:
                rec = CaseRecommendation(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    user_id=str(current_user.id),
                    priority=priority,
                    action="Upload key case documents",
                    reasoning=f"Document completeness score is {latest_health.document_completeness_score}%. Complete documentation enables better case management.",
                    category="documents",
                    urgency_level="low",
                    suggested_document_types=["Complaint", "Answer", "Discovery Requests", "Discovery Responses"],
                    status='pending'
                )
                db.add(rec)
                new_recommendations.append(rec)
                priority += 1

    # Commit new recommendations
    try:
        db.commit()
        for r in new_recommendations:
            db.refresh(r)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save recommendations: {e}")

    # Fetch all current recommendations
    all_recs = db.query(CaseRecommendation).filter(
        CaseRecommendation.case_id == case_id,
        CaseRecommendation.user_id == str(current_user.id),
        CaseRecommendation.status.in_(['pending', 'in_progress'])
    ).order_by(
        CaseRecommendation.priority.asc()
    ).limit(limit).all()

    return _format_action_plan(case_id, all_recs)


def _format_action_plan(case_id: str, recommendations: List[CaseRecommendation]) -> dict:
    """Format recommendations into an action plan response."""
    # Group by urgency
    critical = [r for r in recommendations if r.urgency_level == 'critical']
    high = [r for r in recommendations if r.urgency_level == 'high']
    medium = [r for r in recommendations if r.urgency_level == 'medium']
    low = [r for r in recommendations if r.urgency_level == 'low']

    return {
        "case_id": case_id,
        "total_recommendations": len(recommendations),
        "by_urgency": {
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "low": len(low)
        },
        "recommendations": [r.to_dict() for r in recommendations],
        "grouped": {
            "critical": [r.to_dict() for r in critical],
            "high": [r.to_dict() for r in high],
            "medium": [r.to_dict() for r in medium],
            "low": [r.to_dict() for r in low]
        }
    }


@router.patch("/recommendations/{recommendation_id}")
async def update_recommendation(
    recommendation_id: str,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a recommendation's status.

    Request body:
    {
        "status": "completed" | "dismissed" | "in_progress",
        "dismissed_reason": "Optional reason for dismissal"
    }
    """
    rec = db.query(CaseRecommendation).filter(
        CaseRecommendation.id == recommendation_id,
        CaseRecommendation.user_id == str(current_user.id)
    ).first()

    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    new_status = update_data.get('status')
    if new_status:
        if new_status not in ['pending', 'in_progress', 'completed', 'dismissed']:
            raise HTTPException(status_code=400, detail="Invalid status")

        rec.status = new_status

        if new_status == 'completed':
            rec.completed_at = datetime.utcnow()
        elif new_status == 'dismissed':
            rec.dismissed_at = datetime.utcnow()
            rec.dismissed_reason = update_data.get('dismissed_reason')

    try:
        db.commit()
        db.refresh(rec)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update recommendation: {e}")
        raise HTTPException(status_code=500, detail="Failed to update recommendation")

    return {
        "success": True,
        "recommendation": rec.to_dict(),
        "message": f"Recommendation marked as {new_status}"
    }


@router.delete("/recommendations/{recommendation_id}")
async def delete_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a recommendation.
    """
    rec = db.query(CaseRecommendation).filter(
        CaseRecommendation.id == recommendation_id,
        CaseRecommendation.user_id == str(current_user.id)
    ).first()

    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    try:
        db.delete(rec)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete recommendation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete recommendation")

    return {"success": True, "message": "Recommendation deleted"}
