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
  metadata?: any;
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
  created_at: string;
}

export interface Trigger {
  id: string;
  trigger_type: string;
  trigger_date: string;
  title: string;
  dependent_deadlines_count: number;
  status?: string;  // Optional: pending, completed, cancelled
  created_at: string;
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
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to load case data';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  const fetchDocuments = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/cases/${caseId}/documents`);
      setDocuments(response.data);
    } catch (err) {
      console.error('Failed to load documents:', err);
      throw err;
    }
  }, [caseId]);

  const fetchDeadlines = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/deadlines/case/${caseId}`);
      setDeadlines(response.data);
    } catch (err) {
      console.error('Failed to load deadlines:', err);
      throw err;
    }
  }, [caseId]);

  const fetchTriggers = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/triggers/case/${caseId}/triggers`);
      setTriggers(response.data);
    } catch (err) {
      console.error('Failed to load triggers:', err);
      throw err;
    }
  }, [caseId]);

  const fetchCaseSummary = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/v1/cases/${caseId}/summary`);
      setCaseSummary(response.data);
    } catch (err) {
      console.error('Failed to load case summary:', err);
      throw err;
    }
  }, [caseId]);

  const refreshAll = useCallback(async () => {
    await Promise.all([
      fetchCaseData(),
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
    },
  };
}
