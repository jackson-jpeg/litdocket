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
  parties?: any[];
  metadata?: any;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  case_id: string;
  file_name: string;
  document_type?: string;
  filing_date?: string;
  ai_summary?: string;
  extracted_metadata?: any;
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
  priority: string;
  status: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  context_rules?: string[];
  context_documents?: string[];
  created_at: string;
}

export interface UploadResponse {
  success: boolean;
  document_id: string;
  case_id: string;
  case_created: boolean;
  analysis: any;
  redirect_url: string;
  message: string;
}
