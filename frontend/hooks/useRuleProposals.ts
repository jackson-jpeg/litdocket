/**
 * Custom hook for managing rule proposals (AI-discovered rules pending attorney review)
 *
 * Phase 3 of intelligent document recognition - "Glass Box" transparency
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api-client';
import type { RuleProposal, RuleProposalConflict } from '@/types';

export interface RuleProposalFilters {
  status?: 'pending' | 'approved' | 'rejected' | 'modified';
  caseId?: string;
  documentId?: string;
}

export interface RuleProposalListResponse {
  success: boolean;
  total: number;
  skip: number;
  limit: number;
  proposals: RuleProposal[];
  pending_count: number;
}

export interface ApproveProposalOptions {
  proposalId: string;
  notes?: string;
  createDeadline?: boolean;
  caseId?: string;
}

export interface ModifyProposalOptions {
  proposalId: string;
  modifications: {
    proposed_days?: number;
    proposed_priority?: string;
    proposed_trigger?: string;
    proposed_calculation_method?: string;
  };
  notes?: string;
}

export function useRuleProposals(filters?: RuleProposalFilters) {
  const [proposals, setProposals] = useState<RuleProposal[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState<string | null>(null); // ID of proposal being processed

  // Fetch proposals
  const fetchProposals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters?.status) params.set('status', filters.status);
      if (filters?.caseId) params.set('case_id', filters.caseId);
      if (filters?.documentId) params.set('document_id', filters.documentId);

      const url = `/api/v1/rule-proposals${params.toString() ? `?${params.toString()}` : ''}`;
      const response = await apiClient.get<RuleProposalListResponse>(url);

      setProposals(response.data.proposals || []);
      setPendingCount(response.data.pending_count || 0);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Failed to load rule proposals';
      setError(errorMsg);
      console.error('Failed to load rule proposals:', err);
    } finally {
      setLoading(false);
    }
  }, [filters?.status, filters?.caseId, filters?.documentId]);

  // Approve a proposal
  const approveProposal = useCallback(async (options: ApproveProposalOptions): Promise<boolean> => {
    const { proposalId, notes, createDeadline, caseId } = options;

    try {
      setProcessing(proposalId);
      setError(null);

      await apiClient.post(`/api/v1/rule-proposals/${proposalId}/approve`, {
        notes,
        create_deadline: createDeadline,
        case_id: caseId,
      });

      // Optimistic update - remove from pending list
      setProposals(prev => prev.filter(p => p.id !== proposalId));
      setPendingCount(prev => Math.max(0, prev - 1));

      return true;
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Failed to approve proposal';
      setError(errorMsg);
      return false;
    } finally {
      setProcessing(null);
    }
  }, []);

  // Reject a proposal
  const rejectProposal = useCallback(async (proposalId: string, reason?: string): Promise<boolean> => {
    try {
      setProcessing(proposalId);
      setError(null);

      await apiClient.post(`/api/v1/rule-proposals/${proposalId}/reject`, {
        notes: reason,
      });

      // Optimistic update - remove from pending list
      setProposals(prev => prev.filter(p => p.id !== proposalId));
      setPendingCount(prev => Math.max(0, prev - 1));

      return true;
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Failed to reject proposal';
      setError(errorMsg);
      return false;
    } finally {
      setProcessing(null);
    }
  }, []);

  // Modify and approve a proposal
  const modifyProposal = useCallback(async (options: ModifyProposalOptions): Promise<boolean> => {
    const { proposalId, modifications, notes } = options;

    try {
      setProcessing(proposalId);
      setError(null);

      await apiClient.put(`/api/v1/rule-proposals/${proposalId}/modify`, {
        ...modifications,
        notes,
      });

      // Optimistic update - remove from pending list
      setProposals(prev => prev.filter(p => p.id !== proposalId));
      setPendingCount(prev => Math.max(0, prev - 1));

      return true;
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Failed to modify proposal';
      setError(errorMsg);
      return false;
    } finally {
      setProcessing(null);
    }
  }, []);

  // Research deadlines for a document
  const researchDocument = useCallback(async (documentId: string): Promise<RuleProposal | null> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post(`/api/v1/documents/${documentId}/research-deadlines`);

      if (response.data.success && response.data.proposal) {
        // Add new proposal to the list
        const newProposal: RuleProposal = {
          id: response.data.proposal_id,
          user_id: '', // Will be set by backend
          ...response.data.proposal,
          status: 'pending',
          created_at: new Date().toISOString(),
        };

        setProposals(prev => [newProposal, ...prev]);
        setPendingCount(prev => prev + 1);

        return newProposal;
      }

      return null;
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Failed to research document';
      setError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchProposals();
  }, [fetchProposals]);

  return {
    proposals,
    pendingCount,
    loading,
    error,
    processing,
    refetch: fetchProposals,
    approveProposal,
    rejectProposal,
    modifyProposal,
    researchDocument,
  };
}

// Helper hook for a single proposal
export function useRuleProposal(proposalId: string) {
  const [proposal, setProposal] = useState<RuleProposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProposal = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get(`/api/v1/rule-proposals/${proposalId}`);
      setProposal(response.data);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Failed to load proposal';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    if (proposalId) {
      fetchProposal();
    }
  }, [proposalId, fetchProposal]);

  return { proposal, loading, error, refetch: fetchProposal };
}
