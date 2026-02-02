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

export interface Deadline {
  id: string;
  case_id: string;
  title: string;
  description?: string;
  deadline_date: string;
  deadline_time?: string;
  deadline_type?: string;
  applicable_rule?: string;
  rule_citation?: string;
  calculation_basis?: string;
  priority: 'informational' | 'standard' | 'important' | 'critical' | 'fatal';
  status: 'pending' | 'completed' | 'cancelled';
  party_role?: string;
  action_required?: string;
  trigger_event?: string;
  trigger_date?: string;
  is_estimated?: boolean;
  is_calculated?: boolean;
  is_dependent?: boolean;
  is_manually_overridden?: boolean;
  confidence_score?: number;
  confidence_level?: 'low' | 'medium' | 'high';
  verification_status?: 'pending' | 'verified' | 'rejected';
  created_at?: string;
  updated_at?: string;
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

// =============================================================================
// AUTHORITY CORE TYPES - AI-Powered Rules Database
// =============================================================================

export type AuthorityTier = 'federal' | 'state' | 'local' | 'standing_order' | 'firm';
export type ProposalStatus = 'pending' | 'approved' | 'rejected' | 'needs_revision';
export type ScrapeStatus = 'queued' | 'searching' | 'extracting' | 'completed' | 'failed';
export type ConflictResolution = 'pending' | 'use_higher_tier' | 'use_rule_a' | 'use_rule_b' | 'manual' | 'ignored';

export interface DeadlineSpec {
  title: string;
  days_from_trigger: number;
  calculation_method: 'calendar_days' | 'business_days' | 'court_days';
  priority: string;
  party_responsible?: string;
  conditions?: Record<string, unknown>;
  description?: string;
}

export interface ServiceExtensions {
  mail: number;
  electronic: number;
  personal: number;
}

export interface RuleConditions {
  case_types?: string[];
  motion_types?: string[];
  service_methods?: string[];
  exclusions?: Record<string, unknown>;
}

export interface AuthorityRule {
  id: string;
  jurisdiction_id?: string;
  jurisdiction_name?: string;
  user_id?: string;
  rule_code: string;
  rule_name: string;
  trigger_type: string;
  authority_tier: AuthorityTier;
  citation?: string;
  source_url?: string;
  source_text?: string;
  deadlines: DeadlineSpec[];
  conditions?: RuleConditions;
  service_extensions?: ServiceExtensions;
  confidence_score: number;
  is_verified: boolean;
  verified_by?: string;
  verified_at?: string;
  is_active: boolean;
  effective_date?: string;
  superseded_date?: string;
  created_at: string;
  updated_at: string;
  usage_count?: number;
}

export interface ScrapeJob {
  id: string;
  user_id: string;
  jurisdiction_id?: string;
  jurisdiction_name?: string;
  search_query: string;
  status: ScrapeStatus;
  progress_pct: number;
  rules_found: number;
  proposals_created: number;
  urls_processed: string[];
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ScrapeProgress {
  job_id: string;
  status: ScrapeStatus;
  progress_pct: number;
  message: string;
  urls_processed: string[];
  rules_found: number;
  current_action?: string;
}

export interface RuleProposal {
  id: string;
  user_id: string;
  scrape_job_id?: string;
  jurisdiction_id?: string;
  jurisdiction_name?: string;
  proposed_rule_data: {
    rule_code: string;
    rule_name: string;
    trigger_type: string;
    authority_tier: AuthorityTier;
    citation?: string;
    deadlines: DeadlineSpec[];
    conditions?: RuleConditions;
    service_extensions?: ServiceExtensions;
  };
  source_url?: string;
  source_text?: string;
  confidence_score: number;
  extraction_notes?: string;
  status: ProposalStatus;
  reviewed_by?: string;
  reviewer_notes?: string;
  approved_rule_id?: string;
  created_at: string;
  reviewed_at?: string;
}

export interface RuleConflict {
  id: string;
  rule_a_id: string;
  rule_a_name?: string;
  rule_a_citation?: string;
  rule_b_id: string;
  rule_b_name?: string;
  rule_b_citation?: string;
  conflict_type: string;
  severity: 'info' | 'warning' | 'error';
  description: string;
  resolution: ConflictResolution;
  resolution_notes?: string;
  resolved_by?: string;
  resolved_at?: string;
  created_at: string;
}

export interface CalculatedDeadline {
  title: string;
  deadline_date: string;
  days_from_trigger: number;
  calculation_method: string;
  priority: string;
  party_responsible?: string;
  source_rule_id: string;
  citation?: string;
  rule_name: string;
}

// =============================================================================
// DOCUMENT DEADLINE SUGGESTIONS
// =============================================================================

export type SuggestionStatus = 'pending' | 'approved' | 'rejected' | 'expired';
export type ExtractionMethod = 'ai_key_dates' | 'ai_deadlines_mentioned' | 'trigger_detected';

export interface ConfidenceFactors {
  has_specific_date?: boolean;
  has_description?: boolean;
  has_rule_citation?: boolean;
  trigger_matched?: boolean;
  extraction_method?: string;
  matched_trigger?: string;
  expected_deadlines?: number;
  rejection_notes?: string;
}

export interface DeadlineSuggestion {
  id: string;
  document_id: string;
  case_id: string;
  title: string;
  description?: string;
  suggested_date?: string;
  deadline_type?: string;
  extraction_method: ExtractionMethod;
  source_text?: string;
  matched_trigger_type?: string;
  rule_citation?: string;
  confidence_score: number;
  confidence_factors: ConfidenceFactors;
  status: SuggestionStatus;
  reviewed_at?: string;
  created_deadline_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SuggestionListResponse {
  suggestions: DeadlineSuggestion[];
  total: number;
  pending_count: number;
  document_id: string;
}

export interface ApplySuggestionItem {
  suggestion_id: string;
  apply_as_trigger?: boolean;
  override_date?: string;
  override_title?: string;
}

export interface ApplySuggestionsRequest {
  suggestions: ApplySuggestionItem[];
}

export interface ApplySuggestionsResult {
  suggestion_id: string;
  success: boolean;
  deadline_id?: string;
  cascade_count?: number;
  error?: string;
  message?: string;
}

export interface ApplySuggestionsResponse {
  success: boolean;
  results: ApplySuggestionsResult[];
  total_deadlines_created: number;
  total_cascade_deadlines: number;
  message: string;
}

export interface CasePendingSuggestions {
  case_id: string;
  total_pending: number;
  suggestions: DeadlineSuggestion[];
  by_document: Record<string, DeadlineSuggestion[]>;
}

// =============================================================================
// ENHANCED CASE RECOMMENDATIONS (Action Plan)
// =============================================================================

export type RecommendationStatus = 'pending' | 'in_progress' | 'completed' | 'dismissed' | 'expired';
export type UrgencyLevel = 'critical' | 'high' | 'medium' | 'low';

export interface SuggestedTool {
  tool: string;
  action: string;
  params?: Record<string, unknown>;
}

export interface TriggeredByDeadline {
  id: string;
  title: string;
  deadline_date?: string;
  priority: string;
}

export interface EnhancedRecommendation {
  id: string;
  case_id: string;
  priority: number;
  action: string;
  reasoning?: string;
  category: string;
  triggered_by_deadline_id?: string;
  triggered_by_deadline?: TriggeredByDeadline;
  triggered_by_document_id?: string;
  rule_citations: string[];
  consequence_if_ignored?: string;
  urgency_level: UrgencyLevel;
  days_until_consequence?: number;
  suggested_tools: SuggestedTool[];
  suggested_document_types: string[];
  status: RecommendationStatus;
  completed_at?: string;
  dismissed_at?: string;
  dismissed_reason?: string;
  expires_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ActionPlanResponse {
  case_id: string;
  total_recommendations: number;
  by_urgency: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  recommendations: EnhancedRecommendation[];
  grouped: {
    critical: EnhancedRecommendation[];
    high: EnhancedRecommendation[];
    medium: EnhancedRecommendation[];
    low: EnhancedRecommendation[];
  };
}

// =============================================================================
// CASE SHARING & ACCESS CONTROL
// =============================================================================

export type CaseAccessRole = 'owner' | 'editor' | 'viewer';

export interface CaseAccessUser {
  id: string;
  email: string;
  name?: string;
}

export interface CaseAccess {
  id: string;
  case_id: string;
  user_id?: string;
  role: CaseAccessRole;
  is_active: boolean;
  invited_email?: string;
  invitation_accepted_at?: string;
  created_at: string;
  updated_at?: string;
  user?: CaseAccessUser;
}

export interface CaseAccessListResponse {
  case_id: string;
  owner_id: string;
  access_grants: CaseAccess[];
  total: number;
}

export interface ShareCaseRequest {
  email: string;
  role: CaseAccessRole;
}

export interface ShareCaseResponse {
  success: boolean;
  message: string;
  access: CaseAccess;
  user_exists: boolean;
}

export interface CasePresenceUser {
  user_id: string;
  name: string;
  email?: string;
  last_activity?: string;
  is_current_user: boolean;
}

export interface CasePresenceResponse {
  case_id: string;
  active_users: CasePresenceUser[];
  total: number;
}

export interface SharedCaseItem {
  access: CaseAccess;
  case: {
    id: string;
    case_number: string;
    title: string;
    court?: string;
    status: string;
  };
}

export interface SharedCasesResponse {
  shared_cases: SharedCaseItem[];
  total: number;
}
