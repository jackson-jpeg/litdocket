"""
Enhanced Chat Service - Ultimate RAG-powered docketing assistant
Uses Claude with tool calling, RAG context, and comprehensive case awareness

Production-hardened with:
- Explicit API timeouts (120s default)
- Retry logic with exponential backoff
- Graceful degradation on RAG failures
- Comprehensive error handling and logging
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from anthropic import Anthropic, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError
import json
import logging
import time

from app.services.rag_service import rag_service
from app.services.chat_tools import CHAT_TOOLS, ChatToolExecutor
from app.models.case import Case
from app.models.chat_message import ChatMessage
from app.config import settings

logger = logging.getLogger(__name__)

# Configuration constants
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds
API_TIMEOUT = 120  # seconds


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
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=API_TIMEOUT
        )
        self.model = settings.DEFAULT_AI_MODEL
        logger.info(f"EnhancedChatService initialized with model: {self.model}")

    def _call_claude_with_retry(
        self,
        system: str,
        messages: List[Dict],
        tools: List[Dict],
        max_tokens: int = 4096
    ) -> Any:
        """
        Call Claude API with retry logic and exponential backoff.

        Handles:
        - Timeouts (retry with longer timeout)
        - Connection errors (retry)
        - Rate limits (wait and retry)
        - Other API errors (fail fast)
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Claude API call attempt {attempt + 1}/{MAX_RETRIES}")

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                    tools=tools
                )

                return response

            except APITimeoutError as e:
                last_error = e
                logger.warning(f"Claude API timeout (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))

            except APIConnectionError as e:
                last_error = e
                logger.warning(f"Claude API connection error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))

            except RateLimitError as e:
                last_error = e
                logger.warning(f"Claude API rate limited (attempt {attempt + 1}): {e}")
                # Rate limits need longer waits
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5 * (2 ** attempt))  # 5s, 10s, 20s

            except APIStatusError as e:
                # Don't retry 4xx errors (client errors)
                if 400 <= e.status_code < 500:
                    logger.error(f"Claude API client error (no retry): {e}")
                    raise
                last_error = e
                logger.warning(f"Claude API server error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))

        # All retries exhausted
        logger.error(f"Claude API call failed after {MAX_RETRIES} attempts: {last_error}")
        raise last_error

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

        logger.info(f"Processing chat message for case {case_id}: {user_message[:50]}...")

        # Get case
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.warning(f"Case not found: {case_id}")
            return {'error': 'Case not found'}

        # Get conversation history (last 10 messages for context)
        try:
            history = db.query(ChatMessage).filter(
                ChatMessage.case_id == case_id
            ).order_by(ChatMessage.created_at.desc()).limit(10).all()
            history.reverse()  # Chronological order
        except Exception as e:
            logger.error(f"Failed to load chat history: {e}")
            history = []  # Continue without history

        # Get comprehensive case context using RAG (graceful degradation)
        try:
            case_context = await rag_service.get_case_context(
                case_id=case_id,
                user_query=user_message,
                db=db
            )
        except Exception as e:
            logger.error(f"RAG context failed, using minimal context: {e}")
            # Graceful degradation - continue with minimal context
            case_context = {
                'case': {
                    'case_number': case.case_number,
                    'title': case.title,
                    'court': case.court,
                    'judge': case.judge,
                    'case_type': case.case_type,
                    'jurisdiction': case.jurisdiction
                },
                'documents': [],
                'deadlines': {'upcoming': [], 'trigger_events': []},
                'relevant_excerpts': []
            }

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
            # Initial API call with tools (using retry logic)
            response = self._call_claude_with_retry(
                system=system_prompt,
                messages=messages,
                tools=CHAT_TOOLS
            )

            total_tokens += response.usage.input_tokens + response.usage.output_tokens
            tool_call_count = 0
            max_tool_calls = 10  # Prevent infinite tool loops

            # Process response - may include tool calls
            while response.stop_reason == "tool_use" and tool_call_count < max_tool_calls:
                tool_call_count += 1
                logger.debug(f"Processing tool call {tool_call_count}")

                # Extract text content
                for block in response.content:
                    if block.type == "text":
                        response_text += block.text

                # Execute tools
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.info(f"Executing tool: {block.name}")

                        # Execute tool with error handling
                        try:
                            result = tool_executor.execute_tool(
                                tool_name=block.name,
                                tool_input=block.input
                            )
                        except Exception as tool_error:
                            logger.error(f"Tool execution failed: {tool_error}")
                            result = {"success": False, "error": str(tool_error)}

                        actions_taken.append({
                            'tool': block.name,
                            'input': block.input,
                            'result': result
                        })

                        # Add tool result to conversation (safely serialize)
                        try:
                            result_json = json.dumps(result, default=str)
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Tool result serialization failed: {e}")
                            result_json = json.dumps({"success": False, "error": "Serialization failed"})

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_json
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

                # Get next response (using retry logic)
                response = self._call_claude_with_retry(
                    system=system_prompt,
                    messages=messages,
                    tools=CHAT_TOOLS
                )

                total_tokens += response.usage.input_tokens + response.usage.output_tokens

            if tool_call_count >= max_tool_calls:
                logger.warning(f"Hit max tool call limit ({max_tool_calls})")

            # Final response text
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

            logger.info(f"Chat response generated successfully. Tokens: {total_tokens}, Tools: {len(actions_taken)}")

        except (APITimeoutError, APIConnectionError) as e:
            logger.error(f"AI service unavailable after retries: {e}")
            return {
                'error': 'AI service temporarily unavailable',
                'response': "I'm experiencing connectivity issues with my AI service. Please try again in a moment.",
                'actions_taken': [],
                'citations': [],
                'message_id': '',
                'tokens_used': 0
            }

        except RateLimitError as e:
            logger.error(f"AI rate limited: {e}")
            return {
                'error': 'AI service rate limited',
                'response': "I'm receiving too many requests right now. Please wait a moment and try again.",
                'actions_taken': [],
                'citations': [],
                'message_id': '',
                'tokens_used': 0
            }

        except Exception as e:
            logger.error(f"Unexpected AI error: {e}", exc_info=True)
            return {
                'error': f'AI processing failed: {str(e)}',
                'response': "I encountered an unexpected error. Please try again or contact support if this persists.",
                'actions_taken': [],
                'citations': [],
                'message_id': '',
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

        # Save messages to database (with error handling)
        message_id = ""
        try:
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
            message_id = str(assistant_msg.id)
            logger.debug(f"Chat messages saved. Message ID: {message_id}")

        except Exception as db_error:
            logger.error(f"Failed to save chat messages: {db_error}")
            db.rollback()
            # Generate a temporary ID since DB save failed
            message_id = f"temp-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return {
            'response': response_text,
            'actions_taken': sanitized_actions,  # Use sanitized version
            'citations': citations,
            'message_id': message_id,
            'tokens_used': total_tokens
        }

    def _build_system_prompt(self, case: Case, context: Dict) -> str:
        """Build comprehensive system prompt with case context and court rules knowledge"""

        # Import court rules knowledge
        from app.constants.court_rules_knowledge import (
            format_rules_for_ai_context,
            get_rule_details,
            get_local_rules
        )

        # Analyze case state for intelligent guidance
        case_intelligence = self._analyze_case_state(case, context)

        # Get relevant court rules for this case's jurisdiction
        jurisdiction = case.jurisdiction or 'florida_state'
        circuit = getattr(case, 'circuit', None) or '11th'  # Default to Miami-Dade
        rules_context = format_rules_for_ai_context(jurisdiction=jurisdiction, circuit=circuit)  # Returns comprehensive rules with circuit-specific local rules

        return f"""# THE DOCKET OVERSEER

You are **The Docket Overseer** — an elite AI docketing specialist with encyclopedic knowledge of Florida and Federal court rules, local circuit rules, and deadline calculations. You have complete authority over this case's docket and can modify ANY aspect of the case on command.

## YOUR IDENTITY & AUTHORITY

You are not just an assistant — you are **the definitive authority** on this case's procedural requirements. Attorneys trust you with their most critical deadlines because you:
- Know every rule citation by heart
- Calculate deadlines with mathematical precision
- Understand the cascading implications of every date change
- Proactively identify risks before they become malpractice

**Your jurisdiction:** You have FULL control over case {case.case_number}. You can edit, add, remove, and modify ANYTHING.

---

## ACTIVE CASE FILE

**Case:** {case.case_number} — *{case.title}*
**Court:** {case.court}
**Judge:** {case.judge or 'Not assigned'}
**Case Type:** {case.case_type} | **Jurisdiction:** {case.jurisdiction}
**Filing Date:** {case.filing_date.isoformat() if case.filing_date else 'Not set'}
**Status:** {case.status or 'Active'}

**Parties:**
{self._format_parties(case.parties or [])}

**Docket Status:**
- 📁 Documents on file: {len(context.get('documents', []))}
- ⏰ Active deadlines: {len(context.get('deadlines', {}).get('upcoming', []))}
- 🎯 Trigger events: {len(context.get('deadlines', {}).get('trigger_events', []))}

---

## YOUR COMPLETE TOOLKIT (26 TOOLS)

### 📅 DEADLINE CONTROL (6 tools)
| Tool | Function | Use When |
|------|----------|----------|
| `create_deadline` | Create manual deadline | User specifies exact date/task |
| `create_trigger_deadline` | Create trigger that auto-generates dependents | Setting trial, service, mediation dates |
| `update_deadline` | Modify date/status/priority | Changing any deadline field |
| `delete_deadline` | Remove deadline | **CONFIRM FIRST** for important deadlines |
| `query_deadlines` | Search/filter deadlines | "What's due next week?" |
| `bulk_update_deadlines` | Mass status change | "Mark all discovery deadlines complete" |

### 🔄 CASCADE SYSTEM (3 tools)
| Tool | Function | Use When |
|------|----------|----------|
| `preview_cascade_update` | Preview dependent changes | **ALWAYS** before changing trigger dates |
| `apply_cascade_update` | Apply cascade to all dependents | After user confirms preview |
| `get_dependency_tree` | Show full trigger/dependent structure | Understanding case timeline |

### 📋 CASE CONTROL (4 tools)
| Tool | Function | Use When |
|------|----------|----------|
| `update_case_info` | Edit ANY case field | Change judge, case number, court, parties, etc. |
| `create_case` | Create new case | New matter to track |
| `close_case` | Archive with deadline handling | Case resolved/settled |
| `get_case_statistics` | Analytics dashboard | Overview requests |

### 📄 DOCUMENT CONTROL (3 tools)
| Tool | Function | Use When |
|------|----------|----------|
| `delete_document` | Remove document | Wrong file, duplicate |
| `rename_document` | Change name/type | Reclassify documents |
| `search_documents` | Find documents | Searching case files |

### 👥 PARTY CONTROL (2 tools)
| Tool | Function | Use When |
|------|----------|----------|
| `add_party` | Add party to case | New plaintiff/defendant/attorney |
| `remove_party` | Remove party | Dismissed party, withdrawn counsel |

### 📊 EXPORT & RULES (4 tools)
| Tool | Function | Use When |
|------|----------|----------|
| `export_deadlines` | Export to CSV/iCal/JSON | Calendar sync, reports |
| `get_available_templates` | List rule templates | Exploring automation options |
| `lookup_court_rule` | Get specific rule details | Rule citation needed |
| `calculate_deadline` | Calculate deadline with full audit | Deadline verification |

---

## COURT RULES KNOWLEDGE BASE

{rules_context}

---

## CRITICAL OPERATING PRINCIPLES

### 1. TRIGGER DEADLINES ARE SUPREME
When setting major dates (trial, mediation, service, appeal), **ALWAYS use `create_trigger_deadline`** to auto-generate all dependent deadlines. Never manually create individual deadlines when a trigger template exists.

### 2. CASCADE WORKFLOW (MANDATORY)
When ANY trigger date changes:
```
1. preview_cascade_update → Show user what will change
2. WAIT for user confirmation
3. apply_cascade_update → Execute only after approval
```
**NEVER skip the preview step for trigger deadlines.**

### 3. DEADLINE CALCULATION TRANSPARENCY
For EVERY deadline you create or discuss, show:
- **Base rule** (e.g., "Fla. R. Civ. P. 1.140(a)(1)")
- **Calculation method** (calendar days vs court days)
- **Service extension** (mail +5 days FL state, +3 days federal)
- **Weekend/holiday adjustment** ("Dec 25 → Dec 26")
- **Final date** with confidence

### 4. CONFIRMATION REQUIRED FOR:
- ❌ Deleting ANY deadline
- ❌ Deleting documents
- ❌ Removing parties
- ❌ Closing cases
- ❌ Changing case number
- ❌ Bulk status updates

For these, ALWAYS ask: "Are you sure you want to [action]? This will [consequence]."

### 5. DIRECT ACTION FOR:
- ✅ Adding deadlines
- ✅ Adding parties
- ✅ Changing case title
- ✅ Changing judge
- ✅ Changing court
- ✅ Querying deadlines
- ✅ Searching documents
- ✅ Exporting data

For these, execute immediately and report results.

### 6. SERVICE DATE vs FILING DATE (CRITICAL)
**ALWAYS use SERVICE DATE as the trigger, not filing date.**
- Filing date = when document was filed with clerk
- Service date = when opposing party received it
- Service date is typically 1-2 days AFTER filing
- Florida Rule 2.514 deadlines run from SERVICE DATE

---

## INTELLIGENT CASE ANALYSIS

{case_intelligence['summary']}

**🚨 Urgent Matters:**
{self._format_list(case_intelligence.get('urgent_matters', []))}

**📋 Recommended Actions:**
{self._format_list(case_intelligence.get('next_steps', []))}

**⚠️ Potential Issues:**
{self._format_list(case_intelligence.get('issues', []))}

---

## RELEVANT CASE CONTEXT

{self._format_relevant_excerpts(context.get('relevant_excerpts', []))}

---

## RESPONSE FORMAT

Use clean markdown formatting:
- **Bold** for important dates, rules, and warnings
- Tables for multiple deadlines
- Code blocks for calculations
- Clear headers for organization
- ✓ checkmarks for completed actions
- ⚠️ warnings for risks
- 📋 for procedural guidance

**You are The Docket Overseer. Act with confidence and precision. Your calculations protect attorneys from malpractice.**"""

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
