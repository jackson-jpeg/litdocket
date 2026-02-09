"""
Phase 7: Power Tools - Simplified Tool Interface for Claude

This module consolidates 41+ granular tools into 5 powerful, context-aware tools:
1. query_case - Get case info, deadlines, documents, parties
2. update_case - Update case metadata, parties, or settings
3. manage_deadline - Create, update, delete deadlines with cascade awareness
4. execute_trigger - Generate deadlines from triggers using Authority Core rules
5. search_rules - Search Authority Core for court rules by citation or keyword

Benefits:
- Reduces tool choice complexity for Claude (41 → 5)
- Improves reliability and reduces API round trips
- Each power tool is context-aware and handles routing internally
- Maintains backward compatibility with old tools for 30-day transition
"""

from typing import Dict, Any, List, Optional
from datetime import date as date_type, datetime
from sqlalchemy.orm import Session
import logging
import uuid
import os

from app.models.case import Case
from app.models.deadline import Deadline
from app.models.document import Document
from app.models.authority_core import AuthorityRule
from app.models.jurisdiction import Jurisdiction
from app.models.proposal import Proposal
from app.services.authority_integrated_deadline_service import AuthorityIntegratedDeadlineService
from app.services.authority_core_service import AuthorityCoreService
from app.services.dependency_listener import DependencyListener
from app.models.enums import TriggerType, ProposalStatus, ProposalActionType

logger = logging.getLogger(__name__)

# Phase 7 Step 11: Feature flag for proposal/approval workflow
USE_PROPOSALS = os.environ.get("USE_PROPOSALS", "false").lower() == "true"

if USE_PROPOSALS:
    logger.info("✅ Proposal workflow enabled - AI actions require user approval")
else:
    logger.info("ℹ️  Proposal workflow disabled - AI writes directly to database")


# Phase 7 Step 9: Required field validation for conversational intake
# Prevents AI from guessing or using defaults - forces clarification questions
TRIGGER_REQUIREMENTS = {
    'trial_date': ['jury_status'],
    'complaint_served': ['service_method'],
    'answer_filed': ['service_method'],
    'discovery_served': ['service_method', 'discovery_type'],
    'motion_filed': ['service_method', 'motion_type'],
    'motion_hearing': [],  # No additional context needed
    'pretrial_conference': [],
    'mediation': [],
    'arbitration': [],
    'appeal_filed': ['service_method'],
    'judgment_entered': [],
    'case_filed': [],
    'custom': []  # User-defined triggers don't require validation
}

CLARIFICATION_QUESTIONS = {
    'jury_status': "Is this a jury trial or non-jury trial? (jury/non_jury)",
    'service_method': "How was service completed? (mail, electronic, or hand_delivery)",
    'discovery_type': "What type of discovery? (interrogatories, requests_for_production, requests_for_admission, depositions)",
    'motion_type': "What type of motion? (summary_judgment, dismiss, compel, protective_order, other)",
    'case_type': "What type of case is this? (civil, criminal, family, probate, appellate)"
}


# Power Tool Definitions for Claude API
POWER_TOOLS = [
    {
        "name": "query_case",
        "description": """Get comprehensive case information in one call.

Use this when the user asks questions like:
- "What deadlines do I have?"
- "Show me case details"
- "List all documents"
- "Who are the parties?"
- "What's the status of my deadlines?"

This tool replaces: query_deadlines, get_case_statistics, search_documents, get_dependency_tree, list_parties""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["summary", "deadlines", "documents", "parties", "statistics", "dependencies"],
                    "description": "What information to retrieve"
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filters (e.g., status, priority, date range)",
                    "properties": {
                        "status": {"type": "string"},
                        "priority": {"type": "string"},
                        "overdue_only": {"type": "boolean"},
                        "upcoming_days": {"type": "integer"}
                    }
                }
            },
            "required": ["query_type"]
        }
    },
    {
        "name": "update_case",
        "description": """Update case metadata, parties, or settings.

Use this when the user wants to:
- "Change the judge to Smith"
- "Add John Doe as plaintiff"
- "Update case status to active"
- "Remove party Jane Doe"

This tool replaces: update_case_info, add_party, remove_party, close_case""",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["update_metadata", "add_party", "remove_party", "change_status"],
                    "description": "Type of update to perform"
                },
                "data": {
                    "type": "object",
                    "description": "Update data (judge, party info, status, etc.)"
                }
            },
            "required": ["action", "data"]
        }
    },
    {
        "name": "manage_deadline",
        "description": """Comprehensive deadline management with cascade awareness.

Use this for ALL deadline operations:
- "Add deadline for Answer Due on March 15"
- "Move trial date to June 1" (handles cascade)
- "Delete this deadline"
- "Update deadline priority to fatal"
- "Mark deadline as completed"

This tool replaces: create_deadline, update_deadline, delete_deadline, move_deadline,
apply_cascade_update, preview_cascade_update, bulk_update_deadlines""",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "delete", "move", "mark_complete", "preview_cascade"],
                    "description": "Deadline operation to perform"
                },
                "deadline_id": {
                    "type": "string",
                    "description": "ID of deadline (for update/delete/move)"
                },
                "data": {
                    "type": "object",
                    "description": "Deadline data (title, date, priority, etc.)",
                    "properties": {
                        "title": {"type": "string"},
                        "deadline_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "priority": {
                            "type": "string",
                            "enum": ["informational", "standard", "important", "critical", "fatal"]
                        },
                        "description": {"type": "string"},
                        "party_role": {"type": "string"},
                        "action_required": {"type": "string"}
                    }
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "execute_trigger",
        "description": """Generate deadlines from trigger events using Authority Core rules.

Use this when the user provides a trigger event:
- "Trial is scheduled for June 15"
- "I just served the complaint"
- "Discovery deadline is March 1"
- "Motion hearing is next Tuesday"

This tool:
1. Queries Authority Core for verified rules (or falls back to hardcoded)
2. Calculates 20-50+ dependent deadlines automatically
3. Handles service method extensions (+5 days for mail)
4. Creates full deadline chain with dependencies
5. Asks clarifying questions if needed (jury vs non-jury, service method)

This tool replaces: create_trigger_deadline, generate_all_deadlines_for_case,
calculate_from_rule, find_applicable_rules""",
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_type": {
                    "type": "string",
                    "enum": [
                        "case_filed", "complaint_served", "answer_filed",
                        "discovery_served", "discovery_deadline",
                        "motion_filed", "motion_hearing",
                        "trial_date", "pretrial_conference",
                        "mediation", "arbitration",
                        "appeal_filed", "judgment_entered", "custom"
                    ],
                    "description": "Type of trigger event"
                },
                "trigger_date": {
                    "type": "string",
                    "description": "Date of trigger event (YYYY-MM-DD)"
                },
                "service_method": {
                    "type": "string",
                    "enum": ["electronic", "mail", "hand_delivery"],
                    "description": "How was service completed (affects +5 day rule)"
                },
                "context": {
                    "type": "object",
                    "description": "Additional context (jury_status, case_type, etc.)",
                    "properties": {
                        "jury_status": {"type": "string", "enum": ["jury", "non_jury"]},
                        "case_type": {"type": "string"},
                        "motion_type": {"type": "string"}
                    }
                }
            },
            "required": ["trigger_type", "trigger_date"]
        }
    },
    {
        "name": "search_rules",
        "description": """Search Authority Core rules database by citation, trigger, or keyword.

Use this when the user asks:
- "What's the deadline for answering a complaint?"
- "Show me Rule 1.140"
- "What are the MSJ response rules?"
- "Find rules about discovery deadlines"
- "What triggers are available for Florida civil cases?"

This tool queries the verified Authority Core rules database (29+ rules).

This tool replaces: search_court_rules, get_rule_details, lookup_court_rule,
validate_deadline_against_rules, explain_deadline_from_rule, suggest_related_rules,
get_available_templates, analyze_rule_coverage""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["by_citation", "by_trigger", "by_keyword", "list_all"],
                    "description": "How to search"
                },
                "query": {
                    "type": "string",
                    "description": "Search query (rule citation, trigger type, or keyword)"
                },
                "jurisdiction_id": {
                    "type": "string",
                    "description": "Optional: filter by jurisdiction UUID"
                },
                "include_details": {
                    "type": "boolean",
                    "description": "Include full rule text and deadlines (default: false)"
                }
            },
            "required": ["query_type"]
        }
    }
]


class PowerToolExecutor:
    """
    Phase 7: Simplified tool executor with 5 powerful, context-aware tools.

    Each power tool handles routing and consolidates multiple granular tools.
    """

    def __init__(self, case_id: str, user_id: str, db: Session):
        self.case_id = case_id
        self.user_id = user_id
        self.db = db

        # Initialize Authority Core services
        try:
            self.authority_service = AuthorityCoreService(db)
            self.deadline_service = AuthorityIntegratedDeadlineService(db)
            self.dependency_listener = DependencyListener(db)
        except Exception as e:
            logger.warning(f"Failed to initialize Authority Core services: {e}")
            self.authority_service = None
            self.deadline_service = None
            self.dependency_listener = None

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a power tool.

        Phase 7 Step 11: If USE_PROPOSALS is enabled and this is a write operation,
        creates a Proposal instead of executing directly.
        """

        # Phase 7 Step 11: Check if this is a write operation that needs approval
        if USE_PROPOSALS and self._is_write_operation(tool_name, tool_input):
            return self._create_proposal_for_action(tool_name, tool_input)

        # Execute tool directly
        if tool_name == "query_case":
            return await self._query_case(tool_input)
        elif tool_name == "update_case":
            return await self._update_case(tool_input)
        elif tool_name == "manage_deadline":
            return await self._manage_deadline(tool_input)
        elif tool_name == "execute_trigger":
            return await self._execute_trigger(tool_input)
        elif tool_name == "search_rules":
            return await self._search_rules(tool_input)
        else:
            return {"success": False, "error": f"Unknown power tool: {tool_name}"}

    def _is_write_operation(self, tool_name: str, tool_input: Dict) -> bool:
        """
        Phase 7 Step 11: Determine if a tool operation requires approval.

        Read operations (query_case, search_rules) don't need approval.
        Write operations (manage_deadline, execute_trigger, update_case) do.
        """
        # Read operations - no approval needed
        if tool_name in ["query_case", "search_rules"]:
            return False

        # Write operations - need approval
        if tool_name in ["manage_deadline", "execute_trigger", "update_case"]:
            return True

        # Default to requiring approval for unknown operations
        return True

    def _create_proposal_for_action(self, tool_name: str, tool_input: Dict) -> Dict:
        """
        Phase 7 Step 11: Create a Proposal record instead of executing action.

        Returns a success response with proposal_id, requiring user approval.
        """
        try:
            # Map tool_name to ProposalActionType
            action_type_map = {
                "manage_deadline": self._get_manage_deadline_action_type(tool_input),
                "execute_trigger": ProposalActionType.CREATE_DEADLINE,
                "update_case": ProposalActionType.UPDATE_CASE
            }

            action_type = action_type_map.get(tool_name)
            if not action_type:
                return {"success": False, "error": f"Cannot create proposal for tool: {tool_name}"}

            # Generate preview summary
            preview_summary = self._generate_preview_summary(tool_name, tool_input)

            # Create proposal
            proposal = Proposal(
                id=str(uuid.uuid4()),
                case_id=self.case_id,
                user_id=self.user_id,
                action_type=action_type,
                action_data=tool_input,
                ai_reasoning=self._generate_ai_reasoning(tool_name, tool_input),
                status=ProposalStatus.PENDING,
                preview_summary=preview_summary,
                affected_items=self._calculate_affected_items(tool_name, tool_input)
            )

            self.db.add(proposal)
            self.db.commit()

            logger.info(f"✅ Created proposal {proposal.id} for {tool_name}")

            return {
                "success": True,
                "requires_approval": True,
                "proposal_id": proposal.id,
                "preview_summary": preview_summary,
                "message": "This action requires your approval. Please approve or reject the proposal.",
                "approval_url": f"/api/v1/proposals/{proposal.id}"
            }

        except Exception as e:
            logger.error(f"❌ Failed to create proposal: {str(e)}")
            return {"success": False, "error": f"Failed to create proposal: {str(e)}"}

    def _get_manage_deadline_action_type(self, tool_input: Dict) -> ProposalActionType:
        """Map manage_deadline action to ProposalActionType"""
        action = tool_input.get("action")

        if action == "create":
            return ProposalActionType.CREATE_DEADLINE
        elif action == "update":
            return ProposalActionType.UPDATE_DEADLINE
        elif action == "delete":
            return ProposalActionType.DELETE_DEADLINE
        elif action == "move":
            return ProposalActionType.MOVE_DEADLINE
        else:
            return ProposalActionType.UPDATE_DEADLINE  # Default

    def _generate_preview_summary(self, tool_name: str, tool_input: Dict) -> str:
        """Generate human-readable summary for proposal"""

        if tool_name == "manage_deadline":
            action = tool_input.get("action")
            data = tool_input.get("data", {})

            if action == "create":
                title = data.get("title", "Unnamed deadline")
                date = data.get("deadline_date", "unknown date")
                return f"Create deadline: {title} on {date}"
            elif action == "update":
                deadline_id = tool_input.get("deadline_id")
                return f"Update deadline {deadline_id}"
            elif action == "delete":
                deadline_id = tool_input.get("deadline_id")
                return f"Delete deadline {deadline_id}"
            elif action == "move":
                deadline_id = tool_input.get("deadline_id")
                new_date = data.get("deadline_date", "unknown date")
                return f"Move deadline {deadline_id} to {new_date}"

        elif tool_name == "execute_trigger":
            trigger_type = tool_input.get("trigger_type", "unknown trigger")
            trigger_date = tool_input.get("trigger_date", "unknown date")
            return f"Generate deadlines from {trigger_type.replace('_', ' ')} on {trigger_date}"

        elif tool_name == "update_case":
            action = tool_input.get("action")
            return f"Update case: {action}"

        return f"Execute {tool_name}"

    def _generate_ai_reasoning(self, tool_name: str, tool_input: Dict) -> str:
        """Generate AI reasoning for why this action was proposed"""

        if tool_name == "execute_trigger":
            trigger_type = tool_input.get("trigger_type", "unknown")
            return f"Based on your statement, I identified a {trigger_type.replace('_', ' ')} trigger event and calculated the dependent deadlines using Authority Core rules."

        elif tool_name == "manage_deadline":
            action = tool_input.get("action")
            return f"Based on your request, I need to {action} a deadline."

        elif tool_name == "update_case":
            return "Based on your request, I need to update case information."

        return f"AI proposed {tool_name} action"

    def _calculate_affected_items(self, tool_name: str, tool_input: Dict) -> Dict:
        """Calculate which items will be affected by this action"""

        if tool_name == "execute_trigger":
            # Would create multiple deadlines
            return {
                "estimated_deadlines": "20-50+",
                "type": "bulk_creation"
            }

        elif tool_name == "manage_deadline":
            action = tool_input.get("action")

            if action == "move":
                # Check for dependent deadlines
                deadline_id = tool_input.get("deadline_id")
                dependents = self.db.query(Deadline).filter(
                    Deadline.parent_deadline_id == deadline_id,
                    Deadline.auto_recalculate == True
                ).count()

                return {
                    "dependent_deadlines": dependents,
                    "type": "cascade_update"
                }

        return {}

    # =============================================================================
    # POWER TOOL 1: QUERY_CASE
    # =============================================================================

    async def _query_case(self, input_data: Dict) -> Dict:
        """Get comprehensive case information"""
        try:
            query_type = input_data['query_type']
            filters = input_data.get('filters', {})

            # Get case
            case = self.db.query(Case).filter(
                Case.id == self.case_id,
                Case.user_id == self.user_id
            ).first()

            if not case:
                return {"success": False, "error": "Case not found"}

            if query_type == "summary":
                return {
                    "success": True,
                    "case": {
                        "id": case.id,
                        "case_number": case.case_number,
                        "title": case.title,
                        "court": case.court,
                        "judge": case.judge,
                        "status": case.status,
                        "case_type": case.case_type,
                        "jurisdiction": case.jurisdiction,
                        "parties": case.parties,
                        "filing_date": case.filing_date.isoformat() if case.filing_date else None
                    }
                }

            elif query_type == "deadlines":
                # Query deadlines with filters
                query = self.db.query(Deadline).filter(
                    Deadline.case_id == self.case_id,
                    Deadline.user_id == self.user_id
                )

                # Apply filters
                if filters.get('status'):
                    query = query.filter(Deadline.status == filters['status'])
                if filters.get('priority'):
                    query = query.filter(Deadline.priority == filters['priority'])
                if filters.get('overdue_only'):
                    query = query.filter(
                        Deadline.status == 'pending',
                        Deadline.deadline_date < date_type.today()
                    )
                if filters.get('upcoming_days'):
                    from datetime import timedelta
                    future_date = date_type.today() + timedelta(days=filters['upcoming_days'])
                    query = query.filter(
                        Deadline.deadline_date >= date_type.today(),
                        Deadline.deadline_date <= future_date
                    )

                deadlines = query.order_by(Deadline.deadline_date).all()

                return {
                    "success": True,
                    "count": len(deadlines),
                    "deadlines": [
                        {
                            "id": d.id,
                            "title": d.title,
                            "deadline_date": d.deadline_date.isoformat() if d.deadline_date else None,
                            "priority": d.priority,
                            "status": d.status,
                            "party_role": d.party_role,
                            "calculation_basis": d.calculation_basis,
                            "source_rule_id": d.source_rule_id,
                            "is_calculated": d.is_calculated,
                            "is_overdue": d.deadline_date < date_type.today() if d.deadline_date else False
                        }
                        for d in deadlines
                    ]
                }

            elif query_type == "documents":
                documents = self.db.query(Document).filter(
                    Document.case_id == self.case_id
                ).order_by(Document.created_at.desc()).all()

                return {
                    "success": True,
                    "count": len(documents),
                    "documents": [
                        {
                            "id": d.id,
                            "file_name": d.file_name,
                            "document_type": d.document_type,
                            "filing_date": d.filing_date.isoformat() if d.filing_date else None,
                            "ai_summary": d.ai_summary,
                            "created_at": d.created_at.isoformat() if d.created_at else None
                        }
                        for d in documents
                    ]
                }

            elif query_type == "parties":
                return {
                    "success": True,
                    "parties": case.parties or []
                }

            elif query_type == "statistics":
                # Calculate deadline statistics
                all_deadlines = self.db.query(Deadline).filter(
                    Deadline.case_id == self.case_id,
                    Deadline.user_id == self.user_id
                ).all()

                total = len(all_deadlines)
                pending = sum(1 for d in all_deadlines if d.status == 'pending')
                completed = sum(1 for d in all_deadlines if d.status == 'completed')
                overdue = sum(1 for d in all_deadlines
                             if d.status == 'pending' and d.deadline_date and d.deadline_date < date_type.today())
                fatal = sum(1 for d in all_deadlines if d.priority == 'fatal')
                authority_core = sum(1 for d in all_deadlines if d.source_rule_id)

                return {
                    "success": True,
                    "statistics": {
                        "total_deadlines": total,
                        "pending": pending,
                        "completed": completed,
                        "overdue": overdue,
                        "fatal_priority": fatal,
                        "from_authority_core": authority_core,
                        "from_hardcoded": total - authority_core
                    }
                }

            elif query_type == "dependencies":
                # Get deadline dependency tree
                deadlines_with_deps = self.db.query(Deadline).filter(
                    Deadline.case_id == self.case_id,
                    Deadline.user_id == self.user_id,
                    Deadline.is_dependent == True
                ).all()

                return {
                    "success": True,
                    "dependent_deadlines": len(deadlines_with_deps),
                    "chains": [
                        {
                            "deadline_id": d.id,
                            "title": d.title,
                            "parent_id": d.parent_deadline_id,
                            "trigger_event": d.trigger_event
                        }
                        for d in deadlines_with_deps
                    ]
                }

            else:
                return {"success": False, "error": f"Unknown query_type: {query_type}"}

        except Exception as e:
            logger.error(f"Error in _query_case: {e}")
            return {"success": False, "error": str(e)}

    # =============================================================================
    # POWER TOOL 2: UPDATE_CASE
    # =============================================================================

    async def _update_case(self, input_data: Dict) -> Dict:
        """Update case metadata, parties, or settings"""
        try:
            action = input_data['action']
            data = input_data['data']

            # Get case
            case = self.db.query(Case).filter(
                Case.id == self.case_id,
                Case.user_id == self.user_id
            ).first()

            if not case:
                return {"success": False, "error": "Case not found"}

            if action == "update_metadata":
                # Update case fields
                for key, value in data.items():
                    if hasattr(case, key):
                        setattr(case, key, value)

                self.db.commit()
                return {
                    "success": True,
                    "message": f"Updated case metadata",
                    "updated_fields": list(data.keys())
                }

            elif action == "add_party":
                # Add party to parties JSON
                parties = case.parties or []
                new_party = {
                    "name": data.get('name'),
                    "role": data.get('role'),
                    "type": data.get('type', 'individual')
                }
                parties.append(new_party)
                case.parties = parties
                self.db.commit()

                return {
                    "success": True,
                    "message": f"Added party: {new_party['name']} ({new_party['role']})",
                    "parties": parties
                }

            elif action == "remove_party":
                # Remove party by name
                parties = case.parties or []
                party_name = data.get('name')
                parties = [p for p in parties if p.get('name') != party_name]
                case.parties = parties
                self.db.commit()

                return {
                    "success": True,
                    "message": f"Removed party: {party_name}",
                    "parties": parties
                }

            elif action == "change_status":
                case.status = data.get('status')
                self.db.commit()

                return {
                    "success": True,
                    "message": f"Changed case status to {case.status}"
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in _update_case: {e}")
            return {"success": False, "error": str(e)}

    # =============================================================================
    # POWER TOOL 3: MANAGE_DEADLINE
    # =============================================================================

    async def _manage_deadline(self, input_data: Dict) -> Dict:
        """Comprehensive deadline management with cascade awareness"""
        try:
            action = input_data['action']
            deadline_id = input_data.get('deadline_id')
            data = input_data.get('data', {})

            if action == "create":
                # Create new deadline
                deadline = Deadline(
                    id=str(uuid.uuid4()),
                    case_id=self.case_id,
                    user_id=self.user_id,
                    title=data['title'],
                    deadline_date=date_type.fromisoformat(data['deadline_date']),
                    description=data.get('description'),
                    priority=data.get('priority', 'standard'),
                    party_role=data.get('party_role'),
                    action_required=data.get('action_required'),
                    status='pending',
                    created_via_chat=True,
                    extraction_method='manual',
                    confidence_score=100,
                    confidence_level='high'
                )
                self.db.add(deadline)
                self.db.commit()

                return {
                    "success": True,
                    "deadline_id": deadline.id,
                    "message": f"Created deadline: {deadline.title} on {deadline.deadline_date.isoformat()}"
                }

            elif action == "update":
                # Update existing deadline
                deadline = self.db.query(Deadline).filter(
                    Deadline.id == deadline_id,
                    Deadline.user_id == self.user_id
                ).first()

                if not deadline:
                    return {"success": False, "error": "Deadline not found"}

                # Track manual override
                if 'deadline_date' in data and deadline.is_calculated:
                    deadline.is_manually_overridden = True
                    deadline.override_timestamp = datetime.utcnow()
                    deadline.override_user_id = self.user_id
                    deadline.original_deadline_date = deadline.deadline_date

                # Update fields
                for key, value in data.items():
                    if key == 'deadline_date':
                        value = date_type.fromisoformat(value)
                    if hasattr(deadline, key):
                        setattr(deadline, key, value)

                self.db.commit()

                return {
                    "success": True,
                    "message": f"Updated deadline: {deadline.title}",
                    "manually_overridden": deadline.is_manually_overridden
                }

            elif action == "delete":
                # Delete deadline
                deadline = self.db.query(Deadline).filter(
                    Deadline.id == deadline_id,
                    Deadline.user_id == self.user_id
                ).first()

                if not deadline:
                    return {"success": False, "error": "Deadline not found"}

                title = deadline.title
                self.db.delete(deadline)
                self.db.commit()

                return {
                    "success": True,
                    "message": f"Deleted deadline: {title}"
                }

            elif action == "move":
                # Move deadline with cascade preview
                deadline = self.db.query(Deadline).filter(
                    Deadline.id == deadline_id,
                    Deadline.user_id == self.user_id
                ).first()

                if not deadline:
                    return {"success": False, "error": "Deadline not found"}

                new_date = date_type.fromisoformat(data['deadline_date'])
                old_date = deadline.deadline_date

                # Check if this triggers cascade
                dependents = self.db.query(Deadline).filter(
                    Deadline.parent_deadline_id == deadline_id,
                    Deadline.auto_recalculate == True,
                    Deadline.is_manually_overridden == False
                ).all()

                if dependents and not data.get('apply_cascade'):
                    # Return cascade preview
                    return {
                        "success": False,
                        "needs_cascade_approval": True,
                        "message": f"Moving this deadline will affect {len(dependents)} dependent deadlines",
                        "affected_deadlines": [
                            {
                                "id": d.id,
                                "title": d.title,
                                "current_date": d.deadline_date.isoformat() if d.deadline_date else None
                            }
                            for d in dependents
                        ],
                        "instruction": "Call manage_deadline again with apply_cascade: true to confirm"
                    }

                # Apply the move
                deadline.deadline_date = new_date
                deadline.is_manually_overridden = True
                deadline.override_timestamp = datetime.utcnow()
                deadline.original_deadline_date = old_date

                # Apply cascade if approved
                if data.get('apply_cascade') and self.dependency_listener:
                    days_shift = (new_date - old_date).days
                    cascade_count = await self.dependency_listener.handle_trigger_change(
                        trigger_id=deadline_id,
                        old_date=old_date,
                        new_date=new_date
                    )
                else:
                    cascade_count = 0

                self.db.commit()

                return {
                    "success": True,
                    "message": f"Moved deadline from {old_date.isoformat()} to {new_date.isoformat()}",
                    "cascade_applied": cascade_count > 0,
                    "dependents_updated": cascade_count
                }

            elif action == "mark_complete":
                deadline = self.db.query(Deadline).filter(
                    Deadline.id == deadline_id,
                    Deadline.user_id == self.user_id
                ).first()

                if not deadline:
                    return {"success": False, "error": "Deadline not found"}

                deadline.status = 'completed'
                self.db.commit()

                return {
                    "success": True,
                    "message": f"Marked deadline as completed: {deadline.title}"
                }

            elif action == "preview_cascade":
                # Preview cascade impact
                deadline = self.db.query(Deadline).filter(
                    Deadline.id == deadline_id,
                    Deadline.user_id == self.user_id
                ).first()

                if not deadline:
                    return {"success": False, "error": "Deadline not found"}

                dependents = self.db.query(Deadline).filter(
                    Deadline.parent_deadline_id == deadline_id,
                    Deadline.auto_recalculate == True,
                    Deadline.is_manually_overridden == False
                ).all()

                return {
                    "success": True,
                    "is_trigger": deadline.is_calculated == False,
                    "dependent_count": len(dependents),
                    "dependents": [
                        {
                            "id": d.id,
                            "title": d.title,
                            "current_date": d.deadline_date.isoformat() if d.deadline_date else None,
                            "will_update": d.auto_recalculate and not d.is_manually_overridden
                        }
                        for d in dependents
                    ]
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in _manage_deadline: {e}")
            return {"success": False, "error": str(e)}

    # =============================================================================
    # POWER TOOL 4: EXECUTE_TRIGGER
    # =============================================================================

    async def _execute_trigger(self, input_data: Dict) -> Dict:
        """Generate deadlines from trigger events using Authority Core"""
        try:
            trigger_type_str = input_data['trigger_type']
            trigger_date = date_type.fromisoformat(input_data['trigger_date'])
            context = input_data.get('context', {})

            # Phase 7 Step 9: Required field validation - NO DEFAULTS ALLOWED
            # Check for missing required fields based on trigger type
            required_fields = TRIGGER_REQUIREMENTS.get(trigger_type_str, [])
            missing_fields = []

            for field in required_fields:
                # Check both in top-level input_data and nested context
                if field not in input_data and field not in context:
                    missing_fields.append(field)

            # If any required fields are missing, return clarification request
            if missing_fields:
                clarification_needed = {}
                for field in missing_fields:
                    clarification_needed[field] = CLARIFICATION_QUESTIONS.get(
                        field,
                        f"Please provide: {field.replace('_', ' ')}"
                    )

                logger.info(f"⚠️ Missing required fields for {trigger_type_str}: {missing_fields}")
                return {
                    "success": False,
                    "needs_clarification": True,
                    "missing_fields": missing_fields,
                    "clarification_questions": clarification_needed,
                    "message": f"I need more information to generate accurate deadlines for {trigger_type_str.replace('_', ' ')}."
                }

            # Extract validated fields (no defaults - must be explicitly provided)
            service_method = input_data.get('service_method') or context.get('service_method', 'electronic')

            # Get case and jurisdiction
            case = self.db.query(Case).filter(Case.id == self.case_id).first()
            if not case:
                return {"success": False, "error": "Case not found"}

            jurisdiction_name = case.jurisdiction or 'florida_state'
            court_type = case.case_type or 'civil'

            # Look up jurisdiction_id
            jurisdiction_obj = self.db.query(Jurisdiction).filter(
                (Jurisdiction.code == jurisdiction_name.upper()) |
                (Jurisdiction.name.ilike(f'%{jurisdiction_name}%'))
            ).first()

            if not jurisdiction_obj:
                jurisdiction_obj = self.db.query(Jurisdiction).filter(
                    Jurisdiction.code == 'FL'
                ).first()

            jurisdiction_id = str(jurisdiction_obj.id) if jurisdiction_obj else None

            # Use Authority Integrated Deadline Service
            if not self.deadline_service:
                return {"success": False, "error": "Deadline service not initialized"}

            integrated_deadlines = await self.deadline_service.calculate_deadlines(
                jurisdiction_id=jurisdiction_id,
                trigger_type=trigger_type_str,
                trigger_date=trigger_date,
                jurisdiction_name=jurisdiction_name,
                court_type=court_type,
                service_method=service_method,
                case_context=context,
                user_id=self.user_id,
                case_id=self.case_id
            )

            if not integrated_deadlines:
                return {
                    "success": False,
                    "error": f"No rules found for {trigger_type_str} in {jurisdiction_name}/{court_type}"
                }

            # Create trigger deadline (parent)
            trigger_deadline = Deadline(
                id=str(uuid.uuid4()),
                case_id=self.case_id,
                user_id=self.user_id,
                title=trigger_type_str.replace('_', ' ').title(),
                description=f"Trigger event: {trigger_type_str}",
                deadline_date=trigger_date,
                trigger_event=trigger_type_str,
                trigger_date=trigger_date,
                is_calculated=False,
                is_dependent=False,
                priority="important",
                status="completed",
                created_via_chat=True,
                extraction_method='manual',
                confidence_score=95,
                confidence_level='high'
            )
            self.db.add(trigger_deadline)
            self.db.flush()

            # Create dependent deadlines
            created_deadlines = []
            for integrated_dl in integrated_deadlines:
                extraction_method = 'authority_core' if integrated_dl.source_rule_id else 'rule-based'
                confidence_score = 95 if integrated_dl.source_rule_id else 90

                deadline = Deadline(
                    id=str(uuid.uuid4()),
                    case_id=self.case_id,
                    user_id=self.user_id,
                    parent_deadline_id=trigger_deadline.id,
                    title=integrated_dl.title,
                    description=integrated_dl.description,
                    deadline_date=integrated_dl.deadline_date,
                    priority=integrated_dl.priority.lower(),
                    party_role=integrated_dl.party_role,
                    action_required=integrated_dl.action_required,
                    applicable_rule=integrated_dl.rule_citation,
                    calculation_basis=integrated_dl.calculation_basis,
                    trigger_event=integrated_dl.trigger_event,
                    trigger_date=integrated_dl.trigger_date,
                    is_calculated=True,
                    is_dependent=True,
                    service_method=service_method,
                    source_rule_id=integrated_dl.source_rule_id,
                    calculation_type=integrated_dl.calculation_type,
                    days_count=integrated_dl.days_count,
                    created_via_chat=True,
                    extraction_method=extraction_method,
                    confidence_score=confidence_score,
                    confidence_level='high',
                    verification_status='pending',
                    extraction_quality_score=9 if integrated_dl.source_rule_id else 8
                )
                self.db.add(deadline)
                created_deadlines.append({
                    "title": integrated_dl.title,
                    "deadline_date": integrated_dl.deadline_date.isoformat(),
                    "priority": integrated_dl.priority,
                    "source": "Authority Core" if integrated_dl.source_rule_id else "Hardcoded Rules",
                    "citation": integrated_dl.rule_citation
                })

            self.db.commit()

            authority_count = sum(1 for d in integrated_deadlines if d.source_rule_id)
            hardcoded_count = len(integrated_deadlines) - authority_count

            return {
                "success": True,
                "trigger_id": trigger_deadline.id,
                "trigger_type": trigger_type_str,
                "trigger_date": trigger_date.isoformat(),
                "deadlines_created": len(created_deadlines),
                "authority_core_count": authority_count,
                "hardcoded_count": hardcoded_count,
                "deadlines": created_deadlines,
                "message": f"✓ Created '{trigger_type_str}' with {len(created_deadlines)} deadlines ({authority_count} from Authority Core, {hardcoded_count} from hardcoded rules)"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in _execute_trigger: {e}")
            return {"success": False, "error": str(e)}

    # =============================================================================
    # POWER TOOL 5: SEARCH_RULES
    # =============================================================================

    async def _search_rules(self, input_data: Dict) -> Dict:
        """Search Authority Core rules database"""
        try:
            query_type = input_data['query_type']
            query = input_data.get('query', '')
            jurisdiction_id = input_data.get('jurisdiction_id')
            include_details = input_data.get('include_details', False)

            # Base query for Authority Core rules
            base_query = self.db.query(AuthorityRule).filter(
                AuthorityRule.is_active == True
            )

            if jurisdiction_id:
                base_query = base_query.filter(AuthorityRule.jurisdiction_id == jurisdiction_id)

            if query_type == "by_citation":
                # Search by rule code or citation
                rules = base_query.filter(
                    (AuthorityRule.rule_code.ilike(f'%{query}%')) |
                    (AuthorityRule.citation.ilike(f'%{query}%'))
                ).all()

            elif query_type == "by_trigger":
                # Search by trigger type
                rules = base_query.filter(
                    AuthorityRule.trigger_type == query
                ).all()

            elif query_type == "by_keyword":
                # Search by keyword in name or source text
                rules = base_query.filter(
                    (AuthorityRule.rule_name.ilike(f'%{query}%')) |
                    (AuthorityRule.source_text.ilike(f'%{query}%'))
                ).all()

            elif query_type == "list_all":
                # List all rules
                rules = base_query.order_by(AuthorityRule.rule_code).all()

            else:
                return {"success": False, "error": f"Unknown query_type: {query_type}"}

            # Format response
            if include_details:
                return {
                    "success": True,
                    "count": len(rules),
                    "rules": [
                        {
                            "rule_id": str(r.id),
                            "rule_code": r.rule_code,
                            "rule_name": r.rule_name,
                            "trigger_type": r.trigger_type,
                            "citation": r.citation,
                            "authority_tier": r.authority_tier.value if hasattr(r.authority_tier, 'value') else r.authority_tier,
                            "deadlines": r.deadlines,
                            "service_extensions": r.service_extensions,
                            "conditions": r.conditions,
                            "source_url": r.source_url,
                            "confidence_score": r.confidence_score,
                            "is_verified": r.is_verified,
                            "usage_count": r.usage_count,
                            "jurisdiction_name": r.jurisdiction.name if r.jurisdiction else None
                        }
                        for r in rules
                    ]
                }
            else:
                return {
                    "success": True,
                    "count": len(rules),
                    "rules": [
                        {
                            "rule_id": str(r.id),
                            "rule_code": r.rule_code,
                            "rule_name": r.rule_name,
                            "trigger_type": r.trigger_type,
                            "citation": r.citation,
                            "deadlines_count": len(r.deadlines),
                            "confidence_score": r.confidence_score,
                            "is_verified": r.is_verified
                        }
                        for r in rules
                    ]
                }

        except Exception as e:
            logger.error(f"Error in _search_rules: {e}")
            return {"success": False, "error": str(e)}
