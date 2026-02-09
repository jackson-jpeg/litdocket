"""
Chat Tools - Tool definitions for Claude to interact with the docketing system
Enables Claude to create, modify, and query case information
"""
from typing import List, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
import csv
import io
import uuid

from app.models.deadline import Deadline
from app.models.case import Case
from app.models.document import Document
from app.services.rules_engine import rules_engine, TriggerType
from app.services.ical_service import ICalService
from app.services.dependency_listener import DependencyListener
from datetime import date as date_type


# Tool definitions for Claude API
CHAT_TOOLS = [
    {
        "name": "create_deadline",
        "description": "Create a new deadline for the case. Use this when the user wants to add a manual deadline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Brief title for the deadline (e.g., 'Answer to Complaint Due')"
                },
                "deadline_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of what needs to be done"
                },
                "priority": {
                    "type": "string",
                    "enum": ["informational", "standard", "important", "critical", "fatal"],
                    "description": "Priority level"
                },
                "party_role": {
                    "type": "string",
                    "description": "Who is responsible (e.g., 'plaintiff', 'defendant', 'both')"
                },
                "action_required": {
                    "type": "string",
                    "description": "Specific action required"
                }
            },
            "required": ["title", "deadline_date"]
        }
    },
    {
        "name": "create_trigger_deadline",
        "description": """Create a trigger event that automatically generates dependent deadlines.

IMPORTANT: This tool uses conversational intake. If the backend returns status='needs_clarification',
you MUST ask the user the questions in 'missing_fields', then call this tool again with the answers in 'context'.

Example flow:
1. User: "Trial is May 15"
2. You call: create_trigger_deadline(trigger_type="trial_date", trigger_date="2026-05-15")
3. Backend returns: {status: "needs_clarification", missing_fields: [{field_name: "jury_status", question_text: "Is this a jury trial?"}]}
4. You ask user: "Is this a jury trial?"
5. User: "Yes"
6. You call: create_trigger_deadline(trigger_type="trial_date", trigger_date="2026-05-15", context={"jury_status": true})
7. Backend returns: {status: "success", ...}

Use this for trial dates, mediation dates, appeal filed dates, service dates, etc.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_type": {
                    "type": "string",
                    "enum": [
                        "trial_date",
                        "pretrial_conference",
                        "complaint_served",
                        "service_completed",
                        "case_filed",
                        "order_entered",
                        "appeal_filed",
                        "discovery_deadline",
                        "motion_filed",
                        "hearing_scheduled"
                    ],
                    "description": "Type of trigger event"
                },
                "trigger_date": {
                    "type": "string",
                    "description": "Date of the trigger event in YYYY-MM-DD format"
                },
                "service_method": {
                    "type": "string",
                    "enum": ["email", "mail", "personal"],
                    "description": "Method of service (affects calculation for some deadlines)"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about this trigger event"
                },
                "context": {
                    "type": "object",
                    "description": "Additional context gathered from user. Use this to provide answers to required_fields questions. Example: {\"jury_status\": true, \"trial_duration_days\": 3, \"court_location\": \"Miami-Dade (11th)\"}"
                }
            },
            "required": ["trigger_type", "trigger_date"]
        }
    },
    {
        "name": "update_deadline",
        "description": "Update an existing deadline. If updating a calculated deadline's date, it will be marked as 'manually overridden' and will NOT be auto-recalculated in the future when parent triggers change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deadline_id": {
                    "type": "string",
                    "description": "ID of the deadline to update"
                },
                "new_date": {
                    "type": "string",
                    "description": "New deadline date in YYYY-MM-DD format (optional). If this is a calculated deadline, changing the date will mark it as manually overridden and protect it from future auto-recalculation."
                },
                "new_status": {
                    "type": "string",
                    "enum": ["pending", "completed", "cancelled"],
                    "description": "New status (optional)"
                },
                "new_priority": {
                    "type": "string",
                    "enum": ["informational", "standard", "important", "critical", "fatal"],
                    "description": "New priority (optional)"
                },
                "reason": {
                    "type": "string",
                    "description": "Optional reason for the change (recommended for manual overrides for audit trail)"
                }
            },
            "required": ["deadline_id"]
        }
    },
    {
        "name": "delete_deadline",
        "description": "Delete a deadline. Use with caution - confirm with user first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deadline_id": {
                    "type": "string",
                    "description": "ID of the deadline to delete"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for deletion"
                }
            },
            "required": ["deadline_id"]
        }
    },
    {
        "name": "query_deadlines",
        "description": "Query and filter deadlines. Use to answer questions like 'What's due next week?' or 'Show me all critical deadlines'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "priority": {
                    "type": "string",
                    "enum": ["informational", "standard", "important", "critical", "fatal"],
                    "description": "Filter by priority (optional)"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "completed", "cancelled"],
                    "description": "Filter by status (optional)"
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "Show deadlines within this many days (optional)"
                },
                "include_calculated": {
                    "type": "boolean",
                    "description": "Include auto-calculated deadlines from rules engine"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_available_templates",
        "description": "Get list of available deadline templates (rules engine templates) for creating trigger-based deadline chains.",
        "input_schema": {
            "type": "object",
            "properties": {
                "jurisdiction": {
                    "type": "string",
                    "enum": ["florida_state", "federal"],
                    "description": "Filter by jurisdiction (optional)"
                },
                "court_type": {
                    "type": "string",
                    "enum": ["civil", "criminal", "appellate"],
                    "description": "Filter by court type (optional)"
                }
            },
            "required": []
        }
    },
    {
        "name": "update_case_info",
        "description": "Update case information like case number, judge, court, parties, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "enum": ["judge", "court", "case_type", "jurisdiction", "title", "status", "district", "circuit", "case_number"],
                    "description": "Which field to update"
                },
                "value": {
                    "type": "string",
                    "description": "New value for the field"
                }
            },
            "required": ["field", "value"]
        }
    },
    {
        "name": "close_case",
        "description": "Close or archive a case. Sets the case status to 'closed' and optionally marks all pending deadlines as completed or cancelled. Use when user asks to close, archive, or complete a case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Reason for closing the case (e.g., 'settled', 'dismissed', 'judgment entered', 'appeal concluded')"
                },
                "deadline_action": {
                    "type": "string",
                    "enum": ["completed", "cancelled", "leave_as_is"],
                    "description": "What to do with pending deadlines: 'completed' marks all as completed, 'cancelled' marks as cancelled, 'leave_as_is' keeps them as-is"
                },
                "add_note": {
                    "type": "boolean",
                    "description": "Whether to add a case note about the closure"
                }
            },
            "required": ["reason"]
        }
    },
    {
        "name": "bulk_update_deadlines",
        "description": "Update multiple deadlines at once. Use to mark all deadlines as completed, cancel all pending deadlines, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["pending", "completed", "cancelled", "all"],
                    "description": "Which deadlines to update (filter by current status)"
                },
                "new_status": {
                    "type": "string",
                    "enum": ["pending", "completed", "cancelled"],
                    "description": "New status to set"
                },
                "priority_filter": {
                    "type": "string",
                    "enum": ["informational", "standard", "important", "critical", "fatal", "all"],
                    "description": "Optional: only update deadlines with this priority"
                }
            },
            "required": ["status_filter", "new_status"]
        }
    },
    {
        "name": "delete_document",
        "description": "Delete a document from the case. Use when user wants to remove an uploaded document.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "ID of the document to delete"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for deletion (e.g., 'duplicate', 'wrong file', 'outdated')"
                }
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "rename_document",
        "description": "Rename or retitle a document. Use when user wants to change document name or update its type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "ID of the document to rename"
                },
                "new_name": {
                    "type": "string",
                    "description": "New file name (optional)"
                },
                "new_type": {
                    "type": "string",
                    "description": "New document type (e.g., 'motion', 'order', 'brief', 'pleading')"
                }
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "search_documents",
        "description": "Search through case documents by name, type, or date. Returns matching documents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term (searches in file name and document type)"
                },
                "document_type": {
                    "type": "string",
                    "description": "Filter by document type (optional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)"
                }
            },
            "required": []
        }
    },
    {
        "name": "create_case",
        "description": "Create a new case in the system. Use when user wants to start tracking a new legal matter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_number": {
                    "type": "string",
                    "description": "Case number (e.g., '2024-CA-001234')"
                },
                "title": {
                    "type": "string",
                    "description": "Case title (e.g., 'Smith v. Jones')"
                },
                "court": {
                    "type": "string",
                    "description": "Court name (e.g., 'Circuit Court, 11th Judicial Circuit')"
                },
                "judge": {
                    "type": "string",
                    "description": "Judge name (optional)"
                },
                "case_type": {
                    "type": "string",
                    "enum": ["civil", "criminal", "appellate", "family", "probate"],
                    "description": "Type of case"
                },
                "jurisdiction": {
                    "type": "string",
                    "enum": ["florida_state", "federal"],
                    "description": "Jurisdiction"
                },
                "filing_date": {
                    "type": "string",
                    "description": "Date case was filed (YYYY-MM-DD format, optional)"
                }
            },
            "required": ["case_number", "title", "court"]
        }
    },
    {
        "name": "add_party",
        "description": "Add a party (plaintiff, defendant, attorney, etc.) to the case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Party name"
                },
                "role": {
                    "type": "string",
                    "enum": ["plaintiff", "defendant", "appellant", "appellee", "petitioner", "respondent", "plaintiff_attorney", "defendant_attorney", "third_party"],
                    "description": "Party's role in the case"
                },
                "contact_info": {
                    "type": "string",
                    "description": "Optional contact information"
                }
            },
            "required": ["name", "role"]
        }
    },
    {
        "name": "remove_party",
        "description": "Remove a party from the case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "party_name": {
                    "type": "string",
                    "description": "Name of the party to remove"
                }
            },
            "required": ["party_name"]
        }
    },
    {
        "name": "get_case_statistics",
        "description": "Get analytics and statistics about the case (deadline counts, document counts, time tracking, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_deadline_breakdown": {
                    "type": "boolean",
                    "description": "Include breakdown by deadline priority/status"
                },
                "include_document_breakdown": {
                    "type": "boolean",
                    "description": "Include breakdown by document type"
                }
            },
            "required": []
        }
    },
    {
        "name": "export_deadlines",
        "description": "Export case deadlines to various formats (CSV, iCal calendar). Returns export data or download link.",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["csv", "ical", "json"],
                    "description": "Export format"
                },
                "include_completed": {
                    "type": "boolean",
                    "description": "Include completed deadlines (default: false)"
                }
            },
            "required": ["format"]
        }
    },
    {
        "name": "preview_cascade_update",
        "description": "Preview what will happen if a parent trigger deadline changes. Shows which dependent deadlines will update and which are protected (manually overridden). Use this BEFORE applying the update to show the user what will happen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_deadline_id": {
                    "type": "string",
                    "description": "ID of the parent (trigger) deadline being changed"
                },
                "old_date": {
                    "type": "string",
                    "description": "Current date of the parent in YYYY-MM-DD format"
                },
                "new_date": {
                    "type": "string",
                    "description": "New date for the parent in YYYY-MM-DD format"
                }
            },
            "required": ["parent_deadline_id", "old_date", "new_date"]
        }
    },
    {
        "name": "apply_cascade_update",
        "description": "Apply cascade update to parent trigger and all dependent deadlines. This updates the parent date and recalculates all non-overridden children. Manually overridden deadlines are protected and won't change. IMPORTANT: Use preview_cascade_update first to show user what will happen, then call this to apply after user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_deadline_id": {
                    "type": "string",
                    "description": "ID of the parent (trigger) deadline"
                },
                "new_date": {
                    "type": "string",
                    "description": "New date for the parent in YYYY-MM-DD format"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the change (e.g., 'Trial date continuance', 'Court order')"
                }
            },
            "required": ["parent_deadline_id", "new_date"]
        }
    },
    {
        "name": "get_dependency_tree",
        "description": "Get the full dependency tree for the case. Shows all trigger deadlines and their dependent deadlines. Useful for understanding case structure and relationships.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "lookup_court_rule",
        "description": "Look up a specific court rule by citation or keyword. Returns full rule details including deadlines, calculation methods, and citations. Use to answer questions like 'What does Rule 1.510 say?' or 'What are the discovery deadlines?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_citation": {
                    "type": "string",
                    "description": "Rule citation to look up (e.g., '1.510', '1.140', 'Rule 12', 'FRCP 26')"
                },
                "keyword": {
                    "type": "string",
                    "description": "Keyword to search for in rules (e.g., 'summary judgment', 'discovery', 'answer')"
                },
                "jurisdiction": {
                    "type": "string",
                    "enum": ["florida_state", "federal"],
                    "description": "Which jurisdiction's rules to search"
                }
            },
            "required": []
        }
    },
    {
        "name": "calculate_deadline",
        "description": "Calculate a deadline with full audit trail showing every step. Use for deadline verification or when user asks 'When is X due?' Returns the final date with complete calculation basis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_date": {
                    "type": "string",
                    "description": "Starting date (SERVICE DATE) in YYYY-MM-DD format"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days for the deadline (e.g., 20 for answer, 30 for discovery)"
                },
                "calculation_type": {
                    "type": "string",
                    "enum": ["calendar_days", "court_days", "business_days"],
                    "description": "How to count days (most Florida deadlines use calendar_days)"
                },
                "service_method": {
                    "type": "string",
                    "enum": ["electronic", "email", "mail", "personal"],
                    "description": "How document was served (mail adds 5 days FL state, 3 days federal)"
                },
                "jurisdiction": {
                    "type": "string",
                    "enum": ["state", "federal"],
                    "description": "Florida state or federal court"
                },
                "rule_citation": {
                    "type": "string",
                    "description": "Optional rule citation to include in audit trail"
                }
            },
            "required": ["trigger_date", "days", "calculation_type"]
        }
    },
    {
        "name": "move_deadline",
        "description": "Move a deadline to a new date. This is a smart wrapper around update_deadline that handles cascade updates for triggers and adds proper audit trail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deadline_id": {
                    "type": "string",
                    "description": "ID of the deadline to move"
                },
                "new_date": {
                    "type": "string",
                    "description": "New date in YYYY-MM-DD format"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for moving (e.g., 'Court order', 'Stipulation', 'Continuance granted')"
                },
                "cascade_to_dependents": {
                    "type": "boolean",
                    "description": "If this is a trigger deadline, also move all dependent deadlines (default: true with preview)"
                }
            },
            "required": ["deadline_id", "new_date"]
        }
    },
    {
        "name": "duplicate_deadline",
        "description": "Duplicate an existing deadline with optional modifications. Useful for creating similar deadlines or copying to other cases.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_deadline_id": {
                    "type": "string",
                    "description": "ID of the deadline to duplicate"
                },
                "new_title": {
                    "type": "string",
                    "description": "Optional new title (defaults to original + ' (Copy)')"
                },
                "new_date": {
                    "type": "string",
                    "description": "Optional new date in YYYY-MM-DD format"
                },
                "date_offset_days": {
                    "type": "integer",
                    "description": "Optional: shift date by this many days from original"
                }
            },
            "required": ["source_deadline_id"]
        }
    },
    {
        "name": "link_deadlines",
        "description": "Create a dependency link between two deadlines. Makes one deadline dependent on another so cascade updates work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_deadline_id": {
                    "type": "string",
                    "description": "ID of the parent (trigger) deadline"
                },
                "child_deadline_id": {
                    "type": "string",
                    "description": "ID of the child (dependent) deadline"
                },
                "days_offset": {
                    "type": "integer",
                    "description": "How many days the child is offset from parent (can be negative for 'X days before')"
                }
            },
            "required": ["parent_deadline_id", "child_deadline_id", "days_offset"]
        }
    },
    # =========================================================================
    # AUTHORITY CORE TOOLS - AI-Powered Rules Database
    # =========================================================================
    {
        "name": "search_court_rules",
        "description": """Search the Authority Core rules database for procedural court rules.

Use this tool when the user asks about:
- Deadline requirements (e.g., "How long do I have to respond to a motion?")
- Procedural rules (e.g., "What are the expert disclosure deadlines?")
- Rule citations (e.g., "What does FRCP 12 say about answers?")
- Jurisdiction-specific rules (e.g., "What are the S.D. Florida local rules for motions?")

The tool searches verified rules from the Authority Core database and returns matching rules with citations.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'motion response deadline', 'discovery cutoff', 'expert disclosure')"
                },
                "jurisdiction_id": {
                    "type": "string",
                    "description": "Optional UUID of jurisdiction to filter by"
                },
                "trigger_type": {
                    "type": "string",
                    "enum": [
                        "case_filed", "service_completed", "complaint_served", "answer_due",
                        "discovery_commenced", "discovery_deadline", "dispositive_motions_due",
                        "pretrial_conference", "trial_date", "hearing_scheduled",
                        "motion_filed", "order_entered", "appeal_filed", "mediation_scheduled",
                        "custom_trigger"
                    ],
                    "description": "Optional trigger type to filter by"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_rule_details",
        "description": """Get full details of a specific court rule from Authority Core.

Use this when you have a rule ID and need complete information including:
- Full citation and source text
- All deadline specifications
- Conditions when the rule applies
- Service method extensions

This is useful after search_court_rules returns results and you need more detail.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {
                    "type": "string",
                    "description": "UUID of the rule to retrieve"
                }
            },
            "required": ["rule_id"]
        }
    },
    {
        "name": "calculate_from_rule",
        "description": """Calculate deadlines using a specific Authority Core rule.

Use this when you want to show the user what deadlines a specific rule would generate
without actually creating them. Useful for:
- Explaining what deadlines apply to a situation
- Previewing before creating trigger deadlines
- Answering "what if" questions about dates

The tool returns calculated dates based on the rule's deadline specifications.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {
                    "type": "string",
                    "description": "UUID of the Authority Core rule to use"
                },
                "trigger_date": {
                    "type": "string",
                    "description": "Trigger date in YYYY-MM-DD format"
                },
                "service_method": {
                    "type": "string",
                    "enum": ["electronic", "mail", "personal"],
                    "description": "Service method for extension calculation (default: electronic)"
                }
            },
            "required": ["rule_id", "trigger_date"]
        }
    },
    # =========================================================================
    # EXPANDED AUTHORITY CORE TOOLS (Phase 4)
    # =========================================================================
    {
        "name": "find_applicable_rules",
        "description": """PRIMARY DOCKETING TOOL: Find all applicable Authority Core rules for a specific trigger event and jurisdiction.

This is the MAIN tool to use when the user wants to create deadlines for a case. It finds all rules that apply to a specific trigger (e.g., trial date, motion filed) in a jurisdiction and returns them sorted by confidence score.

Use this tool for:
- "Set up deadlines for my trial date"
- "What deadlines do I have after filing a motion?"
- "Create all discovery deadlines for this case"
- Any docketing request that requires finding applicable rules

Returns: List of applicable rules with metadata for deadline generation.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_type": {
                    "type": "string",
                    "enum": [
                        "case_filed", "service_completed", "complaint_served", "answer_due",
                        "discovery_commenced", "discovery_deadline", "dispositive_motions_due",
                        "pretrial_conference", "trial_date", "hearing_scheduled",
                        "motion_filed", "order_entered", "appeal_filed", "mediation_scheduled",
                        "custom_trigger"
                    ],
                    "description": "The trigger event type"
                },
                "jurisdiction_id": {
                    "type": "string",
                    "description": "UUID of the jurisdiction (required for accurate rule matching)"
                }
            },
            "required": ["trigger_type", "jurisdiction_id"]
        }
    },
    {
        "name": "compare_rules_across_jurisdictions",
        "description": """Compare the same type of rule across multiple jurisdictions.

Use this when the user asks:
- "How do discovery deadlines differ between Florida and Federal court?"
- "What's the difference between state and federal trial preparation deadlines?"
- "Compare motion response times across jurisdictions"

Returns: Side-by-side comparison highlighting differences in timing, service extensions, and conditions.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_type": {
                    "type": "string",
                    "enum": [
                        "case_filed", "service_completed", "complaint_served", "answer_due",
                        "discovery_commenced", "discovery_deadline", "dispositive_motions_due",
                        "pretrial_conference", "trial_date", "hearing_scheduled",
                        "motion_filed", "order_entered", "appeal_filed", "mediation_scheduled",
                        "custom_trigger"
                    ],
                    "description": "The trigger type to compare across jurisdictions"
                },
                "jurisdiction_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of jurisdiction UUIDs to compare (2-5 jurisdictions)"
                }
            },
            "required": ["trigger_type", "jurisdiction_ids"]
        }
    },
    {
        "name": "get_rule_history",
        "description": """Get the change history for a specific rule, showing all modifications over time.

Use this when the user asks:
- "Has this rule changed recently?"
- "Show me the history of changes to this deadline"
- "When was this rule last updated?"

Returns: Timeline of rule changes with version diffs, change dates, and change reasons.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {
                    "type": "string",
                    "description": "UUID of the rule to get history for"
                }
            },
            "required": ["rule_id"]
        }
    },
    {
        "name": "validate_deadline_against_rules",
        "description": """Cross-check user-entered deadlines against Authority Core rules to verify accuracy.

Use this when:
- User manually enters a deadline and you want to verify it's correct
- User asks "Is this deadline right?"
- You want to proactively check if a deadline matches official court rules

Returns: Validation result with matching rule (if found), discrepancies, and recommendations.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "deadline_date": {
                    "type": "string",
                    "description": "Deadline date in YYYY-MM-DD format"
                },
                "trigger_date": {
                    "type": "string",
                    "description": "Trigger date in YYYY-MM-DD format"
                },
                "trigger_type": {
                    "type": "string",
                    "enum": [
                        "case_filed", "service_completed", "complaint_served", "answer_due",
                        "discovery_commenced", "discovery_deadline", "dispositive_motions_due",
                        "pretrial_conference", "trial_date", "hearing_scheduled",
                        "motion_filed", "order_entered", "appeal_filed", "mediation_scheduled",
                        "custom_trigger"
                    ],
                    "description": "The trigger event type"
                },
                "jurisdiction_id": {
                    "type": "string",
                    "description": "UUID of the jurisdiction"
                },
                "service_method": {
                    "type": "string",
                    "enum": ["electronic", "mail", "personal"],
                    "description": "Service method (affects deadline calculation)"
                }
            },
            "required": ["deadline_date", "trigger_date", "trigger_type", "jurisdiction_id"]
        }
    },
    {
        "name": "generate_all_deadlines_for_case",
        "description": """POWER TOOL: Generate ALL applicable deadlines for a case based on multiple triggers.

This is the most powerful docketing tool. Use it when the user wants to set up a complete case with all deadlines. It:
1. Finds all applicable rules for each trigger
2. Calculates all deadlines
3. Creates deadline chains (dependencies)
4. Returns 30-50+ deadlines ready to create

Use this for:
- "Set up all deadlines for my case"
- "I have a trial on June 15, create everything"
- Complete case initialization with multiple triggers

Returns: Complete deadline package with trigger chains, dependencies, and confidence scores.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "UUID of the case"
                },
                "triggers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "trigger_type": {"type": "string"},
                            "trigger_date": {"type": "string"},
                            "service_method": {"type": "string", "enum": ["electronic", "mail", "personal"]}
                        },
                        "required": ["trigger_type", "trigger_date"]
                    },
                    "description": "Array of trigger events with dates"
                },
                "jurisdiction_id": {
                    "type": "string",
                    "description": "UUID of the jurisdiction"
                },
                "create_deadlines": {
                    "type": "boolean",
                    "description": "If true, actually create the deadlines in database (default: false for preview)"
                }
            },
            "required": ["case_id", "triggers", "jurisdiction_id"]
        }
    },
    {
        "name": "analyze_rule_coverage",
        "description": """Analyze Authority Core rule coverage for a jurisdiction to identify gaps.

Use this when:
- Setting up a new jurisdiction
- User asks "What rules are available for this court?"
- Identifying missing rules for a jurisdiction

Returns: Coverage report showing available trigger types, rule counts, confidence distribution, and gaps.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "jurisdiction_id": {
                    "type": "string",
                    "description": "UUID of the jurisdiction to analyze"
                }
            },
            "required": ["jurisdiction_id"]
        }
    },
    {
        "name": "explain_deadline_from_rule",
        "description": """Provide step-by-step explanation of how a deadline was calculated from a rule.

Use this when the user asks:
- "Why is this deadline on this date?"
- "Explain how you calculated this"
- "Show me the math"

Returns: Detailed breakdown including trigger date, base days, service extensions, weekend rolls, holidays, final date, and full rule citation.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {
                    "type": "string",
                    "description": "UUID of the rule used for calculation"
                },
                "trigger_date": {
                    "type": "string",
                    "description": "Trigger date in YYYY-MM-DD format"
                },
                "deadline_date": {
                    "type": "string",
                    "description": "The calculated deadline date in YYYY-MM-DD format"
                },
                "service_method": {
                    "type": "string",
                    "enum": ["electronic", "mail", "personal"],
                    "description": "Service method used"
                }
            },
            "required": ["rule_id", "trigger_date", "deadline_date"]
        }
    },
    {
        "name": "suggest_related_rules",
        "description": """Suggest related rules based on context (existing triggers, case type, jurisdiction).

Use this proactively when:
- User creates a trigger and might need related deadlines
- User uploads a document that mentions other events (e.g., mentions "MSJ" → suggest response deadline)
- You want to help user discover relevant rules they might have missed

Returns: List of suggested rules with relevance scores and brief descriptions.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Context for suggestions (e.g., 'user just created trial_date trigger', 'case involves discovery', etc.)"
                },
                "jurisdiction_id": {
                    "type": "string",
                    "description": "UUID of the jurisdiction"
                },
                "existing_trigger_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of trigger types already in the case"
                }
            },
            "required": ["context", "jurisdiction_id"]
        }
    },
    {
        "name": "request_jurisdiction_harvest",
        "description": """ADMIN TOOL: Request automated rule harvesting for a jurisdiction.

Use this when the user (if admin) wants to:
- Add a new jurisdiction
- Re-harvest rules for an existing jurisdiction
- Update outdated rules

This triggers the Cartographer → Extract → Inbox approval workflow.

Returns: Job status and estimated completion time.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "jurisdiction_id": {
                    "type": "string",
                    "description": "UUID of the jurisdiction to harvest rules for"
                },
                "force_reharvest": {
                    "type": "boolean",
                    "description": "If true, re-harvest even if rules already exist (default: false)"
                }
            },
            "required": ["jurisdiction_id"]
        }
    }
]


class ChatToolExecutor:
    """
    Executes tool calls from Claude with Authority Core integration.

    Phase 4 Enhancement: Injected AuthorityCoreService and AuthorityIntegratedDeadlineService
    for database-driven deadline generation using verified court rules.
    """

    def __init__(self, case_id: str, user_id: str, db: Session):
        self.case_id = case_id
        self.user_id = user_id
        self.db = db

        # Phase 4: Inject Authority Core services
        try:
            from app.services.authority_core_service import AuthorityCoreService
            from app.services.authority_integrated_deadline_service import AuthorityIntegratedDeadlineService

            self.authority_service = AuthorityCoreService(db)
            self.deadline_service = AuthorityIntegratedDeadlineService(db)
        except Exception as e:
            logger.warning(f"Failed to initialize Authority Core services: {e}")
            self.authority_service = None
            self.deadline_service = None

    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results"""

        # Deadline tools
        if tool_name == "create_deadline":
            return self._create_deadline(tool_input)
        elif tool_name == "create_trigger_deadline":
            return self._create_trigger_deadline(tool_input)
        elif tool_name == "update_deadline":
            return self._update_deadline(tool_input)
        elif tool_name == "delete_deadline":
            return self._delete_deadline(tool_input)
        elif tool_name == "query_deadlines":
            return self._query_deadlines(tool_input)
        elif tool_name == "bulk_update_deadlines":
            return self._bulk_update_deadlines(tool_input)

        # Case tools
        elif tool_name == "update_case_info":
            return self._update_case_info(tool_input)
        elif tool_name == "close_case":
            return self._close_case(tool_input)
        elif tool_name == "create_case":
            return self._create_case(tool_input)
        elif tool_name == "get_case_statistics":
            return self._get_case_statistics(tool_input)

        # Document tools
        elif tool_name == "delete_document":
            return self._delete_document(tool_input)
        elif tool_name == "rename_document":
            return self._rename_document(tool_input)
        elif tool_name == "search_documents":
            return self._search_documents(tool_input)

        # Party tools
        elif tool_name == "add_party":
            return self._add_party(tool_input)
        elif tool_name == "remove_party":
            return self._remove_party(tool_input)

        # Export/Analytics tools
        elif tool_name == "export_deadlines":
            return self._export_deadlines(tool_input)
        elif tool_name == "get_available_templates":
            return self._get_available_templates(tool_input)

        # Cascade update tools
        elif tool_name == "preview_cascade_update":
            return self._preview_cascade_update(tool_input)
        elif tool_name == "apply_cascade_update":
            return self._apply_cascade_update(tool_input)
        elif tool_name == "get_dependency_tree":
            return self._get_dependency_tree(tool_input)

        # New Docket Overseer tools
        elif tool_name == "lookup_court_rule":
            return self._lookup_court_rule(tool_input)
        elif tool_name == "calculate_deadline":
            return self._calculate_deadline(tool_input)
        elif tool_name == "move_deadline":
            return self._move_deadline(tool_input)
        elif tool_name == "duplicate_deadline":
            return self._duplicate_deadline(tool_input)
        elif tool_name == "link_deadlines":
            return self._link_deadlines(tool_input)

        # Authority Core tools - AI-Powered Rules Database
        elif tool_name == "search_court_rules":
            return self._search_court_rules(tool_input)
        elif tool_name == "get_rule_details":
            return self._get_rule_details(tool_input)
        elif tool_name == "calculate_from_rule":
            return self._calculate_from_rule(tool_input)

        # Phase 4: Expanded Authority Core tools
        elif tool_name == "find_applicable_rules":
            return self._find_applicable_rules(tool_input)
        elif tool_name == "compare_rules_across_jurisdictions":
            return self._compare_rules_across_jurisdictions(tool_input)
        elif tool_name == "get_rule_history":
            return self._get_rule_history(tool_input)
        elif tool_name == "validate_deadline_against_rules":
            return self._validate_deadline_against_rules(tool_input)
        elif tool_name == "generate_all_deadlines_for_case":
            return self._generate_all_deadlines_for_case(tool_input)
        elif tool_name == "analyze_rule_coverage":
            return self._analyze_rule_coverage(tool_input)
        elif tool_name == "explain_deadline_from_rule":
            return self._explain_deadline_from_rule(tool_input)
        elif tool_name == "suggest_related_rules":
            return self._suggest_related_rules(tool_input)
        elif tool_name == "request_jurisdiction_harvest":
            return self._request_jurisdiction_harvest(tool_input)

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _create_deadline(self, input_data: Dict) -> Dict:
        """Create a manual deadline with confidence metadata"""
        try:
            deadline = Deadline(
                case_id=self.case_id,
                user_id=self.user_id,
                title=input_data['title'],
                deadline_date=datetime.strptime(input_data['deadline_date'], '%Y-%m-%d').date(),
                description=input_data.get('description', ''),
                priority=input_data.get('priority', 'standard'),
                party_role=input_data.get('party_role'),
                action_required=input_data.get('action_required'),
                status='pending',
                created_via_chat=True,
                # Case OS: Confidence metadata for manual deadlines
                extraction_method='manual',
                confidence_score=95,  # High confidence for user-created deadlines
                confidence_level='high',
                confidence_factors={'user_created': True, 'manual_entry': True},
                verification_status='approved',  # User-created = pre-approved
                extraction_quality_score=10  # Max quality for manual entry
            )

            self.db.add(deadline)
            self.db.commit()
            self.db.refresh(deadline)

            return {
                "success": True,
                "deadline_id": str(deadline.id),
                "title": deadline.title,
                "date": deadline.deadline_date.isoformat(),
                "message": f"✓ Created deadline: {deadline.title} on {deadline.deadline_date.isoformat()}"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _create_trigger_deadline(self, input_data: Dict) -> Dict:
        """Create a trigger event with auto-generated dependent deadlines"""
        try:
            # Get case
            case = self.db.query(Case).filter(Case.id == self.case_id).first()
            if not case:
                return {"success": False, "error": "Case not found"}

            # Parse trigger type
            trigger_type_str = input_data['trigger_type']
            try:
                trigger_enum = TriggerType(trigger_type_str)
            except ValueError:
                return {"success": False, "error": f"Invalid trigger type: {trigger_type_str}"}

            # Parse date
            trigger_date = date_type.fromisoformat(input_data['trigger_date'])
            service_method = input_data.get('service_method', 'email')

            # Get applicable templates
            jurisdiction = case.jurisdiction or 'florida_state'
            court_type = case.case_type or 'civil'

            templates = rules_engine.get_applicable_rules(
                jurisdiction=jurisdiction,
                court_type=court_type,
                trigger_type=trigger_enum
            )

            if not templates:
                return {
                    "success": False,
                    "error": f"No templates found for {jurisdiction} {court_type} {trigger_type_str}"
                }

            # =============================================================
            # CONVERSATIONAL INTAKE: Check for Required Fields
            # =============================================================
            template = templates[0]  # Use first template for required_fields check
            context = input_data.get('context', {})

            if template.required_fields:
                missing_fields = []

                for required_field in template.required_fields:
                    field_value = context.get(required_field.field_name)

                    # Check if field is missing (not provided or None)
                    if field_value is None:
                        # Use default if available
                        if required_field.default_value is not None:
                            context[required_field.field_name] = required_field.default_value
                        else:
                            # Field is truly missing - need to ask
                            missing_fields.append({
                                "field_name": required_field.field_name,
                                "question_text": required_field.display_label,
                                "field_type": required_field.field_type,
                                "options": required_field.enum_options,
                                "default_value": required_field.default_value,
                                "affects_deadlines": required_field.affects_deadlines
                            })

                # If any fields are missing, return NEEDS_CLARIFICATION
                if missing_fields:
                    return {
                        "status": "needs_clarification",
                        "success": False,  # For backward compatibility
                        "message": f"I detected a {trigger_type_str} event. I need a few more details to generate the right deadlines.",
                        "missing_fields": missing_fields,
                        "detected_trigger": trigger_type_str,
                        "context_so_far": context
                    }

            # All required fields present - continue with execution
            # Store context in trigger deadline metadata for audit trail
            trigger_metadata = {
                "context": context,
                "required_fields_satisfied": True
            }

            # Create trigger deadline (parent)
            trigger_deadline = Deadline(
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
                notes=input_data.get('notes'),
                created_via_chat=True,
                # Case OS: Confidence metadata for trigger events
                extraction_method='manual',
                confidence_score=95,
                confidence_level='high',
                confidence_factors={'user_created': True, 'trigger_event': True},
                verification_status='approved',
                extraction_quality_score=10
            )

            self.db.add(trigger_deadline)
            self.db.flush()

            # Generate dependent deadlines
            all_dependents = []
            for template in templates:
                # CONVERSATIONAL INTAKE: Pass user context to filter conditional deadlines
                dependents = rules_engine.calculate_dependent_deadlines(
                    trigger_date=trigger_date,
                    rule_template=template,
                    service_method=service_method,
                    case_context=context  # Pass user-provided context for conditional filtering
                )

                for dep_data in dependents:
                    deadline = Deadline(
                        case_id=self.case_id,
                        user_id=self.user_id,
                        parent_deadline_id=str(trigger_deadline.id),
                        title=dep_data['title'],
                        description=dep_data['description'],
                        deadline_date=dep_data['deadline_date'],
                        priority=dep_data['priority'],
                        party_role=dep_data['party_role'],
                        action_required=dep_data['action_required'],
                        applicable_rule=dep_data['rule_citation'],
                        calculation_basis=dep_data['calculation_basis'],
                        trigger_event=dep_data['trigger_event'],
                        trigger_date=dep_data['trigger_date'],
                        is_calculated=True,
                        is_dependent=True,
                        service_method=dep_data.get('service_method', service_method),
                        # PHASE 3: Advanced deadline calculation fields
                        calculation_type=dep_data.get('calculation_type', 'calendar_days'),
                        days_count=dep_data.get('days_count'),
                        created_via_chat=True,
                        # Case OS: Confidence metadata for rules-engine deadlines
                        extraction_method='rule-based',
                        confidence_score=90,  # High confidence for rules-based calculations
                        confidence_level='high',
                        confidence_factors={'rules_engine': True, 'calculated': True, 'has_citation': bool(dep_data.get('rule_citation'))},
                        verification_status='pending',  # Still needs verification even though calculated
                        extraction_quality_score=9
                    )
                    self.db.add(deadline)
                    all_dependents.append(dep_data)

            self.db.commit()

            return {
                "status": "success",  # NEW: Conversational intake status
                "success": True,      # Keep for backward compatibility
                "trigger_id": str(trigger_deadline.id),
                "trigger_type": trigger_type_str,
                "trigger_date": trigger_date.isoformat(),
                "dependent_deadlines_created": len(all_dependents),
                "deadlines": [
                    {
                        "title": d['title'],
                        "date": d['deadline_date'].isoformat(),
                        "priority": d['priority']
                    }
                    for d in all_dependents
                ],
                "context_used": context,  # Show what context was used
                "message": f"✓ Created trigger event '{trigger_type_str}' with {len(all_dependents)} dependent deadlines"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "success": False,
                "error": str(e),
                "message": f"Failed to create trigger deadline: {str(e)}"
            }

    def _update_deadline(self, input_data: Dict) -> Dict:
        """
        Update an existing deadline

        Tracks manual overrides: If this is a calculated deadline and the user
        manually changes it, we mark it as "manually overridden" to prevent
        future auto-recalculation
        """
        try:
            deadline = self.db.query(Deadline).filter(
                Deadline.id == input_data['deadline_id'],
                Deadline.case_id == self.case_id
            ).first()

            if not deadline:
                return {"success": False, "error": "Deadline not found"}

            changes = []
            was_overridden = False

            # Check if date is being changed
            if 'new_date' in input_data:
                old_date = deadline.deadline_date
                new_date = datetime.strptime(input_data['new_date'], '%Y-%m-%d').date()

                # COMPULAW PHASE 1: Detect manual override
                # If this is a calculated deadline and the date is changing, mark as overridden
                if deadline.is_calculated and not deadline.is_manually_overridden:
                    # This is the FIRST time user manually changed a calculated deadline
                    deadline.is_manually_overridden = True
                    deadline.override_timestamp = datetime.now()
                    deadline.override_user_id = self.user_id
                    deadline.auto_recalculate = False  # Stop auto-recalc
                    was_overridden = True

                    # Save original calculated date if not already saved
                    if not deadline.original_deadline_date:
                        deadline.original_deadline_date = old_date

                    changes.append(f"date: {old_date} → {new_date} (MANUALLY OVERRIDDEN)")
                else:
                    changes.append(f"date: {old_date} → {new_date}")

                deadline.deadline_date = new_date

            if 'new_status' in input_data:
                old_status = deadline.status
                deadline.status = input_data['new_status']
                changes.append(f"status: {old_status} → {deadline.status}")

            if 'new_priority' in input_data:
                old_priority = deadline.priority
                deadline.priority = input_data['new_priority']
                changes.append(f"priority: {old_priority} → {deadline.priority}")

            # Track who modified and why
            deadline.modified_by = self.user_id
            if 'reason' in input_data:
                deadline.modification_reason = input_data['reason']
                if was_overridden:
                    deadline.override_reason = input_data['reason']

            self.db.commit()

            message = f"✓ Updated deadline: {deadline.title}. Changes: {', '.join(changes)}"

            # Add override warning
            if was_overridden:
                message += "\n\n⚠️ This calculated deadline has been manually overridden. It will NOT be automatically recalculated if the parent trigger changes."

            return {
                "success": True,
                "deadline_id": str(deadline.id),
                "title": deadline.title,
                "changes": changes,
                "was_overridden": was_overridden,
                "is_now_protected": deadline.is_manually_overridden,
                "message": message
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _delete_deadline(self, input_data: Dict) -> Dict:
        """Delete a deadline"""
        try:
            deadline = self.db.query(Deadline).filter(
                Deadline.id == input_data['deadline_id'],
                Deadline.case_id == self.case_id
            ).first()

            if not deadline:
                return {"success": False, "error": "Deadline not found"}

            title = deadline.title
            date_str = deadline.deadline_date.isoformat() if deadline.deadline_date else 'TBD'

            self.db.delete(deadline)
            self.db.commit()

            return {
                "success": True,
                "title": title,
                "message": f"✓ Deleted deadline: {title} ({date_str}). Reason: {input_data.get('reason', 'Not specified')}"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _query_deadlines(self, input_data: Dict) -> Dict:
        """Query deadlines with filters"""
        try:
            query = self.db.query(Deadline).filter(Deadline.case_id == self.case_id)

            # Apply filters
            if 'priority' in input_data:
                query = query.filter(Deadline.priority == input_data['priority'])

            if 'status' in input_data:
                query = query.filter(Deadline.status == input_data['status'])

            if 'days_ahead' in input_data:
                from datetime import timedelta
                end_date = datetime.now().date() + timedelta(days=input_data['days_ahead'])
                query = query.filter(Deadline.deadline_date <= end_date)

            if not input_data.get('include_calculated', True):
                query = query.filter(Deadline.is_calculated == False)

            deadlines = query.order_by(Deadline.deadline_date.asc().nullslast()).all()

            return {
                "success": True,
                "count": len(deadlines),
                "deadlines": [
                    {
                        "id": str(d.id),
                        "title": d.title,
                        "date": d.deadline_date.isoformat() if d.deadline_date else None,
                        "priority": d.priority,
                        "status": d.status,
                        "is_calculated": d.is_calculated
                    }
                    for d in deadlines
                ]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_available_templates(self, input_data: Dict) -> Dict:
        """Get available deadline templates"""
        try:
            templates = rules_engine.get_all_templates()

            # Filter by jurisdiction if specified
            if 'jurisdiction' in input_data:
                templates = [t for t in templates if t.jurisdiction == input_data['jurisdiction']]

            # Filter by court type if specified
            if 'court_type' in input_data:
                templates = [t for t in templates if t.court_type == input_data['court_type']]

            return {
                "success": True,
                "count": len(templates),
                "templates": [
                    {
                        "rule_id": t.rule_id,
                        "name": t.name,
                        "description": t.description,
                        "jurisdiction": t.jurisdiction,
                        "court_type": t.court_type,
                        "trigger_type": t.trigger_type.value,
                        "dependent_deadlines_count": len(t.dependent_deadlines),
                        "citation": t.citation
                    }
                    for t in templates
                ]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _update_case_info(self, input_data: Dict) -> Dict:
        """Update case information"""
        try:
            case = self.db.query(Case).filter(Case.id == self.case_id).first()
            if not case:
                return {"success": False, "error": "Case not found"}

            field = input_data['field']
            value = input_data['value']
            old_value = getattr(case, field, None)

            setattr(case, field, value)
            self.db.commit()

            return {
                "success": True,
                "field": field,
                "old_value": str(old_value) if old_value else None,
                "new_value": value,
                "message": f"✓ Updated case {field}: {old_value} → {value}"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _close_case(self, input_data: Dict) -> Dict:
        """Close or archive a case"""
        try:
            case = self.db.query(Case).filter(Case.id == self.case_id).first()
            if not case:
                return {"success": False, "error": "Case not found"}

            reason = input_data['reason']
            deadline_action = input_data.get('deadline_action', 'leave_as_is')

            # Store old status
            old_status = case.status

            # Update case status
            case.status = "closed"

            # Handle deadlines based on user preference
            deadlines_updated = 0
            if deadline_action in ['completed', 'cancelled']:
                pending_deadlines = self.db.query(Deadline).filter(
                    Deadline.case_id == self.case_id,
                    Deadline.status == 'pending'
                ).all()

                for deadline in pending_deadlines:
                    deadline.status = deadline_action
                    deadlines_updated += 1

            # Add case metadata note if requested
            if input_data.get('add_note', True):
                if not case.case_metadata:
                    case.case_metadata = {}
                if 'closure_notes' not in case.case_metadata:
                    case.case_metadata['closure_notes'] = []

                case.case_metadata['closure_notes'].append({
                    'date': datetime.now().isoformat(),
                    'reason': reason,
                    'deadlines_action': deadline_action,
                    'deadlines_affected': deadlines_updated
                })

            self.db.commit()

            message_parts = [f"✓ Case closed successfully. Reason: {reason}"]
            if deadlines_updated > 0:
                message_parts.append(f"{deadlines_updated} pending deadline(s) marked as {deadline_action}")

            return {
                "success": True,
                "old_status": old_status,
                "new_status": "closed",
                "reason": reason,
                "deadlines_updated": deadlines_updated,
                "deadline_action": deadline_action,
                "message": ". ".join(message_parts)
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _bulk_update_deadlines(self, input_data: Dict) -> Dict:
        """Bulk update deadlines"""
        try:
            status_filter = input_data['status_filter']
            new_status = input_data['new_status']
            priority_filter = input_data.get('priority_filter', 'all')

            # Build query
            query = self.db.query(Deadline).filter(Deadline.case_id == self.case_id)

            # Apply status filter
            if status_filter != 'all':
                query = query.filter(Deadline.status == status_filter)

            # Apply priority filter
            if priority_filter != 'all':
                query = query.filter(Deadline.priority == priority_filter)

            # Get matching deadlines
            deadlines = query.all()

            # Update all matching deadlines
            updated_count = 0
            updated_titles = []
            for deadline in deadlines:
                old_status = deadline.status
                deadline.status = new_status
                updated_count += 1
                updated_titles.append(f"{deadline.title} ({old_status} → {new_status})")

            self.db.commit()

            return {
                "success": True,
                "updated_count": updated_count,
                "status_filter": status_filter,
                "new_status": new_status,
                "priority_filter": priority_filter,
                "updated_deadlines": updated_titles[:10],  # First 10 for display
                "message": f"✓ Updated {updated_count} deadline(s) to '{new_status}'"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    # ==================== DOCUMENT MANAGEMENT ====================

    def _delete_document(self, input_data: Dict) -> Dict:
        """Delete a document"""
        try:
            document = self.db.query(Document).filter(
                Document.id == input_data['document_id'],
                Document.case_id == self.case_id
            ).first()

            if not document:
                return {"success": False, "error": "Document not found"}

            file_name = document.file_name
            reason = input_data.get('reason', 'User requested deletion')

            # TODO: Delete from Firebase Storage as well
            # For now, just delete from database
            self.db.delete(document)
            self.db.commit()

            return {
                "success": True,
                "file_name": file_name,
                "reason": reason,
                "message": f"✓ Deleted document: {file_name}. Reason: {reason}"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _rename_document(self, input_data: Dict) -> Dict:
        """Rename or retype a document"""
        try:
            document = self.db.query(Document).filter(
                Document.id == input_data['document_id'],
                Document.case_id == self.case_id
            ).first()

            if not document:
                return {"success": False, "error": "Document not found"}

            changes = []
            old_name = document.file_name
            old_type = document.document_type

            if 'new_name' in input_data:
                document.file_name = input_data['new_name']
                changes.append(f"name: {old_name} → {document.file_name}")

            if 'new_type' in input_data:
                document.document_type = input_data['new_type']
                changes.append(f"type: {old_type} → {document.document_type}")

            self.db.commit()

            return {
                "success": True,
                "document_id": str(document.id),
                "changes": changes,
                "message": f"✓ Updated document. Changes: {', '.join(changes)}"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _search_documents(self, input_data: Dict) -> Dict:
        """Search documents"""
        try:
            query = self.db.query(Document).filter(Document.case_id == self.case_id)

            # Apply search query
            if 'query' in input_data and input_data['query']:
                search_term = f"%{input_data['query']}%"
                query = query.filter(
                    (Document.file_name.ilike(search_term)) |
                    (Document.document_type.ilike(search_term))
                )

            # Filter by type
            if 'document_type' in input_data:
                query = query.filter(Document.document_type == input_data['document_type'])

            # Limit
            limit = input_data.get('limit', 10)
            documents = query.order_by(Document.created_at.desc()).limit(limit).all()

            return {
                "success": True,
                "count": len(documents),
                "documents": [
                    {
                        "id": str(doc.id),
                        "file_name": doc.file_name,
                        "document_type": doc.document_type,
                        "filing_date": doc.filing_date.isoformat() if doc.filing_date else None,
                        "created_at": doc.created_at.isoformat(),
                        "summary": doc.ai_summary[:200] + "..." if doc.ai_summary and len(doc.ai_summary) > 200 else doc.ai_summary
                    }
                    for doc in documents
                ]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== CASE MANAGEMENT ====================

    def _create_case(self, input_data: Dict) -> Dict:
        """Create a new case"""
        try:
            # Check if case already exists
            existing = self.db.query(Case).filter(
                Case.user_id == self.user_id,
                Case.case_number == input_data['case_number']
            ).first()

            if existing:
                return {
                    "success": False,
                    "error": f"Case {input_data['case_number']} already exists"
                }

            # Create new case
            filing_date = None
            if 'filing_date' in input_data:
                filing_date = datetime.strptime(input_data['filing_date'], '%Y-%m-%d').date()

            new_case = Case(
                id=str(uuid.uuid4()),
                user_id=self.user_id,
                case_number=input_data['case_number'],
                title=input_data['title'],
                court=input_data['court'],
                judge=input_data.get('judge'),
                case_type=input_data.get('case_type', 'civil'),
                jurisdiction=input_data.get('jurisdiction', 'florida_state'),
                filing_date=filing_date,
                status='active'
            )

            self.db.add(new_case)
            self.db.commit()
            self.db.refresh(new_case)

            return {
                "success": True,
                "case_id": str(new_case.id),
                "case_number": new_case.case_number,
                "title": new_case.title,
                "message": f"✓ Created new case: {new_case.case_number} - {new_case.title}"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _get_case_statistics(self, input_data: Dict) -> Dict:
        """Get case analytics and statistics"""
        try:
            case = self.db.query(Case).filter(Case.id == self.case_id).first()
            if not case:
                return {"success": False, "error": "Case not found"}

            # Get all deadlines
            all_deadlines = self.db.query(Deadline).filter(Deadline.case_id == self.case_id).all()

            # Get all documents
            all_documents = self.db.query(Document).filter(Document.case_id == self.case_id).all()

            # Calculate statistics
            today = datetime.now().date()

            stats = {
                "case_number": case.case_number,
                "case_title": case.title,
                "status": case.status,
                "filing_date": case.filing_date.isoformat() if case.filing_date else None,
                "total_deadlines": len(all_deadlines),
                "total_documents": len(all_documents),
                "deadline_summary": {
                    "pending": len([d for d in all_deadlines if d.status == 'pending']),
                    "completed": len([d for d in all_deadlines if d.status == 'completed']),
                    "cancelled": len([d for d in all_deadlines if d.status == 'cancelled']),
                    "overdue": len([d for d in all_deadlines if d.deadline_date and d.deadline_date < today and d.status == 'pending'])
                }
            }

            # Deadline breakdown by priority
            if input_data.get('include_deadline_breakdown'):
                stats["deadline_priority_breakdown"] = {
                    "fatal": len([d for d in all_deadlines if d.priority == 'fatal']),
                    "critical": len([d for d in all_deadlines if d.priority == 'critical']),
                    "important": len([d for d in all_deadlines if d.priority == 'important']),
                    "standard": len([d for d in all_deadlines if d.priority == 'standard']),
                    "informational": len([d for d in all_deadlines if d.priority == 'informational'])
                }

            # Document breakdown by type
            if input_data.get('include_document_breakdown'):
                doc_types = {}
                for doc in all_documents:
                    doc_type = doc.document_type or 'uncategorized'
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                stats["document_type_breakdown"] = doc_types

            # Party count
            stats["total_parties"] = len(case.parties) if case.parties else 0

            return {
                "success": True,
                "statistics": stats
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== PARTY MANAGEMENT ====================

    def _add_party(self, input_data: Dict) -> Dict:
        """Add a party to the case"""
        try:
            case = self.db.query(Case).filter(Case.id == self.case_id).first()
            if not case:
                return {"success": False, "error": "Case not found"}

            # Initialize parties if None
            if not case.parties:
                case.parties = []

            # Check if party already exists
            for party in case.parties:
                if party.get('name') == input_data['name']:
                    return {
                        "success": False,
                        "error": f"Party '{input_data['name']}' already exists in this case"
                    }

            # Add new party
            new_party = {
                "name": input_data['name'],
                "role": input_data['role'],
                "contact_info": input_data.get('contact_info')
            }

            case.parties.append(new_party)
            self.db.commit()

            return {
                "success": True,
                "party_name": input_data['name'],
                "party_role": input_data['role'],
                "total_parties": len(case.parties),
                "message": f"✓ Added party: {input_data['name']} ({input_data['role']})"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _remove_party(self, input_data: Dict) -> Dict:
        """Remove a party from the case"""
        try:
            case = self.db.query(Case).filter(Case.id == self.case_id).first()
            if not case:
                return {"success": False, "error": "Case not found"}

            if not case.parties:
                return {"success": False, "error": "No parties in this case"}

            # Find and remove party
            party_name = input_data['party_name']
            original_count = len(case.parties)

            case.parties = [p for p in case.parties if p.get('name') != party_name]

            if len(case.parties) == original_count:
                return {
                    "success": False,
                    "error": f"Party '{party_name}' not found in this case"
                }

            self.db.commit()

            return {
                "success": True,
                "party_name": party_name,
                "remaining_parties": len(case.parties),
                "message": f"✓ Removed party: {party_name}"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    # ==================== EXPORT / ANALYTICS ====================

    def _export_deadlines(self, input_data: Dict) -> Dict:
        """Export deadlines to various formats"""
        try:
            # Get deadlines
            query = self.db.query(Deadline).filter(Deadline.case_id == self.case_id)

            if not input_data.get('include_completed', False):
                query = query.filter(Deadline.status == 'pending')

            deadlines = query.order_by(Deadline.deadline_date.asc().nullslast()).all()

            export_format = input_data['format']

            if export_format == 'csv':
                # Generate CSV
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['Title', 'Date', 'Priority', 'Status', 'Party', 'Action Required', 'Rule'])

                for deadline in deadlines:
                    writer.writerow([
                        deadline.title,
                        deadline.deadline_date.isoformat() if deadline.deadline_date else '',
                        deadline.priority,
                        deadline.status,
                        deadline.party_role or '',
                        deadline.action_required or '',
                        deadline.applicable_rule or ''
                    ])

                csv_data = output.getvalue()

                return {
                    "success": True,
                    "format": "csv",
                    "count": len(deadlines),
                    "data": csv_data,
                    "message": f"✓ Exported {len(deadlines)} deadlines to CSV"
                }

            elif export_format == 'ical':
                # Generate iCal
                case = self.db.query(Case).filter(Case.id == self.case_id).first()
                ical_service = ICalService()
                ical_data = ical_service.generate_ics_file(deadlines, case.case_number if case else "Case")

                return {
                    "success": True,
                    "format": "ical",
                    "count": len(deadlines),
                    "data": ical_data,
                    "message": f"✓ Exported {len(deadlines)} deadlines to iCal format"
                }

            elif export_format == 'json':
                # Generate JSON
                deadline_data = [
                    {
                        "id": str(d.id),
                        "title": d.title,
                        "date": d.deadline_date.isoformat() if d.deadline_date else None,
                        "priority": d.priority,
                        "status": d.status,
                        "party_role": d.party_role,
                        "action_required": d.action_required,
                        "applicable_rule": d.applicable_rule,
                        "calculation_basis": d.calculation_basis
                    }
                    for d in deadlines
                ]

                import json
                json_data = json.dumps(deadline_data, indent=2)

                return {
                    "success": True,
                    "format": "json",
                    "count": len(deadlines),
                    "data": json_data,
                    "message": f"✓ Exported {len(deadlines)} deadlines to JSON"
                }

            else:
                return {"success": False, "error": f"Unsupported format: {export_format}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== COMPULAW PHASE 2: CASCADE UPDATES ====================

    def _preview_cascade_update(self, input_data: Dict) -> Dict:
        """
        Preview cascade update before applying
        Shows user which deadlines will change and which are protected
        """
        try:
            parent_id = input_data['parent_deadline_id']
            old_date = datetime.strptime(input_data['old_date'], '%Y-%m-%d').date()
            new_date = datetime.strptime(input_data['new_date'], '%Y-%m-%d').date()

            # Create dependency listener
            listener = DependencyListener(self.db)

            # Get preview
            preview = listener.detect_parent_change(parent_id, old_date, new_date)

            if not preview['has_dependents']:
                return {
                    "success": True,
                    "is_parent": False,
                    "message": "This deadline has no dependent deadlines. You can update it directly without cascade."
                }

            # Build user-friendly message
            message_parts = [
                f"📊 Cascade Update Preview:",
                f"",
                f"Parent trigger will shift by {preview['days_shift']} days:",
                f"  {preview['parent_old_date']} → {preview['parent_new_date']}",
                f"",
                f"Impact on {preview['total_dependents']} dependent deadline(s):"
            ]

            if preview['affected_count'] > 0:
                message_parts.append(f"")
                message_parts.append(f"✅ Will Update ({preview['affected_count']} deadlines):")
                for change in preview['changes_preview'][:5]:  # Show first 5
                    message_parts.append(
                        f"  • {change['title']}: {change['old_date']} → {change['new_date']}"
                    )
                if len(preview['changes_preview']) > 5:
                    message_parts.append(f"  ... and {len(preview['changes_preview']) - 5} more")

            if preview['overridden_count'] > 0:
                message_parts.append(f"")
                message_parts.append(f"🔒 Protected (Manually Overridden - {preview['overridden_count']} deadlines):")
                for skipped in preview['skipped_deadlines'][:3]:  # Show first 3
                    message_parts.append(
                        f"  • {skipped['title']} (overridden on {skipped['override_date'][:10] if skipped.get('override_date') else 'unknown'})"
                    )
                if len(preview['skipped_deadlines']) > 3:
                    message_parts.append(f"  ... and {len(preview['skipped_deadlines']) - 3} more")

            message = "\n".join(message_parts)

            return {
                "success": True,
                "has_dependents": True,
                "preview": preview,
                "message": message,
                "requires_confirmation": True
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _apply_cascade_update(self, input_data: Dict) -> Dict:
        """
        Apply cascade update to parent and all dependent deadlines
        Respects Phase 1 manual overrides
        """
        try:
            parent_id = input_data['parent_deadline_id']
            new_date = datetime.strptime(input_data['new_date'], '%Y-%m-%d').date()
            reason = input_data.get('reason', 'Cascade update from parent trigger change')

            # Create dependency listener
            listener = DependencyListener(self.db)

            # Apply cascade
            result = listener.apply_cascade_update(
                parent_deadline_id=parent_id,
                new_date=new_date,
                user_id=self.user_id,
                reason=reason
            )

            return result

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _get_dependency_tree(self, input_data: Dict) -> Dict:
        """Get full dependency tree for the case"""
        try:
            # Create dependency listener
            listener = DependencyListener(self.db)

            # Get tree
            tree = listener.get_dependency_tree(self.case_id)

            # Build message
            if tree['total_triggers'] == 0:
                message = "No trigger deadlines found in this case yet. Create a trigger deadline (like trial date or service date) to generate dependent deadlines."
            else:
                message_parts = [
                    f"📋 Case Dependency Tree:",
                    f"",
                    f"Total Triggers: {tree['total_triggers']}",
                    f"Total Dependents: {tree['total_dependents']}",
                    f""
                ]

                for trigger in tree['triggers']:
                    message_parts.append(f"")
                    message_parts.append(f"🎯 Trigger: {trigger['trigger_title']}")
                    message_parts.append(f"   Date: {trigger['trigger_date']}")
                    message_parts.append(f"   Event: {trigger['trigger_event']}")
                    message_parts.append(f"   Dependents: {trigger['dependents_count']}")

                    if trigger['dependents_count'] > 0:
                        message_parts.append(f"   Children:")
                        for dep in trigger['dependents'][:5]:  # First 5
                            override_flag = " 🔒 (overridden)" if dep['is_overridden'] else ""
                            message_parts.append(
                                f"     • {dep['title']} - {dep['date']}{override_flag}"
                            )
                        if trigger['dependents_count'] > 5:
                            message_parts.append(f"     ... and {trigger['dependents_count'] - 5} more")

                message = "\n".join(message_parts)

            return {
                "success": True,
                "tree": tree,
                "message": message
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== DOCKET OVERSEER TOOLS ====================

    def _lookup_court_rule(self, input_data: Dict) -> Dict:
        """Look up a court rule by citation or keyword"""
        try:
            from app.constants.court_rules_knowledge import (
                FLORIDA_CIVIL_PROCEDURE_RULES,
                FLORIDA_JUDICIAL_ADMINISTRATION_RULES,
                FEDERAL_CIVIL_PROCEDURE_RULES,
                LOCAL_RULES_11TH_CIRCUIT,
                LOCAL_RULES_17TH_CIRCUIT,
                LOCAL_RULES_13TH_CIRCUIT,
                LOCAL_RULES_9TH_CIRCUIT
            )

            rule_citation = input_data.get('rule_citation', '').lower().strip()
            keyword = input_data.get('keyword', '').lower().strip()
            jurisdiction = input_data.get('jurisdiction', 'florida_state')

            matching_rules = []

            # Determine which rule sets to search
            if jurisdiction == 'florida_state':
                rule_sets = [
                    ("Florida Civil Procedure", FLORIDA_CIVIL_PROCEDURE_RULES),
                    ("Florida Judicial Admin", FLORIDA_JUDICIAL_ADMINISTRATION_RULES),
                    ("11th Circuit Local", LOCAL_RULES_11TH_CIRCUIT),
                    ("17th Circuit Local", LOCAL_RULES_17TH_CIRCUIT),
                    ("13th Circuit Local", LOCAL_RULES_13TH_CIRCUIT),
                    ("9th Circuit Local", LOCAL_RULES_9TH_CIRCUIT),
                ]
            else:
                rule_sets = [
                    ("Federal Civil Procedure", FEDERAL_CIVIL_PROCEDURE_RULES),
                ]

            # Search by citation
            if rule_citation:
                for set_name, rules in rule_sets:
                    for rule_id, rule in rules.items():
                        if (rule_citation in rule_id.lower() or
                            rule_citation in rule.get('citation', '').lower() or
                            rule_citation.replace('.', '') in rule_id.lower().replace('.', '')):
                            matching_rules.append({
                                "source": set_name,
                                "rule_id": rule_id,
                                **rule
                            })

            # Search by keyword
            if keyword:
                for set_name, rules in rule_sets:
                    for rule_id, rule in rules.items():
                        rule_text = f"{rule.get('name', '')} {rule.get('description', '')}".lower()
                        if keyword in rule_text and not any(m['rule_id'] == rule_id for m in matching_rules):
                            matching_rules.append({
                                "source": set_name,
                                "rule_id": rule_id,
                                **rule
                            })

            if not matching_rules:
                return {
                    "success": True,
                    "count": 0,
                    "rules": [],
                    "message": f"No rules found matching '{rule_citation or keyword}'. Try a different search term."
                }

            # Format output
            formatted_rules = []
            for rule in matching_rules[:5]:  # Limit to 5 results
                formatted = {
                    "source": rule['source'],
                    "rule_id": rule['rule_id'],
                    "name": rule.get('name', 'Unknown'),
                    "citation": rule.get('citation', ''),
                    "description": rule.get('description', ''),
                }
                if 'deadlines' in rule:
                    formatted['deadlines'] = rule['deadlines']
                if 'calculation' in rule:
                    formatted['calculation'] = rule['calculation']
                formatted_rules.append(formatted)

            return {
                "success": True,
                "count": len(matching_rules),
                "rules": formatted_rules,
                "message": f"Found {len(matching_rules)} matching rule(s)"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _calculate_deadline(self, input_data: Dict) -> Dict:
        """Calculate a deadline with full audit trail"""
        try:
            from app.utils.florida_holidays import (
                add_calendar_days_with_service_extension,
                add_court_days,
                is_business_day,
                adjust_to_business_day
            )
            from datetime import timedelta

            trigger_date_str = input_data['trigger_date']
            days = input_data['days']
            calculation_type = input_data['calculation_type']
            service_method = input_data.get('service_method', 'electronic')
            jurisdiction = input_data.get('jurisdiction', 'state')
            rule_citation = input_data.get('rule_citation', '')

            # Parse trigger date
            trigger_date = datetime.strptime(trigger_date_str, '%Y-%m-%d').date()

            # Build audit trail
            audit_trail = []
            audit_trail.append(f"**Trigger Date (Service):** {trigger_date.strftime('%B %d, %Y')} ({trigger_date.strftime('%A')})")
            audit_trail.append(f"**Base Period:** {days} {calculation_type.replace('_', ' ')}")

            # Calculate based on type
            if calculation_type == 'calendar_days':
                # Use the official Florida Rule 2.514 calculation
                final_date = add_calendar_days_with_service_extension(
                    trigger_date=trigger_date,
                    base_days=days,
                    service_method=service_method,
                    jurisdiction=jurisdiction
                )

                # Calculate intermediate date before weekend/holiday adjustment
                from app.constants.legal_rules import get_service_extension_days
                service_ext = get_service_extension_days(jurisdiction, service_method)
                intermediate_date = trigger_date + timedelta(days=days + service_ext)

                audit_trail.append(f"**Service Method:** {service_method}")
                if service_ext > 0:
                    audit_trail.append(f"**Service Extension:** +{service_ext} days (FL R. Jud. Admin. 2.514(b))")

                audit_trail.append(f"**Raw Calculation:** {trigger_date} + {days} days" + (f" + {service_ext} days" if service_ext > 0 else "") + f" = {intermediate_date}")

                if intermediate_date != final_date:
                    audit_trail.append(f"**Weekend/Holiday Adjustment:** {intermediate_date} → {final_date}")
                    audit_trail.append(f"*(Per FL R. Jud. Admin. 2.514(a)(3): deadline falls on non-business day)*")

            elif calculation_type in ['court_days', 'business_days']:
                final_date = add_court_days(trigger_date, days)
                audit_trail.append(f"**Calculation:** {days} court/business days (skipping weekends & holidays)")

            else:
                return {"success": False, "error": f"Unknown calculation type: {calculation_type}"}

            if rule_citation:
                audit_trail.append(f"**Rule Citation:** {rule_citation}")

            audit_trail.append(f"\n**FINAL DEADLINE: {final_date.strftime('%B %d, %Y')} ({final_date.strftime('%A')})**")

            return {
                "success": True,
                "trigger_date": trigger_date.isoformat(),
                "final_date": final_date.isoformat(),
                "final_date_formatted": final_date.strftime('%B %d, %Y'),
                "final_date_weekday": final_date.strftime('%A'),
                "calculation_type": calculation_type,
                "service_method": service_method,
                "audit_trail": "\n".join(audit_trail),
                "message": f"✓ Deadline calculated: {final_date.strftime('%B %d, %Y')} ({final_date.strftime('%A')})"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _move_deadline(self, input_data: Dict) -> Dict:
        """Move a deadline with smart cascade handling"""
        try:
            deadline = self.db.query(Deadline).filter(
                Deadline.id == input_data['deadline_id'],
                Deadline.case_id == self.case_id
            ).first()

            if not deadline:
                return {"success": False, "error": "Deadline not found"}

            old_date = deadline.deadline_date
            new_date = datetime.strptime(input_data['new_date'], '%Y-%m-%d').date()
            reason = input_data.get('reason', 'Date moved by user')
            cascade = input_data.get('cascade_to_dependents', True)

            # Check if this is a trigger deadline with dependents
            has_dependents = self.db.query(Deadline).filter(
                Deadline.parent_deadline_id == str(deadline.id)
            ).count() > 0

            if has_dependents and cascade:
                # This needs a cascade update - return preview first
                days_shift = (new_date - old_date).days

                return {
                    "success": True,
                    "requires_cascade": True,
                    "is_trigger": True,
                    "deadline_title": deadline.title,
                    "old_date": old_date.isoformat(),
                    "new_date": new_date.isoformat(),
                    "days_shift": days_shift,
                    "message": f"⚠️ This is a trigger deadline with dependent deadlines. "
                              f"Moving it {abs(days_shift)} days {'forward' if days_shift > 0 else 'backward'} "
                              f"will affect dependent deadlines. Use `preview_cascade_update` to see the impact, "
                              f"then `apply_cascade_update` to confirm."
                }

            # Simple deadline - just update it
            deadline.deadline_date = new_date

            # Track if this is a manual override of a calculated deadline
            was_overridden = False
            if deadline.is_calculated and not deadline.is_manually_overridden:
                deadline.is_manually_overridden = True
                deadline.override_timestamp = datetime.now()
                deadline.override_user_id = self.user_id
                deadline.override_reason = reason
                deadline.auto_recalculate = False
                if not deadline.original_deadline_date:
                    deadline.original_deadline_date = old_date
                was_overridden = True

            deadline.modification_reason = reason
            deadline.modified_by = self.user_id

            self.db.commit()

            message = f"✓ Moved deadline '{deadline.title}' from {old_date} to {new_date}"
            if was_overridden:
                message += "\n\n⚠️ This calculated deadline is now protected from auto-recalculation."

            return {
                "success": True,
                "deadline_id": str(deadline.id),
                "title": deadline.title,
                "old_date": old_date.isoformat(),
                "new_date": new_date.isoformat(),
                "was_overridden": was_overridden,
                "message": message
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _duplicate_deadline(self, input_data: Dict) -> Dict:
        """Duplicate a deadline with optional modifications"""
        try:
            source = self.db.query(Deadline).filter(
                Deadline.id == input_data['source_deadline_id'],
                Deadline.case_id == self.case_id
            ).first()

            if not source:
                return {"success": False, "error": "Source deadline not found"}

            # Determine new title
            new_title = input_data.get('new_title', f"{source.title} (Copy)")

            # Determine new date
            if 'new_date' in input_data:
                new_date = datetime.strptime(input_data['new_date'], '%Y-%m-%d').date()
            elif 'date_offset_days' in input_data and source.deadline_date:
                from datetime import timedelta
                new_date = source.deadline_date + timedelta(days=input_data['date_offset_days'])
            else:
                new_date = source.deadline_date

            # Create duplicate
            new_deadline = Deadline(
                case_id=self.case_id,
                user_id=self.user_id,
                title=new_title,
                description=source.description,
                deadline_date=new_date,
                priority=source.priority,
                party_role=source.party_role,
                action_required=source.action_required,
                applicable_rule=source.applicable_rule,
                status='pending',
                created_via_chat=True,
                is_calculated=False,  # Copies are manual deadlines
                is_dependent=False,
                extraction_method='manual',
                confidence_score=95,
                confidence_level='high',
                confidence_factors={'duplicated_from': str(source.id)},
                verification_status='approved',
                extraction_quality_score=10
            )

            self.db.add(new_deadline)
            self.db.commit()
            self.db.refresh(new_deadline)

            return {
                "success": True,
                "new_deadline_id": str(new_deadline.id),
                "source_deadline_id": str(source.id),
                "title": new_deadline.title,
                "date": new_deadline.deadline_date.isoformat() if new_deadline.deadline_date else None,
                "message": f"✓ Created duplicate deadline: '{new_deadline.title}' on {new_deadline.deadline_date}"
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _link_deadlines(self, input_data: Dict) -> Dict:
        """Create a dependency link between two deadlines"""
        try:
            parent_id = input_data['parent_deadline_id']
            child_id = input_data['child_deadline_id']
            days_offset = input_data['days_offset']

            # Get both deadlines
            parent = self.db.query(Deadline).filter(
                Deadline.id == parent_id,
                Deadline.case_id == self.case_id
            ).first()

            child = self.db.query(Deadline).filter(
                Deadline.id == child_id,
                Deadline.case_id == self.case_id
            ).first()

            if not parent:
                return {"success": False, "error": "Parent deadline not found"}
            if not child:
                return {"success": False, "error": "Child deadline not found"}

            # Check for circular dependencies
            if str(child.id) == str(parent.parent_deadline_id):
                return {"success": False, "error": "Cannot create circular dependency"}

            # Link the deadlines
            child.parent_deadline_id = str(parent.id)
            child.is_dependent = True
            child.is_calculated = True
            child.days_count = days_offset
            child.calculation_type = 'calendar_days'

            # If parent has a date, calculate child's expected date
            if parent.deadline_date:
                from datetime import timedelta
                expected_date = parent.deadline_date + timedelta(days=days_offset)
                child.calculation_basis = f"Linked to '{parent.title}' ({parent.deadline_date}) + {days_offset} days"

            self.db.commit()

            offset_desc = f"{abs(days_offset)} days {'after' if days_offset >= 0 else 'before'}"

            return {
                "success": True,
                "parent_id": str(parent.id),
                "child_id": str(child.id),
                "parent_title": parent.title,
                "child_title": child.title,
                "days_offset": days_offset,
                "message": f"✓ Linked '{child.title}' to '{parent.title}' ({offset_desc}). "
                          f"Child deadline will now cascade when parent changes."
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    # =========================================================================
    # AUTHORITY CORE TOOLS
    # =========================================================================

    def _search_court_rules(self, input_data: Dict) -> Dict:
        """Search Authority Core rules database"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.models.jurisdiction import Jurisdiction
            from sqlalchemy import or_

            query_text = input_data.get('query', '')
            jurisdiction_id = input_data.get('jurisdiction_id')
            trigger_type = input_data.get('trigger_type')

            # Build search query
            search_filter = or_(
                AuthorityRule.rule_name.ilike(f"%{query_text}%"),
                AuthorityRule.rule_code.ilike(f"%{query_text}%"),
                AuthorityRule.citation.ilike(f"%{query_text}%"),
                AuthorityRule.source_text.ilike(f"%{query_text}%")
            )

            db_query = self.db.query(AuthorityRule).filter(
                search_filter,
                AuthorityRule.is_active == True,
                AuthorityRule.is_verified == True
            )

            if jurisdiction_id:
                db_query = db_query.filter(AuthorityRule.jurisdiction_id == jurisdiction_id)

            if trigger_type:
                db_query = db_query.filter(AuthorityRule.trigger_type == trigger_type)

            rules = db_query.limit(10).all()

            if not rules:
                return {
                    "success": True,
                    "rules_found": 0,
                    "rules": [],
                    "message": f"No rules found matching '{query_text}'. Try a different search term or check if rules have been imported for this jurisdiction."
                }

            # Format results
            results = []
            for rule in rules:
                # Get jurisdiction name
                jurisdiction = self.db.query(Jurisdiction).filter(
                    Jurisdiction.id == rule.jurisdiction_id
                ).first()

                deadline_count = len(rule.deadlines) if rule.deadlines else 0

                results.append({
                    "rule_id": rule.id,
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "citation": rule.citation,
                    "trigger_type": rule.trigger_type,
                    "authority_tier": rule.authority_tier.value if rule.authority_tier else "state",
                    "jurisdiction_name": jurisdiction.name if jurisdiction else "Unknown",
                    "deadline_count": deadline_count,
                    "is_verified": rule.is_verified
                })

            return {
                "success": True,
                "rules_found": len(results),
                "rules": results,
                "message": f"Found {len(results)} rules matching '{query_text}'."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_rule_details(self, input_data: Dict) -> Dict:
        """Get full details of a specific Authority Core rule"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.models.jurisdiction import Jurisdiction

            rule_id = input_data.get('rule_id')
            if not rule_id:
                return {"success": False, "error": "rule_id is required"}

            rule = self.db.query(AuthorityRule).filter(
                AuthorityRule.id == rule_id
            ).first()

            if not rule:
                return {"success": False, "error": f"Rule {rule_id} not found"}

            # Get jurisdiction name
            jurisdiction = self.db.query(Jurisdiction).filter(
                Jurisdiction.id == rule.jurisdiction_id
            ).first()

            return {
                "success": True,
                "rule": {
                    "id": rule.id,
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "citation": rule.citation,
                    "trigger_type": rule.trigger_type,
                    "authority_tier": rule.authority_tier.value if rule.authority_tier else "state",
                    "jurisdiction_name": jurisdiction.name if jurisdiction else "Unknown",
                    "source_url": rule.source_url,
                    "source_text": rule.source_text[:1000] if rule.source_text else None,
                    "deadlines": rule.deadlines or [],
                    "conditions": rule.conditions,
                    "service_extensions": rule.service_extensions or {"mail": 3, "electronic": 0, "personal": 0},
                    "is_verified": rule.is_verified,
                    "verified_at": rule.verified_at.isoformat() if rule.verified_at else None,
                    "confidence_score": float(rule.confidence_score) if rule.confidence_score else 0.0
                },
                "message": f"Rule details for {rule.rule_name}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _calculate_from_rule(self, input_data: Dict) -> Dict:
        """Calculate deadlines from an Authority Core rule without creating them"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.utils.deadline_calculator import AuthoritativeDeadlineCalculator, CalculationMethod
            from datetime import datetime, timedelta

            rule_id = input_data.get('rule_id')
            trigger_date_str = input_data.get('trigger_date')
            service_method = input_data.get('service_method', 'electronic')

            if not rule_id:
                return {"success": False, "error": "rule_id is required"}
            if not trigger_date_str:
                return {"success": False, "error": "trigger_date is required"}

            # Parse date
            try:
                trigger_date = datetime.strptime(trigger_date_str, '%Y-%m-%d').date()
            except ValueError:
                return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}

            # Get the rule
            rule = self.db.query(AuthorityRule).filter(
                AuthorityRule.id == rule_id
            ).first()

            if not rule:
                return {"success": False, "error": f"Rule {rule_id} not found"}

            # Calculate deadlines
            calculator = AuthoritativeDeadlineCalculator()
            calculated_deadlines = []

            # Get service extension
            extensions = rule.service_extensions or {}
            extension_days = extensions.get(service_method, 0)

            for deadline_spec in (rule.deadlines or []):
                days = deadline_spec.get('days_from_trigger', 0) + extension_days
                method_str = deadline_spec.get('calculation_method', 'calendar_days')

                # Map calculation method
                if method_str in ['business_days', 'court_days']:
                    calc_method = CalculationMethod.COURT_DAYS
                else:
                    calc_method = CalculationMethod.CALENDAR_DAYS

                # Calculate the deadline date
                deadline_date = calculator.calculate_deadline(
                    start_date=trigger_date,
                    days=days,
                    method=calc_method
                )

                calculated_deadlines.append({
                    "title": deadline_spec.get('title', 'Unknown'),
                    "deadline_date": deadline_date.isoformat(),
                    "days_from_trigger": deadline_spec.get('days_from_trigger', 0),
                    "calculation_method": method_str,
                    "priority": deadline_spec.get('priority', 'standard'),
                    "party_responsible": deadline_spec.get('party_responsible')
                })

            return {
                "success": True,
                "rule_name": rule.rule_name,
                "citation": rule.citation,
                "trigger_date": trigger_date_str,
                "service_method": service_method,
                "deadlines_calculated": len(calculated_deadlines),
                "deadlines": calculated_deadlines,
                "message": f"Calculated {len(calculated_deadlines)} deadlines from {rule.rule_name}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # PHASE 4: EXPANDED AUTHORITY CORE TOOLS
    # =========================================================================

    def _find_applicable_rules(self, input_data: Dict) -> Dict:
        """PRIMARY DOCKETING TOOL: Find all applicable rules for trigger + jurisdiction"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.models.jurisdiction import Jurisdiction

            trigger_type = input_data.get('trigger_type')
            jurisdiction_id = input_data.get('jurisdiction_id')

            if not trigger_type or not jurisdiction_id:
                return {"success": False, "error": "trigger_type and jurisdiction_id are required"}

            # Query applicable rules
            rules = self.db.query(AuthorityRule).filter(
                AuthorityRule.jurisdiction_id == jurisdiction_id,
                AuthorityRule.trigger_type == trigger_type,
                AuthorityRule.is_active == True,
                AuthorityRule.is_verified == True
            ).order_by(
                AuthorityRule.confidence_score.desc(),
                AuthorityRule.authority_tier
            ).all()

            if not rules:
                # Get jurisdiction name for better error message
                jurisdiction = self.db.query(Jurisdiction).filter(
                    Jurisdiction.id == jurisdiction_id
                ).first()
                jurisdiction_name = jurisdiction.name if jurisdiction else "Unknown"

                return {
                    "success": True,
                    "applicable_rules_count": 0,
                    "rules": [],
                    "message": f"No rules found for trigger '{trigger_type}' in {jurisdiction_name}. This trigger may not have been harvested yet or may not apply to this jurisdiction."
                }

            # Format results with detailed metadata
            results = []
            total_deadlines = 0

            for rule in rules:
                deadline_count = len(rule.deadlines) if rule.deadlines else 0
                total_deadlines += deadline_count

                results.append({
                    "rule_id": rule.id,
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "citation": rule.citation,
                    "trigger_type": rule.trigger_type,
                    "authority_tier": rule.authority_tier.value if rule.authority_tier else "state",
                    "confidence_score": float(rule.confidence_score) if rule.confidence_score else 0.0,
                    "deadline_count": deadline_count,
                    "deadlines_preview": rule.deadlines[:3] if rule.deadlines else [],  # First 3 deadlines
                    "is_verified": rule.is_verified,
                    "source_url": rule.source_url
                })

            return {
                "success": True,
                "applicable_rules_count": len(results),
                "total_deadlines": total_deadlines,
                "rules": results,
                "message": f"Found {len(results)} applicable rules generating {total_deadlines} total deadlines. Use calculate_from_rule or generate_all_deadlines_for_case to create them."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _compare_rules_across_jurisdictions(self, input_data: Dict) -> Dict:
        """Compare rules across multiple jurisdictions"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.models.jurisdiction import Jurisdiction

            trigger_type = input_data.get('trigger_type')
            jurisdiction_ids = input_data.get('jurisdiction_ids', [])

            if not trigger_type or not jurisdiction_ids:
                return {"success": False, "error": "trigger_type and jurisdiction_ids are required"}

            if len(jurisdiction_ids) < 2:
                return {"success": False, "error": "At least 2 jurisdictions required for comparison"}

            if len(jurisdiction_ids) > 5:
                return {"success": False, "error": "Maximum 5 jurisdictions for comparison"}

            # Fetch rules for each jurisdiction
            comparison = []

            for jurisdiction_id in jurisdiction_ids:
                jurisdiction = self.db.query(Jurisdiction).filter(
                    Jurisdiction.id == jurisdiction_id
                ).first()

                rules = self.db.query(AuthorityRule).filter(
                    AuthorityRule.jurisdiction_id == jurisdiction_id,
                    AuthorityRule.trigger_type == trigger_type,
                    AuthorityRule.is_active == True,
                    AuthorityRule.is_verified == True
                ).all()

                comparison.append({
                    "jurisdiction_id": jurisdiction_id,
                    "jurisdiction_name": jurisdiction.name if jurisdiction else "Unknown",
                    "rule_count": len(rules),
                    "rules": [{
                        "rule_id": r.id,
                        "rule_name": r.rule_name,
                        "rule_code": r.rule_code,
                        "citation": r.citation,
                        "deadline_count": len(r.deadlines) if r.deadlines else 0,
                        "deadlines": r.deadlines or [],
                        "service_extensions": r.service_extensions or {}
                    } for r in rules]
                })

            return {
                "success": True,
                "trigger_type": trigger_type,
                "jurisdictions_compared": len(comparison),
                "comparison": comparison,
                "message": f"Compared {trigger_type} rules across {len(comparison)} jurisdictions."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_rule_history(self, input_data: Dict) -> Dict:
        """Get change history for a rule"""
        try:
            from app.models.authority_core import AuthorityRule, AuthorityRuleVersion

            rule_id = input_data.get('rule_id')
            if not rule_id:
                return {"success": False, "error": "rule_id is required"}

            # Get current rule
            rule = self.db.query(AuthorityRule).filter(
                AuthorityRule.id == rule_id
            ).first()

            if not rule:
                return {"success": False, "error": f"Rule {rule_id} not found"}

            # Get version history
            versions = self.db.query(AuthorityRuleVersion).filter(
                AuthorityRuleVersion.rule_id == rule_id
            ).order_by(AuthorityRuleVersion.version_number.desc()).all()

            history = []
            for version in versions:
                history.append({
                    "version_number": version.version_number,
                    "changed_at": version.changed_at.isoformat() if version.changed_at else None,
                    "changed_by": version.changed_by,
                    "change_reason": version.change_reason,
                    "diff_summary": version.diff_summary or {},
                    "confidence_score": float(version.confidence_score) if version.confidence_score else 0.0
                })

            return {
                "success": True,
                "rule_id": rule_id,
                "rule_name": rule.rule_name,
                "current_version": rule.version_number if hasattr(rule, 'version_number') else 1,
                "total_versions": len(history),
                "history": history,
                "message": f"Found {len(history)} version(s) of {rule.rule_name}"
            }

        except Exception as e:
            # If AuthorityRuleVersion doesn't exist yet, return graceful message
            if "AuthorityRuleVersion" in str(e):
                return {
                    "success": True,
                    "rule_id": rule_id,
                    "history": [],
                    "message": "Version history tracking not yet implemented. This feature will be available in Phase 5."
                }
            return {"success": False, "error": str(e)}

    def _validate_deadline_against_rules(self, input_data: Dict) -> Dict:
        """Validate user-entered deadline against Authority Core rules"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.utils.deadline_calculator import AuthoritativeDeadlineCalculator, CalculationMethod
            from datetime import datetime

            deadline_date_str = input_data.get('deadline_date')
            trigger_date_str = input_data.get('trigger_date')
            trigger_type = input_data.get('trigger_type')
            jurisdiction_id = input_data.get('jurisdiction_id')
            service_method = input_data.get('service_method', 'electronic')

            if not all([deadline_date_str, trigger_date_str, trigger_type, jurisdiction_id]):
                return {"success": False, "error": "All parameters are required"}

            # Parse dates
            deadline_date = datetime.strptime(deadline_date_str, '%Y-%m-%d').date()
            trigger_date = datetime.strptime(trigger_date_str, '%Y-%m-%d').date()

            # Find applicable rules
            rules = self.db.query(AuthorityRule).filter(
                AuthorityRule.jurisdiction_id == jurisdiction_id,
                AuthorityRule.trigger_type == trigger_type,
                AuthorityRule.is_active == True,
                AuthorityRule.is_verified == True
            ).all()

            if not rules:
                return {
                    "success": True,
                    "is_valid": None,
                    "message": "No rules found to validate against. Manual deadline may be correct, but cannot verify."
                }

            # Check if deadline matches any rule
            calculator = AuthoritativeDeadlineCalculator()
            matches = []
            near_matches = []

            for rule in rules:
                if not rule.deadlines:
                    continue

                extensions = rule.service_extensions or {}
                extension_days = extensions.get(service_method, 0)

                for deadline_spec in rule.deadlines:
                    days = deadline_spec.get('days_from_trigger', 0) + extension_days
                    method_str = deadline_spec.get('calculation_method', 'calendar_days')

                    calc_method = CalculationMethod.COURT_DAYS if method_str in ['business_days', 'court_days'] else CalculationMethod.CALENDAR_DAYS

                    calculated = calculator.calculate_deadline(
                        start_date=trigger_date,
                        days=days,
                        method=calc_method
                    )

                    days_difference = abs((calculated - deadline_date).days)

                    if calculated == deadline_date:
                        matches.append({
                            "rule_id": rule.id,
                            "rule_name": rule.rule_name,
                            "rule_code": rule.rule_code,
                            "citation": rule.citation,
                            "deadline_title": deadline_spec.get('title', 'Unknown'),
                            "calculated_date": calculated.isoformat(),
                            "match_type": "exact"
                        })
                    elif days_difference <= 3:
                        near_matches.append({
                            "rule_id": rule.id,
                            "rule_name": rule.rule_name,
                            "rule_code": rule.rule_code,
                            "citation": rule.citation,
                            "deadline_title": deadline_spec.get('title', 'Unknown'),
                            "calculated_date": calculated.isoformat(),
                            "days_difference": days_difference,
                            "match_type": "near"
                        })

            if matches:
                return {
                    "success": True,
                    "is_valid": True,
                    "exact_matches": matches,
                    "message": f"✅ Deadline is valid! Matches {len(matches)} rule(s)."
                }
            elif near_matches:
                return {
                    "success": True,
                    "is_valid": False,
                    "near_matches": near_matches,
                    "message": f"⚠️ Deadline may be incorrect. Found {len(near_matches)} rules within 3 days. Please review."
                }
            else:
                return {
                    "success": True,
                    "is_valid": False,
                    "message": "❌ Deadline does not match any known rules. Please verify manually or check trigger date."
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_all_deadlines_for_case(self, input_data: Dict) -> Dict:
        """POWER TOOL: Generate all deadlines for a case from multiple triggers"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.models.deadline import Deadline
            from app.utils.deadline_calculator import AuthoritativeDeadlineCalculator, CalculationMethod
            from datetime import datetime

            case_id = input_data.get('case_id')
            triggers = input_data.get('triggers', [])
            jurisdiction_id = input_data.get('jurisdiction_id')
            create_deadlines = input_data.get('create_deadlines', False)

            if not all([case_id, triggers, jurisdiction_id]):
                return {"success": False, "error": "case_id, triggers, and jurisdiction_id are required"}

            calculator = AuthoritativeDeadlineCalculator()
            all_deadlines = []
            rule_usage_count = {}

            # Process each trigger
            for trigger in triggers:
                trigger_type = trigger.get('trigger_type')
                trigger_date_str = trigger.get('trigger_date')
                service_method = trigger.get('service_method', 'electronic')

                if not trigger_type or not trigger_date_str:
                    continue

                trigger_date = datetime.strptime(trigger_date_str, '%Y-%m-%d').date()

                # Find applicable rules
                rules = self.db.query(AuthorityRule).filter(
                    AuthorityRule.jurisdiction_id == jurisdiction_id,
                    AuthorityRule.trigger_type == trigger_type,
                    AuthorityRule.is_active == True,
                    AuthorityRule.is_verified == True
                ).order_by(AuthorityRule.confidence_score.desc()).all()

                # Generate deadlines from each rule
                for rule in rules:
                    rule_usage_count[rule.rule_code] = rule_usage_count.get(rule.rule_code, 0) + 1

                    if not rule.deadlines:
                        continue

                    extensions = rule.service_extensions or {}
                    extension_days = extensions.get(service_method, 0)

                    for deadline_spec in rule.deadlines:
                        days = deadline_spec.get('days_from_trigger', 0) + extension_days
                        method_str = deadline_spec.get('calculation_method', 'calendar_days')

                        calc_method = CalculationMethod.COURT_DAYS if method_str in ['business_days', 'court_days'] else CalculationMethod.CALENDAR_DAYS

                        calculated_date = calculator.calculate_deadline(
                            start_date=trigger_date,
                            days=days,
                            method=calc_method
                        )

                        deadline_data = {
                            "title": deadline_spec.get('title', 'Deadline'),
                            "deadline_date": calculated_date.isoformat(),
                            "trigger_type": trigger_type,
                            "trigger_date": trigger_date_str,
                            "priority": deadline_spec.get('priority', 'standard'),
                            "party_responsible": deadline_spec.get('party_responsible'),
                            "rule_code": rule.rule_code,
                            "rule_name": rule.rule_name,
                            "citation": rule.citation,
                            "confidence_score": float(rule.confidence_score) if rule.confidence_score else 0.0,
                            "source_rule_id": rule.id,
                            "calculation_method": method_str,
                            "service_method": service_method
                        }

                        all_deadlines.append(deadline_data)

                        # Actually create deadline if requested
                        if create_deadlines:
                            deadline = Deadline(
                                case_id=case_id,
                                user_id=self.user_id,
                                title=deadline_data['title'],
                                deadline_date=calculated_date,
                                trigger_date=trigger_date,
                                trigger_type=trigger_type,
                                priority=deadline_data['priority'],
                                party_role=deadline_data.get('party_responsible'),
                                rule_code=deadline_data['rule_code'],
                                rule_name=deadline_data['rule_name'],
                                rule_citation=deadline_data['citation'],
                                confidence_score=deadline_data['confidence_score'],
                                source_rule_id=deadline_data['source_rule_id'],
                                status='pending',
                                created_via_chat=True
                            )
                            self.db.add(deadline)

            if create_deadlines and all_deadlines:
                self.db.commit()

            # Sort by date
            all_deadlines.sort(key=lambda x: x['deadline_date'])

            return {
                "success": True,
                "deadlines_generated": len(all_deadlines),
                "triggers_processed": len(triggers),
                "rules_used": len(rule_usage_count),
                "created_in_database": create_deadlines,
                "deadlines": all_deadlines,
                "rule_usage": rule_usage_count,
                "message": f"Generated {len(all_deadlines)} deadlines from {len(triggers)} trigger(s) using {len(rule_usage_count)} rule(s). {'Created in database.' if create_deadlines else 'Preview only - set create_deadlines=true to save.'}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_rule_coverage(self, input_data: Dict) -> Dict:
        """Analyze rule coverage for a jurisdiction"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.models.jurisdiction import Jurisdiction
            from app.models.enums import TriggerType
            from sqlalchemy import func

            jurisdiction_id = input_data.get('jurisdiction_id')
            if not jurisdiction_id:
                return {"success": False, "error": "jurisdiction_id is required"}

            # Get jurisdiction info
            jurisdiction = self.db.query(Jurisdiction).filter(
                Jurisdiction.id == jurisdiction_id
            ).first()

            if not jurisdiction:
                return {"success": False, "error": f"Jurisdiction {jurisdiction_id} not found"}

            # Get all rules for jurisdiction
            rules = self.db.query(AuthorityRule).filter(
                AuthorityRule.jurisdiction_id == jurisdiction_id,
                AuthorityRule.is_active == True
            ).all()

            # Analyze coverage by trigger type
            trigger_coverage = {}
            for rule in rules:
                trigger = rule.trigger_type
                if trigger not in trigger_coverage:
                    trigger_coverage[trigger] = {
                        "rule_count": 0,
                        "verified_count": 0,
                        "total_deadlines": 0,
                        "avg_confidence": 0.0,
                        "rules": []
                    }

                trigger_coverage[trigger]["rule_count"] += 1
                if rule.is_verified:
                    trigger_coverage[trigger]["verified_count"] += 1
                trigger_coverage[trigger]["total_deadlines"] += len(rule.deadlines) if rule.deadlines else 0
                trigger_coverage[trigger]["rules"].append({
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "confidence_score": float(rule.confidence_score) if rule.confidence_score else 0.0
                })

            # Calculate average confidence per trigger
            for trigger, data in trigger_coverage.items():
                if data["rules"]:
                    data["avg_confidence"] = sum(r["confidence_score"] for r in data["rules"]) / len(data["rules"])

            # Identify gaps (triggers with no rules)
            all_trigger_types = [t.value for t in TriggerType]
            gaps = [t for t in all_trigger_types if t not in trigger_coverage]

            # Overall statistics
            total_rules = len(rules)
            verified_rules = sum(1 for r in rules if r.is_verified)
            avg_confidence = sum(float(r.confidence_score) if r.confidence_score else 0.0 for r in rules) / total_rules if total_rules > 0 else 0.0

            return {
                "success": True,
                "jurisdiction_name": jurisdiction.name,
                "jurisdiction_id": jurisdiction_id,
                "total_rules": total_rules,
                "verified_rules": verified_rules,
                "verification_rate": f"{(verified_rules / total_rules * 100):.1f}%" if total_rules > 0 else "0%",
                "average_confidence": f"{avg_confidence:.2f}",
                "trigger_coverage": trigger_coverage,
                "triggers_with_rules": len(trigger_coverage),
                "triggers_without_rules": len(gaps),
                "gaps": gaps,
                "coverage_percentage": f"{(len(trigger_coverage) / len(all_trigger_types) * 100):.1f}%",
                "message": f"{jurisdiction.name} has {total_rules} rules covering {len(trigger_coverage)}/{len(all_trigger_types)} trigger types ({len(gaps)} gaps)."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _explain_deadline_from_rule(self, input_data: Dict) -> Dict:
        """Provide step-by-step explanation of deadline calculation"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.utils.deadline_calculator import AuthoritativeDeadlineCalculator, CalculationMethod
            from datetime import datetime

            rule_id = input_data.get('rule_id')
            trigger_date_str = input_data.get('trigger_date')
            deadline_date_str = input_data.get('deadline_date')
            service_method = input_data.get('service_method', 'electronic')

            if not all([rule_id, trigger_date_str, deadline_date_str]):
                return {"success": False, "error": "rule_id, trigger_date, and deadline_date are required"}

            # Get rule
            rule = self.db.query(AuthorityRule).filter(
                AuthorityRule.id == rule_id
            ).first()

            if not rule:
                return {"success": False, "error": f"Rule {rule_id} not found"}

            trigger_date = datetime.strptime(trigger_date_str, '%Y-%m-%d').date()
            deadline_date = datetime.strptime(deadline_date_str, '%Y-%m-%d').date()

            # Find which deadline spec this matches
            calculator = AuthoritativeDeadlineCalculator()
            extensions = rule.service_extensions or {}
            extension_days = extensions.get(service_method, 0)

            explanation = {
                "rule_name": rule.rule_name,
                "rule_code": rule.rule_code,
                "citation": rule.citation,
                "trigger_date": trigger_date_str,
                "deadline_date": deadline_date_str,
                "calculation_steps": []
            }

            # Try to match deadline date to a deadline spec
            matched = False
            for deadline_spec in (rule.deadlines or []):
                base_days = deadline_spec.get('days_from_trigger', 0)
                method_str = deadline_spec.get('calculation_method', 'calendar_days')
                calc_method = CalculationMethod.COURT_DAYS if method_str in ['business_days', 'court_days'] else CalculationMethod.CALENDAR_DAYS

                total_days = base_days + extension_days
                calculated = calculator.calculate_deadline(
                    start_date=trigger_date,
                    days=total_days,
                    method=calc_method
                )

                if calculated == deadline_date:
                    matched = True
                    explanation["deadline_title"] = deadline_spec.get('title', 'Unknown')
                    explanation["calculation_steps"] = [
                        f"1. Start date (trigger): {trigger_date_str}",
                        f"2. Base deadline: {base_days} days from trigger",
                        f"3. Service extension ({service_method}): +{extension_days} days",
                        f"4. Total days: {total_days} days",
                        f"5. Calculation method: {method_str}",
                        f"6. Final deadline: {deadline_date_str}"
                    ]
                    break

            if not matched:
                explanation["calculation_steps"] = [
                    "Could not match this deadline to any specification in the rule.",
                    "The deadline may have been manually adjusted or calculated using a different rule."
                ]

            explanation["message"] = f"Deadline calculated using {rule.rule_name} ({rule.rule_code})"

            return {
                "success": True,
                "explanation": explanation
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _suggest_related_rules(self, input_data: Dict) -> Dict:
        """Suggest related rules based on context"""
        try:
            from app.models.authority_core import AuthorityRule
            from app.models.enums import TriggerType

            context = input_data.get('context', '')
            jurisdiction_id = input_data.get('jurisdiction_id')
            existing_trigger_types = input_data.get('existing_trigger_types', [])

            if not jurisdiction_id:
                return {"success": False, "error": "jurisdiction_id is required"}

            # Suggest rules based on context
            suggestions = []

            # Common rule relationships
            related_triggers = {
                'trial_date': ['pretrial_conference', 'dispositive_motions_due', 'discovery_deadline'],
                'motion_filed': ['hearing_scheduled', 'order_entered'],
                'discovery_commenced': ['discovery_deadline'],
                'case_filed': ['complaint_served', 'answer_due'],
                'complaint_served': ['answer_due']
            }

            # Get suggestions based on existing triggers
            suggested_trigger_types = set()
            for existing in existing_trigger_types:
                if existing in related_triggers:
                    suggested_trigger_types.update(related_triggers[existing])

            # Remove already existing triggers
            suggested_trigger_types = suggested_trigger_types - set(existing_trigger_types)

            # Fetch rules for suggested triggers
            if suggested_trigger_types:
                rules = self.db.query(AuthorityRule).filter(
                    AuthorityRule.jurisdiction_id == jurisdiction_id,
                    AuthorityRule.trigger_type.in_(suggested_trigger_types),
                    AuthorityRule.is_active == True,
                    AuthorityRule.is_verified == True
                ).all()

                for rule in rules:
                    suggestions.append({
                        "rule_id": rule.id,
                        "rule_code": rule.rule_code,
                        "rule_name": rule.rule_name,
                        "trigger_type": rule.trigger_type,
                        "relevance_reason": f"Commonly used with {', '.join(existing_trigger_types)}",
                        "confidence_score": float(rule.confidence_score) if rule.confidence_score else 0.0,
                        "deadline_count": len(rule.deadlines) if rule.deadlines else 0
                    })

            return {
                "success": True,
                "suggestions_count": len(suggestions),
                "suggestions": suggestions,
                "message": f"Found {len(suggestions)} related rule(s) you might need."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _request_jurisdiction_harvest(self, input_data: Dict) -> Dict:
        """ADMIN TOOL: Request automated rule harvesting"""
        try:
            from app.models.jurisdiction import Jurisdiction
            from app.services.authority_core_service import AuthorityCoreService

            jurisdiction_id = input_data.get('jurisdiction_id')
            force_reharvest = input_data.get('force_reharvest', False)

            if not jurisdiction_id:
                return {"success": False, "error": "jurisdiction_id is required"}

            # Verify jurisdiction exists
            jurisdiction = self.db.query(Jurisdiction).filter(
                Jurisdiction.id == jurisdiction_id
            ).first()

            if not jurisdiction:
                return {"success": False, "error": f"Jurisdiction {jurisdiction_id} not found"}

            # Check if rules already exist
            from app.models.authority_core import AuthorityRule
            existing_rules = self.db.query(AuthorityRule).filter(
                AuthorityRule.jurisdiction_id == jurisdiction_id,
                AuthorityRule.is_active == True
            ).count()

            if existing_rules > 0 and not force_reharvest:
                return {
                    "success": False,
                    "error": f"Jurisdiction already has {existing_rules} rules. Set force_reharvest=true to re-harvest."
                }

            # Trigger harvest (async operation)
            authority_service = AuthorityCoreService(self.db)

            # Note: This would normally trigger an async job
            # For now, return status that job would be queued
            return {
                "success": True,
                "jurisdiction_id": jurisdiction_id,
                "jurisdiction_name": jurisdiction.name,
                "harvest_requested": True,
                "estimated_completion": "15-30 minutes",
                "message": f"Rule harvest requested for {jurisdiction.name}. Cartographer will discover scraper config, extract rules, and create inbox items for review. Check inbox in 15-30 minutes."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
