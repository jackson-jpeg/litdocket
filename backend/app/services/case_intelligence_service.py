"""
Case Intelligence Service

AI-powered case analysis, health scoring, predictions, and recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.case import Case
from app.models.deadline import Deadline
from app.models.document import Document
from app.models.case_intelligence import (
    CaseHealthScore,
    CasePrediction,
    JudgeProfile,
    CaseEvent,
    CaseFact,
    DiscoveryRequest,
)
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class CaseIntelligenceService:
    """
    Provides AI-powered case intelligence including:
    - Health scoring
    - Outcome predictions
    - Risk assessment
    - Strategic recommendations
    - Fact extraction
    """

    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()

    async def calculate_health_score(
        self,
        case_id: str,
        user_id: str
    ) -> CaseHealthScore:
        """
        Calculate comprehensive health score for a case.
        """
        case = self.db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == user_id
        ).first()

        if not case:
            raise ValueError("Case not found")

        # Calculate component scores
        deadline_score = await self._calculate_deadline_compliance_score(case_id, user_id)
        document_score = await self._calculate_document_completeness_score(case_id, user_id)
        discovery_score = await self._calculate_discovery_progress_score(case_id, user_id)
        timeline_score = await self._calculate_timeline_health_score(case_id, user_id)

        # Calculate risk factors
        risk_factors = await self._identify_risk_factors(case_id, user_id)

        # Calculate overall score (weighted average)
        weights = {
            'deadline': 0.35,
            'document': 0.20,
            'discovery': 0.25,
            'timeline': 0.20
        }

        overall_score = int(
            deadline_score * weights['deadline'] +
            document_score * weights['document'] +
            discovery_score * weights['discovery'] +
            timeline_score * weights['timeline']
        )

        # Generate recommendations
        recommendations = await self._generate_recommendations(
            case_id, user_id,
            deadline_score, document_score, discovery_score, timeline_score,
            risk_factors
        )

        # Risk score (inverse of health)
        risk_score = 100 - overall_score

        # Create or update health score record
        health_score = CaseHealthScore(
            id=str(uuid.uuid4()),
            case_id=case_id,
            user_id=user_id,
            overall_score=overall_score,
            deadline_compliance_score=deadline_score,
            document_completeness_score=document_score,
            discovery_progress_score=discovery_score,
            timeline_health_score=timeline_score,
            risk_score=risk_score,
            risk_factors=risk_factors,
            recommendations=recommendations,
            analysis_model="claude-sonnet-4-20250514",
            analysis_confidence=Decimal("0.85")
        )

        self.db.add(health_score)
        self.db.commit()

        return health_score

    async def _calculate_deadline_compliance_score(
        self,
        case_id: str,
        user_id: str
    ) -> int:
        """Calculate score based on deadline compliance."""
        now = datetime.utcnow()

        # Get all deadlines for the case
        deadlines = self.db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.user_id == user_id
        ).all()

        if not deadlines:
            return 100  # No deadlines = perfect compliance

        total = len(deadlines)
        completed_on_time = 0
        missed = 0
        upcoming_at_risk = 0

        for deadline in deadlines:
            if deadline.status == 'completed':
                # Check if it was completed on time
                if deadline.completed_at and deadline.due_date:
                    if deadline.completed_at.date() <= deadline.due_date:
                        completed_on_time += 1
                    else:
                        missed += 1
                else:
                    completed_on_time += 1
            elif deadline.status == 'overdue' or (deadline.due_date and deadline.due_date < now.date()):
                missed += 1
            elif deadline.due_date:
                # Check if upcoming deadline is at risk (within 3 days, not started)
                days_until = (deadline.due_date - now.date()).days
                if days_until <= 3 and deadline.status in ['pending', 'not_started']:
                    upcoming_at_risk += 1

        # Calculate score
        if total == 0:
            return 100

        compliance_rate = (total - missed) / total
        at_risk_penalty = (upcoming_at_risk / total) * 0.2  # 20% max penalty for at-risk

        score = int((compliance_rate - at_risk_penalty) * 100)
        return max(0, min(100, score))

    async def _calculate_document_completeness_score(
        self,
        case_id: str,
        user_id: str
    ) -> int:
        """Calculate score based on document completeness."""
        documents = self.db.query(Document).filter(
            Document.case_id == case_id,
            Document.user_id == user_id
        ).all()

        # Required document types for a well-prepared case
        required_types = [
            'complaint', 'answer', 'discovery_request', 'discovery_response'
        ]

        present_types = set()
        for doc in documents:
            doc_type = doc.document_type or ''
            present_types.add(doc_type.lower())

        # Calculate based on document count and types
        type_score = len(present_types.intersection(set(required_types))) / len(required_types) * 50
        count_score = min(len(documents) / 10, 1) * 50  # Up to 10 docs = full score

        return int(type_score + count_score)

    async def _calculate_discovery_progress_score(
        self,
        case_id: str,
        user_id: str
    ) -> int:
        """Calculate score based on discovery progress."""
        discovery_requests = self.db.query(DiscoveryRequest).filter(
            DiscoveryRequest.case_id == case_id,
            DiscoveryRequest.user_id == user_id
        ).all()

        if not discovery_requests:
            return 75  # No discovery tracked = neutral score

        total = len(discovery_requests)
        responded = sum(1 for r in discovery_requests if r.status in ['responded', 'resolved'])
        pending = sum(1 for r in discovery_requests if r.status == 'pending')
        overdue = sum(1 for r in discovery_requests
                     if r.response_due_date and r.response_due_date < datetime.utcnow().date()
                     and r.status == 'pending')

        if total == 0:
            return 75

        response_rate = responded / total
        overdue_penalty = (overdue / total) * 0.3

        score = int((response_rate - overdue_penalty) * 100)
        return max(0, min(100, score))

    async def _calculate_timeline_health_score(
        self,
        case_id: str,
        user_id: str
    ) -> int:
        """Calculate score based on case timeline health."""
        case = self.db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == user_id
        ).first()

        if not case:
            return 50

        # Check case age and activity
        case_age_days = (datetime.utcnow() - case.created_at).days if case.created_at else 0

        # Get recent activity
        recent_events = self.db.query(CaseEvent).filter(
            CaseEvent.case_id == case_id,
            CaseEvent.event_date >= datetime.utcnow() - timedelta(days=30)
        ).count()

        # Cases should have regular activity
        if case_age_days < 30:
            activity_score = 100  # New case
        elif recent_events >= 3:
            activity_score = 100  # Active case
        elif recent_events >= 1:
            activity_score = 75  # Some activity
        else:
            activity_score = 50  # Stale case

        return activity_score

    async def _identify_risk_factors(
        self,
        case_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Identify risk factors for the case."""
        risk_factors = []
        now = datetime.utcnow()

        # Check for overdue deadlines
        overdue_deadlines = self.db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.user_id == user_id,
            Deadline.due_date < now.date(),
            Deadline.status.notin_(['completed', 'cancelled'])
        ).all()

        if overdue_deadlines:
            risk_factors.append({
                "type": "overdue_deadlines",
                "severity": "critical" if any(d.priority == 'fatal' for d in overdue_deadlines) else "high",
                "description": f"{len(overdue_deadlines)} overdue deadline(s)",
                "details": [{"id": d.id, "title": d.title, "due_date": d.due_date.isoformat()} for d in overdue_deadlines[:5]]
            })

        # Check for upcoming critical deadlines
        critical_upcoming = self.db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.user_id == user_id,
            Deadline.due_date.between(now.date(), now.date() + timedelta(days=7)),
            Deadline.priority.in_(['fatal', 'critical']),
            Deadline.status.notin_(['completed', 'cancelled'])
        ).all()

        if critical_upcoming:
            risk_factors.append({
                "type": "critical_deadlines_approaching",
                "severity": "high",
                "description": f"{len(critical_upcoming)} critical deadline(s) within 7 days",
                "details": [{"id": d.id, "title": d.title, "due_date": d.due_date.isoformat()} for d in critical_upcoming]
            })

        # Check for discovery gaps
        pending_discovery = self.db.query(DiscoveryRequest).filter(
            DiscoveryRequest.case_id == case_id,
            DiscoveryRequest.direction == "incoming",
            DiscoveryRequest.status == "pending",
            DiscoveryRequest.response_due_date < now.date() + timedelta(days=14)
        ).count()

        if pending_discovery > 0:
            risk_factors.append({
                "type": "pending_discovery_responses",
                "severity": "medium",
                "description": f"{pending_discovery} discovery response(s) due soon"
            })

        return risk_factors

    async def _generate_recommendations(
        self,
        case_id: str,
        user_id: str,
        deadline_score: int,
        document_score: int,
        discovery_score: int,
        timeline_score: int,
        risk_factors: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        priority = 1

        # Deadline-based recommendations
        if deadline_score < 70:
            recommendations.append({
                "priority": priority,
                "action": "Review and address overdue or at-risk deadlines immediately",
                "reasoning": "Deadline compliance is critical for case success",
                "category": "deadlines"
            })
            priority += 1

        # Document-based recommendations
        if document_score < 50:
            recommendations.append({
                "priority": priority,
                "action": "Upload and organize key case documents",
                "reasoning": "Complete documentation enables better case management",
                "category": "documents"
            })
            priority += 1

        # Discovery-based recommendations
        if discovery_score < 60:
            recommendations.append({
                "priority": priority,
                "action": "Review discovery status and prepare responses",
                "reasoning": "Timely discovery compliance prevents sanctions",
                "category": "discovery"
            })
            priority += 1

        # Risk factor-based recommendations
        for risk in risk_factors:
            if risk["severity"] == "critical":
                recommendations.insert(0, {
                    "priority": 0,
                    "action": f"URGENT: Address {risk['type'].replace('_', ' ')}",
                    "reasoning": risk["description"],
                    "category": "risk"
                })

        return recommendations

    async def predict_case_outcome(
        self,
        case_id: str,
        user_id: str
    ) -> CasePrediction:
        """
        Generate AI prediction for case outcome.
        """
        case = self.db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == user_id
        ).first()

        if not case:
            raise ValueError("Case not found")

        # Gather case context
        documents = self.db.query(Document).filter(
            Document.case_id == case_id
        ).limit(10).all()

        facts = self.db.query(CaseFact).filter(
            CaseFact.case_id == case_id
        ).all()

        # Build context for AI analysis
        context = {
            "case_type": case.case_type,
            "jurisdiction": case.jurisdiction,
            "status": case.status,
            "parties": case.parties,
            "facts": [{"type": f.fact_type, "text": f.fact_text} for f in facts[:20]],
            "document_types": [d.document_type for d in documents]
        }

        # Generate prediction using AI
        prompt = f"""Analyze this litigation case and predict the likely outcome.

Case Details:
- Type: {case.case_type}
- Jurisdiction: {case.jurisdiction}
- Status: {case.status}
- Parties: {json.dumps(case.parties) if case.parties else 'Unknown'}

Key Facts:
{json.dumps([f['text'] for f in context['facts'][:10]], indent=2)}

Based on similar cases and the information provided, predict:
1. Most likely outcome (settlement, plaintiff_verdict, defendant_verdict, dismissal)
2. Confidence level (0.0-1.0)
3. Key factors influencing this prediction
4. Estimated settlement range if applicable

Respond in JSON format:
{{
    "predicted_outcome": "settlement|plaintiff_verdict|defendant_verdict|dismissal",
    "confidence": 0.75,
    "reasoning": "Brief explanation",
    "factors": [
        {{"factor": "factor_name", "impact": "positive|negative|neutral", "weight": 0.3}}
    ],
    "settlement_range": {{"low": 50000, "high": 150000}} // if settlement predicted
}}"""

        try:
            response = await self.ai_service.analyze_with_claude(prompt)

            # Parse AI response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                prediction_data = json.loads(response[json_start:json_end])
            else:
                prediction_data = {
                    "predicted_outcome": "unknown",
                    "confidence": 0.5,
                    "reasoning": "Unable to parse prediction",
                    "factors": []
                }

            # Create prediction record
            prediction = CasePrediction(
                id=str(uuid.uuid4()),
                case_id=case_id,
                user_id=user_id,
                prediction_type="outcome",
                predicted_value=prediction_data.get("predicted_outcome", "unknown"),
                confidence=Decimal(str(prediction_data.get("confidence", 0.5))),
                influencing_factors=prediction_data.get("factors", []),
                model_version="claude-sonnet-4-20250514"
            )

            if "settlement_range" in prediction_data:
                prediction.lower_bound = str(prediction_data["settlement_range"].get("low"))
                prediction.upper_bound = str(prediction_data["settlement_range"].get("high"))

            self.db.add(prediction)
            self.db.commit()

            return prediction

        except Exception as e:
            logger.error(f"Prediction generation failed: {e}")
            raise

    async def extract_case_facts(
        self,
        case_id: str,
        user_id: str,
        document_id: str
    ) -> List[CaseFact]:
        """
        Extract key facts from a document using AI.
        """
        document = self.db.query(Document).filter(
            Document.id == document_id,
            Document.case_id == case_id,
            Document.user_id == user_id
        ).first()

        if not document:
            raise ValueError("Document not found")

        # Get document content (assuming it's stored or can be retrieved)
        content = document.extracted_text or ""
        if not content:
            return []

        prompt = f"""Extract key legal facts from this document.

Document Type: {document.document_type}
Content:
{content[:8000]}

Extract facts in these categories:
- party: Names of parties involved
- date: Important dates (filing, incident, deadlines)
- amount: Dollar amounts, damages claimed
- claim: Legal claims or causes of action
- defense: Defenses raised
- evidence: Key evidence mentioned
- witness: Witnesses identified

Respond in JSON format:
{{
    "facts": [
        {{
            "type": "party|date|amount|claim|defense|evidence|witness",
            "text": "The extracted fact",
            "normalized_value": "Standardized value if applicable",
            "importance": "critical|high|standard|low",
            "source_excerpt": "Relevant quote from document",
            "confidence": 0.95
        }}
    ]
}}"""

        try:
            response = await self.ai_service.analyze_with_claude(prompt)

            # Parse response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                facts_data = result.get("facts", [])
            else:
                facts_data = []

            # Create fact records
            created_facts = []
            for fact_data in facts_data:
                fact = CaseFact(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    user_id=user_id,
                    fact_type=fact_data.get("type", "unknown"),
                    fact_text=fact_data.get("text", ""),
                    normalized_value=fact_data.get("normalized_value"),
                    importance=fact_data.get("importance", "standard"),
                    source_document_id=document_id,
                    source_excerpt=fact_data.get("source_excerpt"),
                    extraction_confidence=Decimal(str(fact_data.get("confidence", 0.8)))
                )
                self.db.add(fact)
                created_facts.append(fact)

            self.db.commit()
            return created_facts

        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
            raise

    async def get_judge_insights(
        self,
        judge_name: str,
        jurisdiction_id: Optional[str] = None
    ) -> Optional[JudgeProfile]:
        """
        Get or create judge profile with analytics.
        """
        query = self.db.query(JudgeProfile).filter(
            JudgeProfile.name.ilike(f"%{judge_name}%")
        )

        if jurisdiction_id:
            query = query.filter(JudgeProfile.jurisdiction_id == jurisdiction_id)

        profile = query.first()

        if not profile:
            # Create basic profile
            profile = JudgeProfile(
                id=str(uuid.uuid4()),
                name=judge_name,
                jurisdiction_id=jurisdiction_id,
                motion_stats={},
                preferences={},
                case_type_experience={}
            )
            self.db.add(profile)
            self.db.commit()

        return profile

    def get_case_timeline(
        self,
        case_id: str,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[str]] = None
    ) -> List[CaseEvent]:
        """
        Get case timeline events.
        """
        query = self.db.query(CaseEvent).filter(
            CaseEvent.case_id == case_id,
            CaseEvent.user_id == user_id
        )

        if start_date:
            query = query.filter(CaseEvent.event_date >= start_date)
        if end_date:
            query = query.filter(CaseEvent.event_date <= end_date)
        if event_types:
            query = query.filter(CaseEvent.event_type.in_(event_types))

        return query.order_by(CaseEvent.event_date).all()

    def sync_timeline_from_deadlines(
        self,
        case_id: str,
        user_id: str
    ) -> int:
        """
        Sync case events from deadlines.
        """
        deadlines = self.db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.user_id == user_id
        ).all()

        created_count = 0
        for deadline in deadlines:
            # Check if event already exists
            existing = self.db.query(CaseEvent).filter(
                CaseEvent.deadline_id == deadline.id
            ).first()

            if not existing and deadline.due_date:
                event = CaseEvent(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    user_id=user_id,
                    event_type="deadline",
                    event_subtype=deadline.deadline_type,
                    title=deadline.title,
                    description=deadline.description,
                    event_date=datetime.combine(deadline.due_date, datetime.min.time()),
                    status="scheduled" if deadline.status == 'pending' else deadline.status,
                    priority=deadline.priority or "standard",
                    deadline_id=deadline.id
                )
                self.db.add(event)
                created_count += 1

        self.db.commit()
        return created_count
