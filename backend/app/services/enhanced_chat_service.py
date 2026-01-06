"""
Enhanced Chat Service - Ultimate RAG-powered docketing assistant
Uses Claude with tool calling, RAG context, and comprehensive case awareness
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from anthropic import Anthropic
import json

from app.services.rag_service import rag_service
from app.services.chat_tools import CHAT_TOOLS, ChatToolExecutor
from app.models.case import Case
from app.models.chat_message import ChatMessage
from app.config import settings


class EnhancedChatService:
    """
    Ultimate RAG-powered docketing assistant

    Features:
    - Deep case context awareness via RAG
    - Tool calling for actual modifications
    - Beautiful formatted responses with citations
    - Natural language understanding
    - Proactive suggestions
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.DEFAULT_AI_MODEL

    async def process_message(
        self,
        user_message: str,
        case_id: str,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process user message with full RAG context and tool calling

        Returns:
            {
                'response': str,  # Formatted markdown response
                'actions_taken': List[Dict],  # Tools executed
                'citations': List[str],  # Rule citations
                'message_id': str,  # Saved message ID
                'tokens_used': int
            }
        """

        # Get case
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {'error': 'Case not found'}

        # Get conversation history (last 10 messages for context)
        history = db.query(ChatMessage).filter(
            ChatMessage.case_id == case_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()
        history.reverse()  # Chronological order

        # Get comprehensive case context using RAG
        case_context = await rag_service.get_case_context(
            case_id=case_id,
            user_query=user_message,
            db=db
        )

        # Build system prompt
        system_prompt = self._build_system_prompt(case, case_context)

        # Build conversation messages
        messages = self._build_messages(history, user_message, case_context)

        # Initialize tool executor
        tool_executor = ChatToolExecutor(case_id=case_id, user_id=user_id, db=db)

        # Call Claude with tools
        actions_taken = []
        response_text = ""
        total_tokens = 0

        try:
            # Initial API call with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=CHAT_TOOLS
            )

            total_tokens += response.usage.input_tokens + response.usage.output_tokens

            # Process response - may include tool calls
            while response.stop_reason == "tool_use":
                # Extract text content
                for block in response.content:
                    if block.type == "text":
                        response_text += block.text

                # Execute tools
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Execute tool
                        result = tool_executor.execute_tool(
                            tool_name=block.name,
                            tool_input=block.input
                        )

                        actions_taken.append({
                            'tool': block.name,
                            'input': block.input,
                            'result': result
                        })

                        # Add tool result to conversation
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                # Continue conversation with tool results
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # Get next response
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=CHAT_TOOLS
                )

                total_tokens += response.usage.input_tokens + response.usage.output_tokens

            # Final response text
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

        except Exception as e:
            return {
                'error': f'AI processing failed: {str(e)}',
                'response': "I encountered an error processing your request. Please try again.",
                'actions_taken': [],
                'citations': [],
                'tokens_used': 0
            }

        # Extract rule citations
        citations = self._extract_rule_citations(response_text)

        # Sanitize actions_taken to ensure JSON serializability
        sanitized_actions = []
        for action in actions_taken:
            try:
                # Convert to JSON and back to remove circular refs and complex objects
                sanitized = json.loads(json.dumps(action, default=str))
                sanitized_actions.append(sanitized)
            except (TypeError, ValueError):
                # If serialization fails, create a simple fallback
                sanitized_actions.append({
                    'tool': str(action.get('tool', 'unknown')),
                    'input': str(action.get('input', {})),
                    'result': str(action.get('result', {}))
                })

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
            content=response_text,
            context_rules=citations,
            tokens_used=total_tokens,
            model_used=self.model
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return {
            'response': response_text,
            'actions_taken': sanitized_actions,  # Use sanitized version
            'citations': citations,
            'message_id': str(assistant_msg.id),
            'tokens_used': total_tokens
        }

    def _build_system_prompt(self, case: Case, context: Dict) -> str:
        """Build comprehensive system prompt with case context"""

        # Analyze case state for intelligent guidance
        case_intelligence = self._analyze_case_state(case, context)

        return f"""You are an expert Florida legal docketing assistant with deep knowledge of:
- Florida Rules of Civil Procedure
- Florida Rules of Criminal Procedure
- Florida Rules of Appellate Procedure
- Federal Rules of Civil Procedure (FRCP)
- Federal Rules of Appellate Procedure (FRAP)
- All 20 Florida judicial circuits' local rules
- Advanced trigger-based deadline automation

## YOUR ROLE

You are the AI assistant for **{case.case_number}** in **{case.court}**.
Your job is to help manage this case's docket, deadlines, and procedural requirements.

## CASE INFORMATION

**Case:** {case.case_number} - {case.title}
**Court:** {case.court}
**Judge:** {case.judge}
**Type:** {case.case_type} ({case.jurisdiction})
**Filing Date:** {case.filing_date.isoformat() if case.filing_date else 'Not set'}

**Parties:**
{self._format_parties(case.parties or [])}

**Documents on File:** {len(context.get('documents', []))} documents
**Active Deadlines:** {len(context.get('deadlines', {}).get('upcoming', []))} upcoming deadlines
**Trigger Events Set:** {len(context.get('deadlines', {}).get('trigger_events', []))}

## YOUR CAPABILITIES - FULL SYSTEM CONTROL

You have **20 tools** giving you complete control over the case management system (including cascade updates!):

### Deadline Management (6 tools)
1. **create_deadline** - Add manual deadlines
2. **create_trigger_deadline** - Create trigger events that auto-generate dependent deadlines
3. **update_deadline** - Modify existing deadlines (date, status, priority). Phase 1: Auto-detects manual overrides!
4. **delete_deadline** - Remove deadlines (confirm first!)
5. **query_deadlines** - Search and filter deadlines
6. **bulk_update_deadlines** - Update multiple deadlines at once (mark all as completed, cancel all, etc.)

### Cascade Updates (3 NEW tools!)
7. **preview_cascade_update** - Preview what happens if parent trigger changes (shows protected vs updating deadlines)
8. **apply_cascade_update** - Apply cascade update to parent + all dependents (respects manual overrides!)
9. **get_dependency_tree** - See full trigger/dependent structure for the case

### Case Management (4 tools)
10. **create_case** - Create entirely new cases in the system
11. **update_case_info** - Update any case field (judge, court, status, jurisdiction, district, circuit, etc.)
12. **close_case** - Close/archive cases with smart deadline handling
13. **get_case_statistics** - Get analytics (deadline counts, document counts, breakdowns by type/priority)

### Document Management (3 tools)
14. **delete_document** - Delete documents from cases
15. **rename_document** - Rename documents or change their type classification
16. **search_documents** - Search through case documents by name, type, or content

### Party Management (2 tools)
17. **add_party** - Add parties (plaintiff, defendant, attorneys, etc.) to cases
18. **remove_party** - Remove parties from cases

### Export & Analytics (2 tools)
19. **export_deadlines** - Export to CSV, iCal, or JSON for external use
20. **get_available_templates** - See all 13 rule templates available

**YOU CAN DO EVERYTHING A USER CAN DO VIA THE UI - AND MORE!**

## CRITICAL PRINCIPLES

1. **USE TRIGGER DEADLINES WHENEVER POSSIBLE**
   - For trial dates, mediation dates, service dates, appeal dates → use create_trigger_deadline
   - This auto-generates ALL dependent deadlines automatically
   - Example: "Set trial date" → 5+ deadlines auto-created

2. **CASCADE UPDATE WORKFLOW** 🔥
   When user wants to change a parent trigger deadline:
   a) ALWAYS call `preview_cascade_update` FIRST to show what will happen
   b) Explain to user:
      - How many dependents will update
      - Which are protected (manually overridden)
      - How many days everything will shift
   c) ASK user to confirm before applying
   d) If confirmed, call `apply_cascade_update`

   Example flow:
   User: "Move trial date to July 1"
   You: [Call preview_cascade_update]
        "Trial date will shift by 15 days. This will update 4 dependent deadlines.
         1 deadline (MSJ) was manually changed and will stay protected.
         Should I apply this update?"
   User: "Yes"
   You: [Call apply_cascade_update]
        "✓ Updated trial date and 4 dependent deadlines. MSJ deadline protected."

3. **RESPECT MANUAL OVERRIDES (Phase 1)**
   - When user manually changes a calculated deadline date, it becomes "protected"
   - Protected deadlines will NOT change during cascade updates
   - Always warn user when they manually override: "This will be protected from auto-recalc"

4. **BE PROACTIVE**
   - Suggest trigger events when appropriate
   - Warn about upcoming critical deadlines
   - Identify potential conflicts
   - Recommend next steps
   - Offer to show dependency tree when helpful

5. **SHOW YOUR WORK**
   - Always cite applicable rules
   - Explain deadline calculations
   - Show service method impact (mail +5 days, email +0 since 2019)
   - Consider weekends and holidays

4. **FORMAT BEAUTIFULLY**
   - Use markdown for structure
   - Use **bold** for important info
   - Use bullet points for clarity
   - Use tables when showing multiple items

5. **CONFIRM BEFORE DESTRUCTIVE ACTIONS**
   - Ask before deleting deadlines
   - Confirm when changing critical dates
   - Explain implications

## AVAILABLE RULE TEMPLATES

We have 13 comprehensive templates:
- **FL_CIV_ANSWER** - Answer to Complaint (20 days)
- **FL_CIV_TRIAL** - Trial date (generates 5 dependent deadlines)
- **FL_CIV_MEDIATION** - Mediation conference (generates 2 deadlines)
- **FL_CIV_CMO** - Case management order
- **FED_CIV_ANSWER** - Federal answer (21 days)
- **FED_CIV_PRETRIAL_CONF** - Federal pretrial conference
- **FED_CIV_EXPERT_DISC** - Expert disclosures (generates 3 deadlines)
- **FL_APP_NOTICE** - Florida notice of appeal
- **FL_APP_BRIEF** - Florida appellate briefs (generates 3 deadlines)
- **FED_APP_NOTICE** - Federal notice of appeal
- **FED_APP_BRIEF** - Federal appellate briefs (generates 3 deadlines)

## RELEVANT CONTEXT

Recent documents show:
{self._format_relevant_excerpts(context.get('relevant_excerpts', []))}

## INTELLIGENT CASE ANALYSIS

{case_intelligence['summary']}

**Urgent Matters:**
{self._format_list(case_intelligence.get('urgent_matters', []))}

**Recommended Next Steps:**
{self._format_list(case_intelligence.get('next_steps', []))}

**Potential Issues:**
{self._format_list(case_intelligence.get('issues', []))}

Be helpful, accurate, and proactive. You're their docketing expert!"""

    def _build_messages(
        self,
        history: List[ChatMessage],
        current_message: str,
        context: Dict
    ) -> List[Dict]:
        """Build conversation messages for Claude API"""

        messages = []

        # Add conversation history
        for msg in history[-5:]:  # Last 5 exchanges
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current message with context
        context_summary = f"""**Current Question:** {current_message}

**Quick Context:**
- **Upcoming Deadlines:** {len(context.get('deadlines', {}).get('upcoming', []))}
- **Documents:** {len(context.get('documents', []))}
- **Trigger Events:** {len(context.get('deadlines', {}).get('trigger_events', []))}

{self._format_upcoming_deadlines(context.get('deadlines', {}).get('upcoming', []))}
"""

        messages.append({
            "role": "user",
            "content": context_summary
        })

        return messages

    def _format_parties(self, parties: List[Dict]) -> str:
        """Format parties list"""
        if not parties:
            return "- No parties listed"

        formatted = []
        for party in parties:
            role = party.get('role', 'Unknown')
            name = party.get('name', 'Unknown')
            formatted.append(f"- **{role}:** {name}")

        return "\n".join(formatted)

    def _format_relevant_excerpts(self, excerpts: List[Dict]) -> str:
        """Format relevant document excerpts from RAG"""
        if not excerpts:
            return "- No directly relevant excerpts found"

        formatted = []
        for i, excerpt in enumerate(excerpts[:3], 1):
            text = excerpt['text'][:200] + "..." if len(excerpt['text']) > 200 else excerpt['text']
            formatted.append(f"{i}. {text} (similarity: {excerpt['similarity']})")

        return "\n".join(formatted)

    def _format_upcoming_deadlines(self, deadlines: List[Dict]) -> str:
        """Format upcoming deadlines"""
        if not deadlines:
            return "**No upcoming deadlines**"

        formatted = ["**Upcoming Deadlines:**"]
        for d in deadlines[:5]:
            priority_icon = {
                'fatal': '🔴',
                'critical': '🟠',
                'important': '🟡',
                'standard': '🔵',
                'informational': '⚪'
            }.get(d.get('priority'), '⚪')

            calculated = " [AUTO-CALC]" if d.get('is_calculated') else ""
            formatted.append(f"- {priority_icon} **{d['date']}**: {d['title']}{calculated}")

        return "\n".join(formatted)

    def _analyze_case_state(self, case: Case, context: Dict) -> Dict[str, Any]:
        """
        Intelligent case analysis to provide proactive guidance
        Returns urgent matters, next steps, and potential issues
        """
        from datetime import datetime, timedelta

        deadlines = context.get('deadlines', {})
        upcoming = deadlines.get('upcoming', [])
        trigger_events = deadlines.get('trigger_events', [])
        documents_count = len(context.get('documents', []))

        urgent_matters = []
        next_steps = []
        issues = []

        # Check for urgent deadlines (within 7 days)
        now = datetime.now()
        for deadline in upcoming[:10]:
            try:
                # Handle both date and datetime objects
                date_str = deadline['date']
                if isinstance(date_str, str):
                    # Parse ISO format string
                    if 'T' in date_str:
                        deadline_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        # Date only string, convert to datetime
                        from datetime import date as date_type
                        deadline_date = datetime.combine(datetime.fromisoformat(date_str).date(), datetime.min.time())
                else:
                    # Already a date or datetime object
                    if isinstance(date_str, datetime):
                        deadline_date = date_str
                    else:
                        deadline_date = datetime.combine(date_str, datetime.min.time())

                days_until = (deadline_date.replace(tzinfo=None) - now).days

                if days_until <= 0:
                    urgent_matters.append(f"⚠️ OVERDUE: {deadline['title']} was due {abs(days_until)} days ago!")
                elif days_until <= 3:
                    urgent_matters.append(f"🔴 CRITICAL: {deadline['title']} due in {days_until} days ({deadline['date']})")
                elif days_until <= 7:
                    urgent_matters.append(f"🟠 URGENT: {deadline['title']} due in {days_until} days ({deadline['date']})")
            except (ValueError, TypeError, KeyError) as e:
                # Skip deadlines with invalid date formats - not critical for summary
                continue

        # Check for missing critical elements
        if not trigger_events:
            next_steps.append("Consider setting up trigger events (trial date, service date, etc.) for automatic deadline generation")

        if documents_count == 0:
            issues.append("No documents uploaded yet - consider uploading the complaint or initial pleading")

        if not case.filing_date:
            issues.append("Filing date not set - this may affect deadline calculations")

        # Check for trial date
        has_trial = any('trial' in d.get('title', '').lower() for d in upcoming)
        if not has_trial and case.case_type in ['civil', 'Civil']:
            next_steps.append("No trial date set - consider creating a trial date trigger to auto-generate all pretrial deadlines")

        # Check for answer deadline (early in case)
        has_answer = any('answer' in d.get('title', '').lower() for d in upcoming)
        if not has_answer and documents_count <= 2:
            next_steps.append("If complaint was recently served, create an answer deadline trigger")

        # Deadline density check (too many deadlines in short window)
        if len(upcoming) > 10:
            deadline_dates = []
            for d in upcoming[:15]:
                try:
                    date_val = d['date']
                    if isinstance(date_val, str):
                        if 'T' in date_val:
                            dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                        else:
                            dt = datetime.combine(datetime.fromisoformat(date_val).date(), datetime.min.time())
                    elif isinstance(date_val, datetime):
                        dt = date_val
                    else:
                        dt = datetime.combine(date_val, datetime.min.time())
                    deadline_dates.append(dt.replace(tzinfo=None))
                except (ValueError, TypeError, AttributeError):
                    # Skip deadlines with unparseable dates for density analysis
                    continue

            if deadline_dates:
                deadline_dates.sort()
                # Check for clusters (5+ deadlines within 14 days)
                for i in range(len(deadline_dates) - 4):
                    window = (deadline_dates[i+4] - deadline_dates[i]).days
                    if window <= 14:
                        issues.append(f"⚠️ Deadline cluster detected: 5 deadlines within {window} days starting {deadline_dates[i].date()}")
                        break

        # Build summary
        if not urgent_matters and not issues:
            summary = "✅ Case docket is in good shape. All deadlines under control."
        elif urgent_matters:
            summary = f"🚨 ATTENTION REQUIRED: {len(urgent_matters)} urgent deadline(s) need immediate attention."
        elif issues:
            summary = f"⚠️ {len(issues)} potential issue(s) detected in case management."
        else:
            summary = "Case analysis complete."

        return {
            'summary': summary,
            'urgent_matters': urgent_matters or ["None - all clear!"],
            'next_steps': next_steps or ["Continue monitoring deadlines"],
            'issues': issues or ["None detected"]
        }

    def _format_list(self, items: List[str]) -> str:
        """Format a list of items"""
        if not items or items == ["None detected"] or items == ["None - all clear!"] or items == ["Continue monitoring deadlines"]:
            return "- " + (items[0] if items else "None")

        return "\n".join(f"- {item}" for item in items)

    def _extract_rule_citations(self, text: str) -> List[str]:
        """Extract Florida and Federal rule citations"""
        import re

        patterns = [
            r'Fla\.\s*R\.\s*Civ\.\s*P\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'Fla\.\s*R\.\s*Crim\.\s*P\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'Fla\.\s*R\.\s*App\.\s*P\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'F\.R\.C\.P\.\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'FRCP\s*[\d\.]+(?:\([a-z0-9]+\))?',
            r'FRAP\s*[\d\.]+(?:\([a-z0-9]+\))?',
        ]

        citations = []
        for pattern in patterns:
            citations.extend(re.findall(pattern, text, re.IGNORECASE))

        return list(set(citations))  # Remove duplicates


# Singleton instance
enhanced_chat_service = EnhancedChatService()
