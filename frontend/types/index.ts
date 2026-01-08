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
