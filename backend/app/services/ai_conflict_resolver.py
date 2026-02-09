"""
AI Rule Conflict Resolution Service

Phase 6: Advanced Intelligence

Uses Claude AI to automatically detect and resolve conflicts between competing rules:
- Identifies conflicting deadline specifications
- Analyzes source authority (official vs unofficial)
- Compares effective dates and amendments
- Determines which rule is authoritative
- Auto-resolves high-confidence conflicts (≥90%)
- Creates recommendations for medium-confidence conflicts (70-90%)

Success Rate Target: 70% auto-resolve without human intervention
"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import logging
import json

from app.models.authority_core import AuthorityRule, RuleConflict
from app.models.jurisdiction import Jurisdiction
from app.models.enums import ConflictResolution
from app.services.inbox_service import InboxService
from app.config import settings

logger = logging.getLogger(__name__)


class AIConflictResolver:
    """
    Intelligent rule conflict resolution using Claude AI.

    Analyzes competing rules and automatically determines which
    should take precedence based on legal authority principles.
    """

    # Configuration
    AUTO_RESOLVE_THRESHOLD = 0.90  # Confidence threshold for auto-resolution
    RECOMMEND_THRESHOLD = 0.70  # Minimum confidence for recommendation
    MAX_CONFLICTS_PER_RUN = 50  # Batch size for conflict processing

    def __init__(self, db: Session):
        self.db = db
        self.inbox_service = InboxService(db)

    async def detect_conflicts(self, jurisdiction_id: Optional[str] = None) -> List[RuleConflict]:
        """
        Detect potential conflicts between rules.

        Conflicts occur when:
        1. Multiple rules have same trigger type in same jurisdiction
        2. Rules specify different deadlines for same event
        3. Rules have overlapping but inconsistent conditions

        Args:
            jurisdiction_id: Optional filter by jurisdiction

        Returns:
            List of detected conflicts
        """
        logger.info("Starting conflict detection")

        # Query for duplicate rule codes or overlapping trigger types
        query = self.db.query(AuthorityRule).filter(
            AuthorityRule.is_active == True
        )

        if jurisdiction_id:
            query = query.filter(AuthorityRule.jurisdiction_id == jurisdiction_id)

        rules = query.all()

        # Group rules by jurisdiction + trigger_type
        rule_groups: Dict[Tuple[str, str], List[AuthorityRule]] = {}

        for rule in rules:
            key = (rule.jurisdiction_id, rule.trigger_type)
            if key not in rule_groups:
                rule_groups[key] = []
            rule_groups[key].append(rule)

        # Detect conflicts within each group
        conflicts = []

        for (juris_id, trigger), group_rules in rule_groups.items():
            if len(group_rules) <= 1:
                continue  # No conflict possible with single rule

            # Check for conflicting deadline specifications
            for i, rule1 in enumerate(group_rules):
                for rule2 in group_rules[i+1:]:
                    conflict = self._compare_rules(rule1, rule2)

                    if conflict:
                        # Check if conflict already exists
                        existing = self.db.query(RuleConflict).filter(
                            RuleConflict.rule1_id == rule1.id,
                            RuleConflict.rule2_id == rule2.id,
                            RuleConflict.resolution_status == ConflictResolution.UNRESOLVED
                        ).first()

                        if not existing:
                            # Create new conflict record
                            new_conflict = RuleConflict(
                                jurisdiction_id=juris_id,
                                rule1_id=rule1.id,
                                rule2_id=rule2.id,
                                conflict_type=conflict["type"],
                                conflict_details=conflict["details"],
                                detected_at=datetime.now(timezone.utc),
                                resolution_status=ConflictResolution.UNRESOLVED
                            )
                            self.db.add(new_conflict)
                            conflicts.append(new_conflict)

        if conflicts:
            self.db.commit()
            logger.info(f"Detected {len(conflicts)} new conflicts")

        return conflicts

    def _compare_rules(self, rule1: AuthorityRule, rule2: AuthorityRule) -> Optional[Dict[str, Any]]:
        """
        Compare two rules to detect conflicts.

        Args:
            rule1: First rule
            rule2: Second rule

        Returns:
            Conflict details if conflict detected, None otherwise
        """
        # Skip if rules are identical
        if rule1.rule_code == rule2.rule_code:
            return None

        conflicts = []

        # Check for deadline specification conflicts
        if rule1.deadlines and rule2.deadlines:
            rule1_deadlines = {d.get('title'): d for d in rule1.deadlines}
            rule2_deadlines = {d.get('title'): d for d in rule2.deadlines}

            # Find matching deadline titles
            common_titles = set(rule1_deadlines.keys()) & set(rule2_deadlines.keys())

            for title in common_titles:
                d1 = rule1_deadlines[title]
                d2 = rule2_deadlines[title]

                # Check if they specify different days
                days1 = d1.get('days_from_trigger', 0)
                days2 = d2.get('days_from_trigger', 0)

                if days1 != days2:
                    conflicts.append({
                        "deadline_title": title,
                        "rule1_days": days1,
                        "rule2_days": days2,
                        "difference": abs(days1 - days2)
                    })

        if conflicts:
            return {
                "type": "deadline_specification_conflict",
                "details": {
                    "rule1_code": rule1.rule_code,
                    "rule2_code": rule2.rule_code,
                    "conflicts": conflicts
                }
            }

        return None

    async def resolve_conflict(self, conflict_id: str) -> Dict[str, Any]:
        """
        Use AI to analyze and resolve a specific conflict.

        Args:
            conflict_id: Conflict UUID

        Returns:
            Resolution result with confidence score and recommended action
        """
        conflict = self.db.query(RuleConflict).filter(
            RuleConflict.id == conflict_id
        ).first()

        if not conflict:
            return {"success": False, "error": "Conflict not found"}

        # Get the rules involved
        rule1 = self.db.query(AuthorityRule).filter(AuthorityRule.id == conflict.rule1_id).first()
        rule2 = self.db.query(AuthorityRule).filter(AuthorityRule.id == conflict.rule2_id).first()

        if not rule1 or not rule2:
            return {"success": False, "error": "One or both rules not found"}

        # Get jurisdiction for context
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == conflict.jurisdiction_id
        ).first()

        logger.info(f"Resolving conflict between {rule1.rule_code} and {rule2.rule_code}")

        # Call Claude AI for analysis
        try:
            analysis = await self._ai_analyze_conflict(rule1, rule2, jurisdiction, conflict)

            # Determine action based on confidence
            if analysis["confidence"] >= self.AUTO_RESOLVE_THRESHOLD:
                # Auto-resolve
                resolution = await self._apply_resolution(conflict, analysis)
                return {
                    "success": True,
                    "action": "auto_resolved",
                    "resolution": resolution,
                    "analysis": analysis
                }
            elif analysis["confidence"] >= self.RECOMMEND_THRESHOLD:
                # Create recommendation inbox item
                await self._create_conflict_inbox_item(conflict, analysis, "recommendation")
                return {
                    "success": True,
                    "action": "recommendation_created",
                    "analysis": analysis
                }
            else:
                # Low confidence - require manual review
                await self._create_conflict_inbox_item(conflict, analysis, "manual_review")
                return {
                    "success": True,
                    "action": "manual_review_required",
                    "analysis": analysis
                }

        except Exception as e:
            logger.error(f"Conflict resolution failed: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _ai_analyze_conflict(
        self,
        rule1: AuthorityRule,
        rule2: AuthorityRule,
        jurisdiction: Jurisdiction,
        conflict: RuleConflict
    ) -> Dict[str, Any]:
        """
        Use Claude AI to analyze conflict and determine authoritative rule.

        Args:
            rule1: First conflicting rule
            rule2: Second conflicting rule
            jurisdiction: Jurisdiction context
            conflict: Conflict record

        Returns:
            AI analysis with confidence score and recommendation
        """
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=settings.anthropic_api_key)

            # Build prompt
            prompt = f"""You are a legal rules expert analyzing a conflict between two court procedural rules.

JURISDICTION: {jurisdiction.name}
CONFLICT TYPE: {conflict.conflict_type}

RULE 1:
- Code: {rule1.rule_code}
- Name: {rule1.rule_name}
- Citation: {rule1.citation}
- Source URL: {rule1.source_url or 'N/A'}
- Deadlines: {json.dumps(rule1.deadlines, indent=2)}
- Verified: {rule1.is_verified}
- Confidence Score: {rule1.confidence_score}
- Created: {rule1.created_at}

RULE 2:
- Code: {rule2.rule_code}
- Name: {rule2.rule_name}
- Citation: {rule2.citation}
- Source URL: {rule2.source_url or 'N/A'}
- Deadlines: {json.dumps(rule2.deadlines, indent=2)}
- Verified: {rule2.is_verified}
- Confidence Score: {rule2.confidence_score}
- Created: {rule2.created_at}

CONFLICT DETAILS:
{json.dumps(conflict.conflict_details, indent=2)}

ANALYSIS TASK:
1. Determine which rule is authoritative based on:
   - Source authority (official court website > unofficial source)
   - Verification status (verified > unverified)
   - Recency (newer rules may supersede older ones)
   - Citation quality (complete citations > incomplete)
   - Confidence score (higher confidence > lower confidence)

2. Provide a confidence score (0.0-1.0) for your determination

3. Recommend an action:
   - "keep_rule1_deactivate_rule2" - Rule 1 is authoritative
   - "keep_rule2_deactivate_rule1" - Rule 2 is authoritative
   - "merge_rules" - Both have merit, create merged rule
   - "manual_review" - Cannot determine with confidence

Respond in JSON format:
{{
  "authoritative_rule": "rule1" or "rule2" or "both" or "unclear",
  "confidence": 0.0-1.0,
  "reasoning": "explanation of your determination",
  "recommended_action": "action string",
  "key_factors": ["factor1", "factor2", ...],
  "warnings": ["any concerns or caveats"]
}}"""

            # Call Claude
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse JSON response
            response_text = response.content[0].text
            analysis = json.loads(response_text)

            logger.info(f"AI analysis complete with {analysis['confidence']:.0%} confidence")

            return analysis

        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            # Return low-confidence fallback
            return {
                "authoritative_rule": "unclear",
                "confidence": 0.0,
                "reasoning": f"AI analysis failed: {str(e)}",
                "recommended_action": "manual_review",
                "key_factors": [],
                "warnings": ["AI analysis unavailable - manual review required"]
            }

    async def _apply_resolution(self, conflict: RuleConflict, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply AI-recommended conflict resolution.

        Args:
            conflict: Conflict to resolve
            analysis: AI analysis results

        Returns:
            Resolution result
        """
        action = analysis["recommended_action"]

        try:
            if action == "keep_rule1_deactivate_rule2":
                # Deactivate rule 2
                rule2 = self.db.query(AuthorityRule).filter(AuthorityRule.id == conflict.rule2_id).first()
                if rule2:
                    rule2.is_active = False
                    rule2.deactivation_reason = f"Conflict resolved: superseded by {conflict.rule1_id}"

                conflict.resolution_status = ConflictResolution.RESOLVED
                conflict.resolved_at = datetime.now(timezone.utc)
                conflict.resolution_details = analysis

            elif action == "keep_rule2_deactivate_rule1":
                # Deactivate rule 1
                rule1 = self.db.query(AuthorityRule).filter(AuthorityRule.id == conflict.rule1_id).first()
                if rule1:
                    rule1.is_active = False
                    rule1.deactivation_reason = f"Conflict resolved: superseded by {conflict.rule2_id}"

                conflict.resolution_status = ConflictResolution.RESOLVED
                conflict.resolved_at = datetime.now(timezone.utc)
                conflict.resolution_details = analysis

            else:
                # Other actions require manual intervention
                return {"success": False, "error": "Action requires manual intervention"}

            self.db.commit()

            logger.info(f"Conflict {conflict.id} auto-resolved: {action}")

            return {
                "success": True,
                "action": action,
                "confidence": analysis["confidence"]
            }

        except Exception as e:
            logger.error(f"Failed to apply resolution: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    async def _create_conflict_inbox_item(
        self,
        conflict: RuleConflict,
        analysis: Dict[str, Any],
        item_type: str
    ) -> None:
        """
        Create inbox item for conflict requiring human review.

        Args:
            conflict: Conflict record
            analysis: AI analysis
            item_type: "recommendation" or "manual_review"
        """
        try:
            title = (
                f"Conflict Resolution {'Recommendation' if item_type == 'recommendation' else 'Required'}"
                f": {conflict.conflict_type}"
            )

            description = f"""AI-detected rule conflict requires {'your approval' if item_type == 'recommendation' else 'manual review'}.

**AI Analysis:**
- Confidence: {analysis['confidence']:.0%}
- Recommended Action: {analysis['recommended_action']}
- Reasoning: {analysis['reasoning']}

**Key Factors:**
{chr(10).join(f"- {factor}" for factor in analysis.get('key_factors', []))}

**Warnings:**
{chr(10).join(f"- {warning}" for warning in analysis.get('warnings', []))}

Please review the conflicting rules and make a final determination.
"""

            self.inbox_service.create_conflict_resolution_item(
                conflict_id=conflict.id,
                title=title,
                description=description,
                metadata={
                    "ai_analysis": analysis,
                    "conflict_type": conflict.conflict_type,
                    "rule1_id": conflict.rule1_id,
                    "rule2_id": conflict.rule2_id,
                    "confidence": analysis["confidence"]
                }
            )

            logger.info(f"Created conflict inbox item for {conflict.id}")

        except Exception as e:
            logger.error(f"Failed to create conflict inbox item: {str(e)}")

    async def batch_resolve_conflicts(
        self,
        jurisdiction_id: Optional[str] = None,
        max_conflicts: int = MAX_CONFLICTS_PER_RUN
    ) -> Dict[str, Any]:
        """
        Batch process and resolve multiple conflicts.

        Args:
            jurisdiction_id: Optional filter by jurisdiction
            max_conflicts: Maximum conflicts to process in this run

        Returns:
            Batch processing report
        """
        logger.info("Starting batch conflict resolution")

        # Get unresolved conflicts
        query = self.db.query(RuleConflict).filter(
            RuleConflict.resolution_status == ConflictResolution.UNRESOLVED
        )

        if jurisdiction_id:
            query = query.filter(RuleConflict.jurisdiction_id == jurisdiction_id)

        conflicts = query.limit(max_conflicts).all()

        report = {
            "total_processed": len(conflicts),
            "auto_resolved": 0,
            "recommendations_created": 0,
            "manual_review_required": 0,
            "failed": 0,
            "details": []
        }

        for conflict in conflicts:
            try:
                result = await self.resolve_conflict(conflict.id)

                if result["success"]:
                    action = result["action"]
                    if action == "auto_resolved":
                        report["auto_resolved"] += 1
                    elif action == "recommendation_created":
                        report["recommendations_created"] += 1
                    elif action == "manual_review_required":
                        report["manual_review_required"] += 1

                    report["details"].append({
                        "conflict_id": conflict.id,
                        "action": action,
                        "confidence": result.get("analysis", {}).get("confidence", 0)
                    })
                else:
                    report["failed"] += 1

            except Exception as e:
                logger.error(f"Failed to resolve conflict {conflict.id}: {str(e)}")
                report["failed"] += 1

        logger.info(
            f"Batch resolution complete: {report['auto_resolved']} auto-resolved, "
            f"{report['recommendations_created']} recommendations, "
            f"{report['manual_review_required']} manual review"
        )

        return report


# =========================================================================
# SCHEDULED JOB INTEGRATION
# =========================================================================

async def run_conflict_detection_and_resolution(db: Session) -> Dict[str, Any]:
    """
    Entry point for scheduled job (called daily).

    Args:
        db: Database session

    Returns:
        Combined detection and resolution report
    """
    resolver = AIConflictResolver(db)

    # Step 1: Detect new conflicts
    conflicts = await resolver.detect_conflicts()

    # Step 2: Attempt to resolve unresolved conflicts
    resolution_report = await resolver.batch_resolve_conflicts()

    return {
        "conflicts_detected": len(conflicts),
        "resolution_report": resolution_report
    }
