/**
 * Custom hook for managing case data fetching and state
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api-client';

export interface CaseData {
  id: string;
  case_number: string;
  title: string;
  court?: string;
  judge?: string;
  jurisdiction?: string;
  district?: string;
  case_type?: string;
  filing_date?: string;
  parties?: Array<{ name: string; role: string }>;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface Document {
  id: string;
  file_name: string;
  document_type?: string;
  filing_date?: string;
  ai_summary?: string;
  storage_url?: string;
  created_at: string;
}

export interface Deadline {
  id: string;
  title: string;
  description: string;
  deadline_date?: string;
  deadline_type: string;
  priority: string;
  status: string;
  party_role?: string;
  action_required?: string;
  applicable_rule?: string;
  calculation_basis?: string;
  is_estimated: boolean;
  is_calculated?: boolean;
  is_dependent?: boolean;
  trigger_event?: string;
  source_document?: string;
  service_method?: string;  // 'electronic' | 'mail' | 'personal'
  created_at: string;
  // Confidence scoring
  confidence_score?: number;  // 0-100
  confidence_level?: 'high' | 'medium' | 'low';
  extraction_method?: 'rule-based' | 'ai' | 'manual';
  verification_status?: 'pending' | 'verified' | 'disputed';
}

// Status summary for frontend badges (pre-calculated by backend)
export interface TriggerStatusSummary {
  overdue: number;
  pending: number;
  completed: number;
  cancelled: number;
  total: number;
}

// Child deadline in nested trigger response
export interface TriggerChildDeadline {
  id: string;
  title: string;
  description?: string;
  deadline_date: string | null;
  priority: string;
  status: string;
  is_overdue: boolean;
  applicable_rule?: string;
  calculation_basis?: string;
  party_role?: string;
  action_required?: string;
  is_manually_overridden: boolean;
  auto_recalculate: boolean;
}

export interface Trigger {
  id: string;
  trigger_type: string;
  trigger_date: string;
  title: string;
  status?: string;
  notes?: string;
  created_at: string;
  // V2 Nested Structure for Sovereign UI
  status_summary: TriggerStatusSummary;
  child_deadlines: TriggerChildDeadline[];
  // Legacy field for backwards compatibility
  dependent_deadlines_count: number;
}

export interface CaseSummary {
  overview: string;
  current_status: string;
  key_documents: string[];
  critical_deadlines: string[];
  timeline: string[];
  action_items: string[];
  last_updated: string;
}

export function useCaseData(caseId: string) {
  const [caseData, setCaseData] = useState<CaseData | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCaseData = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/cases/${caseId}`);
      setCaseData(response.data);
      setError(null);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Failed to load case data';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  const fetchDocuments = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/cases/${caseId}/documents`);
      setDocuments(response.data || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
      setDocuments([]);  // Don't break the page, just show empty
    }
  }, [caseId]);

  const fetchDeadlines = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/deadlines/case/${caseId}`);
      setDeadlines(response.data || []);
    } catch (err) {
      console.error('Failed to load deadlines:', err);
      setDeadlines([]);  // Don't break the page, just show empty
    }
  }, [caseId]);

  const fetchTriggers = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/triggers/case/${caseId}/triggers`);
      setTriggers(response.data || []);
    } catch (err) {
      console.error('Failed to load triggers:', err);
      setTriggers([]);  // Don't break the page, just show empty
    }
  }, [caseId]);

  const fetchCaseSummary = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/cases/${caseId}/summary`);
      setCaseSummary(response.data);
    } catch (err) {
      console.error('Failed to load case summary:', err);
      // Case summary is optional, don't break the page
    }
  }, [caseId]);

  const refreshAll = useCallback(async () => {
    // Fetch case data first (critical), then others in parallel (non-critical)
    try {
      await fetchCaseData();
    } catch (err) {
      // If case data fails, the error state is already set
      return;
    }

    // These are all non-critical, fetch in parallel with individual error handling
    await Promise.all([
      fetchDocuments(),
      fetchDeadlines(),
      fetchTriggers(),
      fetchCaseSummary(),
    ]);
  }, [fetchCaseData, fetchDocuments, fetchDeadlines, fetchTriggers, fetchCaseSummary]);

  useEffect(() => {
    refreshAll();
  }, [caseId]);

  // Optimistic update functions for immediate UI feedback
  const updateDeadlineStatus = useCallback((deadlineId: string, newStatus: string) => {
    setDeadlines(prev => prev.map(d =>
      d.id === deadlineId ? { ...d, status: newStatus } : d
    ));
  }, []);

  const removeDeadline = useCallback((deadlineId: string) => {
    setDeadlines(prev => prev.filter(d => d.id !== deadlineId));
  }, []);

  const removeDocument = useCallback((documentId: string) => {
    setDocuments(prev => prev.filter(d => d.id !== documentId));
  }, []);

  const updateDeadlineDate = useCallback((deadlineId: string, newDate: string) => {
    setDeadlines(prev => prev.map(d =>
      d.id === deadlineId ? { ...d, deadline_date: newDate } : d
    ));
  }, []);

  return {
    caseData,
    documents,
    deadlines,
    triggers,
    caseSummary,
    loading,
    error,
    refetch: {
      caseData: fetchCaseData,
      documents: fetchDocuments,
      deadlines: fetchDeadlines,
      triggers: fetchTriggers,
      caseSummary: fetchCaseSummary,
      all: refreshAll,
    },
    // Optimistic updates for immediate UI feedback
    optimistic: {
      updateDeadlineStatus,
      removeDeadline,
      updateDeadlineDate,
      removeDocument,
    },
  };
}
