"""
Chat Service - Intelligent case-aware chatbot
Provides natural language interface for docketing assistant
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
import re

import logging

from app.services.ai_service import AIService
from app.services.deadline_service import DeadlineService
from app.services.case_summary_service import CaseSummaryService
from app.services.rules_engine import rules_engine, TriggerType
from app.models.case import Case

logger = logging.getLogger(__name__)
from app.models.document import Document
from app.models.deadline import Deadline
from app.models.chat_message import ChatMessage
from datetime import date as date_type


class ChatService:
    """
    Intelligent chatbot for docketing assistant

    Capabilities:
    - Answer questions about cases, deadlines, rules
    - Create/update/delete deadlines via natural language
    - Search documents
    - Explain deadline calculations
    - Provide procedural guidance
    """

    def __init__(self):
        self.ai_service = AIService()
        self.deadline_service = DeadlineService()
        self.summary_service = CaseSummaryService()

    async def process_message(
        self,
        user_message: str,
        case_id: str,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process user message and generate intelligent response

        Returns:
            {
                'response': str,  # AI response
                'actions_taken': List[Dict],  # Any actions performed (deadline created, etc.)
                'citations': List[str],  # Rule citations
                'message_id': str  # Saved message ID
            }
        """

        # Get case context
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {'error': 'Case not found'}

        # Get conversation history (last 10 messages)
        history = db.query(ChatMessage).filter(
            ChatMessage.case_id == case_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()
        history.reverse()  # Chronological order

        # Build comprehensive context
        context = await self._build_context(case, db)

        # Determine intent and execute actions
        intent = await self._analyze_intent(user_message, context)
        actions_taken = []

        # Execute actions based on intent
        if intent['type'] == 'create_deadline':
            action_result = await self._create_deadline_from_chat(
                intent['details'],
                case_id,
                user_id,
                db
            )
            actions_taken.append(action_result)

        elif intent['type'] == 'create_trigger':
            action_result = await self._create_trigger_from_chat(
                intent['details'],
                case,
                user_id,
                db
            )
            actions_taken.append(action_result)

        elif intent['type'] == 'update_deadline':
            action_result = await self._update_deadline_from_chat(
                intent['details'],
                db
            )
            actions_taken.append(action_result)

        elif intent['type'] == 'delete_deadline':
            action_result = await self._delete_deadline_from_chat(
                intent['details'],
                db
            )
            actions_taken.append(action_result)

        # Generate AI response with full context
        ai_response = await self._generate_response(
            user_message=user_message,
            conversation_history=history,
            case_context=context,
            intent=intent,
            actions_taken=actions_taken
        )

        # Save messages to database
        user_msg = ChatMessage(
            case_id=case_id,
            user_id=user_id,
            role='user',
            content=user_message
        )
        db.add(user_msg)

        assistant_msg = ChatMessage(
            case_id=case_id,
            user_id=user_id,
            role='assistant',
            content=ai_response['content'],
            context_documents=ai_response.get('context_documents', []),
            context_rules=ai_response.get('context_rules', []),
            tokens_used=ai_response.get('tokens_used', 0),
            model_used=ai_response.get('model', 'claude-sonnet-4')
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return {
            'response': ai_response['content'],
            'actions_taken': actions_taken,
            'citations': ai_response.get('context_rules', []),
            'message_id': str(assistant_msg.id),
            'tokens_used': ai_response.get('tokens_used', 0)
        }

    async def _build_context(self, case: Case, db: Session) -> Dict:
        """Build comprehensive context for AI"""

        # Get all case data
        documents = db.query(Document).filter(
            Document.case_id == case.id
        ).order_by(Document.created_at.desc()).all()

        deadlines = db.query(Deadline).filter(
            Deadline.case_id == case.id
        ).order_by(Deadline.deadline_date.asc().nullslast()).all()

        # Get trigger events (non-dependent deadlines with trigger_event set)
        triggers = db.query(Deadline).filter(
            Deadline.case_id == case.id,
            Deadline.is_dependent == False,
            Deadline.trigger_event.isnot(None)
        ).all()

        # Separate upcoming and past deadlines
        today = datetime.now().date()
        upcoming_deadlines = [
            d for d in deadlines
            if d.deadline_date and d.deadline_date >= today and d.status == 'pending'
        ]
        past_deadlines = [
            d for d in deadlines
            if d.deadline_date and d.deadline_date < today
        ]

        return {
            'case_number': case.case_number,
            'case_title': case.title,
            'court': case.court,
            'judge': case.judge,
            'case_type': case.case_type,
            'jurisdiction': case.jurisdiction,
            'parties': case.parties or [],
            'filing_date': case.filing_date.isoformat() if case.filing_date else None,
            'documents': [
                {
                    'id': str(doc.id),
                    'file_name': doc.file_name,
                    'document_type': doc.document_type,
                    'filing_date': doc.filing_date.isoformat() if doc.filing_date else None,
                    'summary': doc.ai_summary,
                    'created_at': doc.created_at.isoformat()
                }
                for doc in documents
            ],
            'upcoming_deadlines': [
                {
                    'id': str(d.id),
                    'title': d.title,
                    'deadline_date': d.deadline_date.isoformat() if d.deadline_date else None,
                    'priority': d.priority,
                    'calculation_basis': d.calculation_basis,
                    'applicable_rule': d.applicable_rule
                }
                for d in upcoming_deadlines
            ],
            'past_deadlines': [
                {
                    'id': str(d.id),
                    'title': d.title,
                    'deadline_date': d.deadline_date.isoformat(),
                    'status': d.status
                }
                for d in past_deadlines[:5]  # Last 5 past deadlines
            ],
            'trigger_events': [
                {
                    'id': str(t.id),
                    'trigger_type': t.trigger_event,
                    'trigger_date': t.deadline_date.isoformat() if t.deadline_date else None,
                    'title': t.title,
                    'dependent_count': db.query(Deadline).filter(
                        Deadline.parent_deadline_id == str(t.id)
                    ).count()
                }
                for t in triggers
            ],
            'document_count': len(documents),
            'deadline_count': len(upcoming_deadlines),
            'trigger_count': len(triggers)
        }

    async def _analyze_intent(self, user_message: str, context: Dict) -> Dict:
        """
        Analyze user intent to determine if they want to take an action
        (create deadline, update case, etc.)
        """

        intent_prompt = f"""Analyze this user message and determine their intent.

User message: "{user_message}"

Case context: {context.get('case_number')} in {context.get('court')}
Existing triggers: {len(context.get('trigger_events', []))} trigger events set

Determine if the user wants to:
1. create_trigger - Set a trigger event (trial date, service date, complaint filed, etc.) that will auto-generate dependent deadlines
2. query_trigger - Ask about existing trigger events or when a trigger date is
3. create_deadline - Add a single manual deadline
4. update_deadline - Modify an existing deadline
5. delete_deadline - Remove a deadline
6. query_information - Just asking a question (no action)
7. search_documents - Search through documents
8. explain_rule - Explain a court rule or calculation

TRIGGER EVENT DETECTION:
If the user mentions setting/creating any of these events, it's a "create_trigger" intent:
- Trial date
- Hearing date
- Service of complaint
- Service of process
- Answer deadline triggering event
- Motion filed date
- Discovery deadline triggering event

If creating a trigger, extract:
- trigger_type: "trial_date", "service_completed", "case_filed", "motion_filed", "answer_filed", "discovery_deadline"
- trigger_date: When did/will the trigger event occur? (YYYY-MM-DD format)
- service_method: "email", "mail", "personal" (default: email)
- notes: Any additional context

If creating a manual deadline, extract:
- title: What is the deadline for?
- deadline_date: When is it due? (YYYY-MM-DD format)
- party_role: Who must take action?
- action_required: What action is needed?
- priority: low/medium/high
- notes: Any additional context

Return as JSON:
{{
  "type": "create_trigger|query_trigger|create_deadline|update_deadline|delete_deadline|query_information|search_documents|explain_rule",
  "confidence": 0.0-1.0,
  "details": {{
    // Extracted information based on intent type
  }}
}}
"""

        try:
            response = await self.ai_service.analyze_with_prompt(intent_prompt, max_tokens=1024)

            # Parse JSON response using AI service's parser
            intent = self.ai_service._parse_json_response(response)

            # Check if parsing failed
            if intent.get('parse_error'):
                raise ValueError("Failed to parse intent response")

            return intent
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return {
                'type': 'query_information',
                'confidence': 0.5,
                'details': {}
            }

    async def _create_deadline_from_chat(
        self,
        details: Dict,
        case_id: str,
        user_id: str,
        db: Session
    ) -> Dict:
        """Create a deadline from chat conversation"""

        try:
            deadline = Deadline(
                case_id=case_id,
                user_id=user_id,
                title=details.get('title', 'New deadline'),
                description=details.get('notes', 'Created via chat'),
                deadline_date=details.get('deadline_date'),
                deadline_type=details.get('deadline_type', 'custom'),
                priority=details.get('priority', 'medium'),
                status='pending',
                party_role=details.get('party_role'),
                action_required=details.get('action_required'),
                created_via_chat=True
            )

            db.add(deadline)
            db.commit()
            db.refresh(deadline)

            return {
                'action': 'create_deadline',
                'success': True,
                'deadline_id': str(deadline.id),
                'deadline_title': deadline.title,
                'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None
            }

        except Exception as e:
            return {
                'action': 'create_deadline',
                'success': False,
                'error': str(e)
            }

    async def _create_trigger_from_chat(
        self,
        details: Dict,
        case: Case,
        user_id: str,
        db: Session
    ) -> Dict:
        """Create a trigger event from chat conversation"""

        try:
            # Parse trigger type
            trigger_type_str = details.get('trigger_type', 'trial_date')
            try:
                trigger_enum = TriggerType(trigger_type_str)
            except ValueError:
                # Default to trial_date if invalid
                trigger_enum = TriggerType.TRIAL_DATE

            # Parse trigger date
            trigger_date_str = details.get('trigger_date')
            if not trigger_date_str:
                return {
                    'action': 'create_trigger',
                    'success': False,
                    'error': 'No trigger date provided'
                }

            trigger_date = date_type.fromisoformat(trigger_date_str)

            # Get service method
            service_method = details.get('service_method', 'email')

            # Get applicable rule templates
            jurisdiction = case.jurisdiction or 'florida_state'
            court_type = case.case_type or 'civil'

            templates = rules_engine.get_applicable_rules(
                jurisdiction=jurisdiction,
                court_type=court_type,
                trigger_type=trigger_enum
            )

            if not templates:
                return {
                    'action': 'create_trigger',
                    'success': False,
                    'error': f'No rule templates found for {jurisdiction} {court_type} {trigger_type_str}'
                }

            # Create the trigger deadline (the "parent")
            trigger_deadline = Deadline(
                case_id=case.id,
                user_id=user_id,
                title=f"{trigger_type_str.replace('_', ' ').title()}",
                description=f"Trigger event: {trigger_type_str}",
                deadline_date=trigger_date,
                trigger_event=trigger_type_str,
                trigger_date=trigger_date,
                is_calculated=False,
                is_dependent=False,
                priority="important",
                status="completed",  # Trigger already happened
                notes=details.get('notes'),
                created_via_chat=True
            )

            db.add(trigger_deadline)
            db.flush()  # Get ID for parent reference

            # Generate all dependent deadlines
            all_dependent_deadlines = []

            for template in templates:
                dependent_deadlines = rules_engine.calculate_dependent_deadlines(
                    trigger_date=trigger_date,
                    rule_template=template,
                    service_method=service_method
                )

                # Create deadline records
                for deadline_data in dependent_deadlines:
                    deadline = Deadline(
                        case_id=case.id,
                        user_id=user_id,
                        parent_deadline_id=str(trigger_deadline.id),
                        title=deadline_data['title'],
                        description=deadline_data['description'],
                        deadline_date=deadline_data['deadline_date'],
                        priority=deadline_data['priority'],
                        party_role=deadline_data['party_role'],
                        action_required=deadline_data['action_required'],
                        applicable_rule=deadline_data['rule_citation'],
                        calculation_basis=deadline_data['calculation_basis'],
                        trigger_event=deadline_data['trigger_event'],
                        trigger_date=deadline_data['trigger_date'],
                        is_calculated=True,
                        is_dependent=True,
                        auto_recalculate=True,
                        original_deadline_date=deadline_data['deadline_date'],
                        service_method=service_method,
                        created_via_chat=True
                    )

                    db.add(deadline)
                    all_dependent_deadlines.append(deadline)

            db.commit()
            db.refresh(trigger_deadline)

            return {
                'action': 'create_trigger',
                'success': True,
                'trigger_id': str(trigger_deadline.id),
                'trigger_type': trigger_type_str,
                'trigger_date': trigger_date.isoformat(),
                'dependent_deadlines_created': len(all_dependent_deadlines)
            }

        except Exception as e:
            db.rollback()
            return {
                'action': 'create_trigger',
                'success': False,
                'error': str(e)
            }

    async def _update_deadline_from_chat(self, details: Dict, db: Session) -> Dict:
        """Update an existing deadline from chat"""

        try:
            deadline_id = details.get('deadline_id')
            if not deadline_id:
                return {'action': 'update_deadline', 'success': False, 'error': 'No deadline ID provided'}

            deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
            if not deadline:
                return {'action': 'update_deadline', 'success': False, 'error': 'Deadline not found'}

            # Update fields
            if 'deadline_date' in details:
                deadline.deadline_date = details['deadline_date']
            if 'status' in details:
                deadline.status = details['status']
            if 'priority' in details:
                deadline.priority = details['priority']

            db.commit()
            db.refresh(deadline)

            return {
                'action': 'update_deadline',
                'success': True,
                'deadline_id': str(deadline.id),
                'deadline_title': deadline.title
            }

        except Exception as e:
            return {
                'action': 'update_deadline',
                'success': False,
                'error': str(e)
            }

    async def _delete_deadline_from_chat(self, details: Dict, db: Session) -> Dict:
        """Delete a deadline from chat"""

        try:
            deadline_id = details.get('deadline_id')
            if not deadline_id:
                return {'action': 'delete_deadline', 'success': False, 'error': 'No deadline ID provided'}

            deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
            if not deadline:
                return {'action': 'delete_deadline', 'success': False, 'error': 'Deadline not found'}

            deadline_title = deadline.title
            db.delete(deadline)
            db.commit()

            return {
                'action': 'delete_deadline',
                'success': True,
                'deadline_title': deadline_title
            }

        except Exception as e:
            return {
                'action': 'delete_deadline',
                'success': False,
                'error': str(e)
            }

    async def _generate_response(
        self,
        user_message: str,
        conversation_history: List[ChatMessage],
        case_context: Dict,
        intent: Dict,
        actions_taken: List[Dict]
    ) -> Dict:
        """Generate AI response with full context"""

        # Build system prompt
        system_prompt = """You are an expert Florida legal docketing assistant with deep knowledge of:
- Florida Rules of Civil Procedure
- Florida Rules of Criminal Procedure
- Florida Rules of Appellate Procedure
- Federal Rules of Civil Procedure
- All Florida judicial circuit local rules

Your role is to:
1. Answer questions about cases, deadlines, and court rules
2. Explain deadline calculations with rule citations
3. Help users manage their case docket with trigger-based automation
4. Provide procedural guidance
5. Be proactive - suggest actions and warn about upcoming deadlines

TRIGGER-BASED DEADLINE GENERATION:
- You can create "trigger events" that auto-generate ALL dependent deadlines
- Example: Set trial date → automatically generates 5+ deadlines (pretrial motions, witness lists, etc.)
- Example: Set service date → automatically calculates answer deadline based on service method
- When users mention trial dates, service dates, or other key events, suggest creating a trigger
- This is MUCH better than manually adding individual deadlines

CRITICAL PRINCIPLES (Jackson's Methodology):
- COMPREHENSIVE OVER SELECTIVE - Mention ALL relevant deadlines and considerations
- SHOW YOUR WORK - Always cite rules and explain calculations
- ACCURACY - Double-check dates, calculations, and rule citations

When discussing deadlines:
- Always cite the applicable rule (e.g., "Fla. R. Civ. P. 1.140(a)")
- Explain service method additions (email=0 days, mail=+5 days since Jan 1, 2019)
- Consider weekends and holidays
- State whether it's a Florida state or federal court rule

Be conversational but professional. Use clear, concise language."""

        # Build conversation history
        messages = []
        for msg in conversation_history[-10:]:  # Last 10 messages
            messages.append({
                'role': msg.role,
                'content': msg.content
            })

        # Build context message
        context_text = f"""CURRENT CASE CONTEXT:

Case: {case_context['case_number']} - {case_context['case_title']}
Court: {case_context['court']}
Judge: {case_context['judge']}
Type: {case_context['case_type']} ({case_context['jurisdiction']})

Parties:
{self._format_parties(case_context['parties'])}

Trigger Events ({case_context['trigger_count']} total):
{self._format_triggers(case_context['trigger_events'])}

Documents ({case_context['document_count']} total):
{self._format_documents(case_context['documents'][:5])}

Upcoming Deadlines ({case_context['deadline_count']} total):
{self._format_deadlines(case_context['upcoming_deadlines'][:5])}

Recent Actions:
{self._format_actions(actions_taken)}
"""

        # Add context and user message
        messages.append({
            'role': 'user',
            'content': f"{context_text}\n\nUser Question: {user_message}"
        })

        # Call Claude
        response = await self.ai_service.analyze_with_prompt(
            prompt=f"System: {system_prompt}\n\n" + "\n\n".join([
                f"{m['role'].title()}: {m['content']}" for m in messages
            ]),
            max_tokens=4096
        )

        # Extract rule citations
        rule_citations = self._extract_rule_citations(response)

        return {
            'content': response,
            'model': 'claude-sonnet-4',
            'tokens_used': len(response.split()),  # Approximate
            'context_rules': rule_citations,
            'context_documents': [str(d['id']) for d in case_context['documents'][:5]]
        }

    def _format_parties(self, parties: List[Dict]) -> str:
        """Format parties for context"""
        if not parties:
            return "  (No parties listed)"
        return "\n".join([f"  - {p.get('role', 'Unknown')}: {p.get('name', 'Unknown')}" for p in parties])

    def _format_triggers(self, triggers: List[Dict]) -> str:
        """Format trigger events for context"""
        if not triggers:
            return "  (No trigger events set - suggest creating one for automatic deadline generation!)"
        formatted = []
        for t in triggers:
            line = f"  ⚡ {t['title']}: {t.get('trigger_date', 'TBD')}"
            if t.get('dependent_count'):
                line += f" (generated {t['dependent_count']} dependent deadlines)"
            formatted.append(line)
        return "\n".join(formatted)

    def _format_documents(self, documents: List[Dict]) -> str:
        """Format documents for context"""
        if not documents:
            return "  (No documents)"
        formatted = []
        for doc in documents:
            line = f"  - {doc['created_at'][:10]}: {doc['file_name']}"
            if doc.get('document_type'):
                line += f" ({doc['document_type']})"
            formatted.append(line)
        return "\n".join(formatted)

    def _format_deadlines(self, deadlines: List[Dict]) -> str:
        """Format deadlines for context"""
        if not deadlines:
            return "  (No upcoming deadlines)"
        formatted = []
        for d in deadlines:
            line = f"  - {d.get('deadline_date', 'TBD')}: {d['title']}"
            if d.get('priority'):
                line += f" [{d['priority'].upper()}]"
            formatted.append(line)
        return "\n".join(formatted)

    def _format_actions(self, actions: List[Dict]) -> str:
        """Format actions taken"""
        if not actions:
            return "  (No actions taken)"
        formatted = []
        for action in actions:
            if action['success']:
                if action['action'] == 'create_trigger':
                    formatted.append(f"  ⚡ Created trigger event: {action.get('trigger_type')} on {action.get('trigger_date')} (generated {action.get('dependent_deadlines_created')} deadlines)")
                else:
                    formatted.append(f"  ✓ {action['action']}: {action.get('deadline_title', 'Success')}")
            else:
                formatted.append(f"  ✗ {action['action']}: Failed - {action.get('error', 'Unknown error')}")
        return "\n".join(formatted)

    def _extract_rule_citations(self, text: str) -> List[str]:
        """Extract Florida and Federal rule citations"""
        patterns = [
            r'Fla\.\s*R\.\s*Civ\.\s*P\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'Fla\.\s*R\.\s*Crim\.\s*P\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'Fla\.\s*R\.\s*App\.\s*P\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'Fla\.\s*R\.\s*Jud\.\s*Admin\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'F\.R\.C\.P\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'FRCP\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'Florida Rule[\s\w]*[\d\.]+(?:\([a-z0-9]+\))?',
        ]

        citations = []
        for pattern in patterns:
            citations.extend(re.findall(pattern, text, re.IGNORECASE))

        return list(set(citations))  # Remove duplicates
