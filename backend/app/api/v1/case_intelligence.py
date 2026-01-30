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
from app.services.case_intelligence_service import CaseIntelligenceService

logger = logging.getLogger(__name__)

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
    # Get all active cases
    cases = db.query(Case).filter(
        Case.user_id == str(current_user.id),
        Case.status.in_(['active', 'discovery', 'trial', 'pending'])
    ).all()

    case_ids = [c.id for c in cases]

    # Get latest health scores for each case
    health_scores = {}
    for case_id in case_ids:
        score = db.query(CaseHealthScore).filter(
            CaseHealthScore.case_id == case_id
        ).order_by(CaseHealthScore.calculated_at.desc()).first()
        if score:
            health_scores[case_id] = score

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
