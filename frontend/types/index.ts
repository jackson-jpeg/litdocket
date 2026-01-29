// Party information for a case
export interface Party {
  name: string;
  role: string;
  type?: 'individual' | 'organization';
  attorney?: string;
}

// Case metadata from document analysis
export interface CaseMetadata {
  case_number?: string;
  court?: string;
  judge?: string;
  case_type?: string;
  jurisdiction?: string;
  district?: string;
  circuit?: string;
  summary?: string;
  parties?: Party[];
  filing_date?: string;
  [key: string]: unknown; // Allow additional properties
}

export interface Case {
  id: string;
  case_number: string;
  title: string;
  court: string;
  judge?: string;
  status: string;
  case_type?: string;
  jurisdiction?: string;
  district?: string;
  circuit?: string;
  filing_date?: string;
  parties?: Party[];
  metadata?: CaseMetadata;
  created_at: string;
  updated_at: string;
}

// Document extracted metadata
export interface DocumentMetadata {
  document_type?: string;
  filing_date?: string;
  case_number?: string;
  court?: string;
  judge?: string;
  parties?: Party[];
  summary?: string;
  key_dates?: Array<{ date: string; description: string }>;
  deadlines_mentioned?: Array<{ title: string; date?: string; rule?: string }>;
  [key: string]: unknown;
}

export interface Document {
  id: string;
  case_id?: string;
  file_name: string;
  document_type?: string;
  filing_date?: string;
  ai_summary?: string;
  extracted_metadata?: DocumentMetadata;
  storage_url?: string;
  created_at: string;
  needs_ocr?: boolean;
  analysis_status?: string;
}

// Priority levels for deadlines - ordered by severity
// Known values: 'informational' | 'standard' | 'important' | 'critical' | 'fatal'
// Legacy values that may appear: 'high' | 'low' | 'medium'
export type DeadlinePriority = 'informational' | 'standard' | 'important' | 'critical' | 'fatal' | 'high' | 'low' | 'medium' | string;

// Status of a deadline
// Known values: 'pending' | 'completed' | 'cancelled'
// Legacy values that may appear: 'in_progress' | 'overdue'
export type DeadlineStatus = 'pending' | 'completed' | 'cancelled' | 'in_progress' | 'overdue' | string;

// Verification status for Case OS
export type VerificationStatus = 'pending' | 'verified' | 'rejected';

// Confidence level for AI extractions
export type ConfidenceLevel = 'low' | 'medium' | 'high';

/**
 * Comprehensive Deadline interface - Single Source of Truth
 *
 * This interface covers ALL fields returned by various API endpoints:
 * - GET /api/v1/deadlines/case/{case_id}
 * - GET /api/v1/deadlines/user/all (includes case_number, case_title)
 * - GET /api/v1/deadlines/{deadline_id}
 *
 * Most fields are optional since different endpoints return different subsets.
 */
export interface Deadline {
  // Core identifiers
  id: string;
  case_id: string;
  user_id?: string;
  document_id?: string;
  parent_deadline_id?: string;

  // Case info (populated by /user/all endpoint via JOIN)
  case_number?: string;
  case_title?: string;

  // Core deadline info
  title: string;
  description?: string;
  deadline_date: string | null;  // ISO format YYYY-MM-DD, nullable for TBD deadlines
  deadline_time?: string;
  deadline_type?: string;

  // Priority and status
  priority: DeadlinePriority;
  status: DeadlineStatus;

  // Responsibility
  party_role?: string;
  action_required?: string;

  // Legal citation and calculation
  applicable_rule?: string;
  rule_citation?: string;
  calculation_basis?: string;

  // Trigger/dependency info (for calculated deadlines)
  trigger_event?: string;
  trigger_date?: string;
  is_calculated?: boolean;
  is_dependent?: boolean;
  auto_recalculate?: boolean;

  // Manual override tracking
  is_manually_overridden?: boolean;
  override_timestamp?: string;
  override_user_id?: string;
  override_reason?: string;
  original_deadline_date?: string;

  // Estimation flag
  is_estimated?: boolean;

  // Service method (for deadline calculation)
  service_method?: 'email' | 'electronic' | 'mail' | 'personal' | string;
  source_document?: string;

  // Case OS - Confidence and verification
  confidence_score?: number;
  confidence_level?: ConfidenceLevel;
  confidence_factors?: Record<string, unknown>;
  verification_status?: VerificationStatus;
  verified_by?: string;
  verified_at?: string;
  verification_notes?: string;

  // Case OS - Source extraction info
  source_page?: number;
  source_text?: string;
  source_coordinates?: Record<string, unknown>;
  extraction_method?: string;
  extraction_quality_score?: number;

  // Audit timestamps
  created_at?: string;
  updated_at?: string;
  modified_by?: string;
  modification_reason?: string;
}

/**
 * CalendarDeadline - Extended Deadline type for calendar view
 * Includes case info and computed fields
 */
export interface CalendarDeadline extends Deadline {
  // Required for calendar display
  case_number: string;
  case_title: string;
  created_at: string;
  updated_at: string;
}

/**
 * TriggerChildDeadline - Deadline nested under a trigger event
 * Used by GET /api/v1/triggers/case/{case_id}/triggers
 */
export interface TriggerChildDeadline {
  id: string;
  title: string;
  description?: string;
  deadline_date: string | null;
  priority: DeadlinePriority | string;
  status: DeadlineStatus | string;
  is_overdue: boolean;
  applicable_rule?: string;
  calculation_basis?: string;
  party_role?: string;
  action_required?: string;
  is_manually_overridden: boolean;
  auto_recalculate: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  context_rules?: string[];
  context_documents?: string[];
  created_at: string;
}

// Document analysis result from AI
export interface DocumentAnalysis {
  case_number?: string;
  document_type?: string;
  court?: string;
  judge?: string;
  jurisdiction?: string;
  district?: string;
  case_type?: string;
  parties?: Party[];
  summary?: string;
  filing_date?: string;
  service_method?: string;
  service_date?: string;
  key_dates?: Array<{ date: string; description: string }>;
  deadlines_mentioned?: Array<{ title: string; date?: string; rule?: string }>;
}

export interface UploadResponse {
  success: boolean;
  document_id: string;
  case_id: string;
  case_created: boolean;
  analysis: DocumentAnalysis;
  deadlines_extracted: number;
  redirect_url: string;
  message: string;
}

// Dashboard types
export interface DashboardDeadline {
  id: string;
  case_id: string;
  case_number?: string;
  case_title?: string;
  title: string;
  deadline_date: string;
  priority: string;
  status: string;
  days_until?: number;
  days_overdue?: number;
}

export interface DashboardStats {
  total_cases: number;
  total_deadlines: number;
  deadlines_this_week: number;
  overdue_deadlines: number;
  deadline_alerts: {
    overdue: { count: number; deadlines: DashboardDeadline[] };
    urgent: { count: number; deadlines: DashboardDeadline[] };
    upcoming_week: { count: number; deadlines: DashboardDeadline[] };
    upcoming_month: { count: number; deadlines: DashboardDeadline[] };
  };
  recent_activity: ActivityItem[];
  critical_cases: CriticalCase[];
  upcoming_deadlines: DashboardDeadline[];
}

export interface ActivityItem {
  id: string;
  type: 'deadline_completed' | 'document_uploaded' | 'case_created' | 'deadline_created';
  title: string;
  description?: string;
  case_id?: string;
  case_title?: string;
  timestamp: string;
}

export interface CriticalCase {
  id: string;
  case_number: string;
  title: string;
  overdue_count: number;
  urgent_count: number;
  next_deadline?: {
    title: string;
    date: string;
    priority: string;
  };
}

// Search result types
export interface SearchResults {
  query: string;
  cases: Case[];
  documents: Document[];
  deadlines: Deadline[];
  total_results: number;
}

// Calendar event type
export interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  resource?: {
    deadline: Deadline;
    case_number?: string;
    case_title?: string;
  };
}

// =========================================================================
// Phase 1: Document Classification Types
// =========================================================================

export interface DocumentClassification {
  status: 'pending' | 'matched' | 'unrecognized' | 'needs_research' | 'researched' | 'manual';
  document_category?: string;
  matched_trigger_type?: string;
  matched_pattern?: string;
  confidence?: number;
  potential_trigger_event?: string;
  response_required?: boolean;
  response_party?: string;
  response_deadline_days?: number;
  procedural_posture?: string;
  relief_sought?: string;
  urgency_indicators?: string[];
  rule_references?: string[];
  suggested_action?: 'apply_rules' | 'research_deadlines' | 'manual_review' | 'review_proposal' | 'none';
}

export interface ClassifiedDocument extends Document {
  classification?: DocumentClassification;
}

// =========================================================================
// Phase 2: Rule Proposal Types
// =========================================================================

export interface RuleProposalConflict {
  type: 'STANDARD_DEVIATION' | 'LOCAL_RULE_OVERRIDE' | 'FEDERAL_STATE_CONFLICT' | 'CITATION_MISMATCH';
  message: string;
  existing_days?: number;
  proposed_days?: number;
  severity: 'warning' | 'error';
}

export interface RuleProposal {
  id: string;
  case_id?: string;
  document_id?: string;
  user_id: string;
  proposed_trigger: string;
  proposed_trigger_type?: string;
  proposed_days: number;
  proposed_priority: 'informational' | 'standard' | 'important' | 'critical' | 'fatal';
  proposed_calculation_method?: 'calendar_days' | 'business_days' | 'court_days';
  citation?: string;
  citation_url?: string;
  source_text?: string;
  reasoning?: string;
  confidence_score?: number;
  conflicts?: RuleProposalConflict[];
  warnings?: string[];
  status: 'pending' | 'approved' | 'rejected' | 'modified';
  reviewed_by?: string;
  reviewed_at?: string;
  user_notes?: string;
  created_rule_template_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface RuleProposalListResponse {
  success: boolean;
  total: number;
  skip: number;
  limit: number;
  proposals: RuleProposal[];
  pending_count: number;
}

export interface ResearchResult {
  success: boolean;
  document_id?: string;
  proposal_id?: string;
  proposal?: {
    proposed_trigger: string;
    proposed_days: number;
    proposed_priority: string;
    citation?: string;
    confidence_score?: number;
    conflicts?: RuleProposalConflict[];
  };
  research_summary: string;
  error?: string;
}

// Extended upload response with classification
export interface ClassifiedUploadResponse extends UploadResponse {
  classification?: {
    classification_status: string;
    detected_document_type: string;
    classification_confidence?: number;
    suggested_action?: string;
    potential_trigger_event?: string;
    response_required?: boolean;
    matched_trigger_type?: string;
  };
}
