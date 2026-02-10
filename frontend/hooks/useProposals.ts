/**
 * useProposals - Hook for managing AI proposal workflow
 *
 * Phase 7 Step 11: Safety Rails
 * Provides functions to fetch, approve, and reject AI-proposed actions.
 */

import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api-client';
import { Proposal } from '@/types';

interface UseProposalsReturn {
  proposals: Proposal[];
  loading: boolean;
  error: string | null;
  fetchProposals: (caseId: string, status?: string) => Promise<void>;
  fetchPendingProposals: () => Promise<void>;
  fetchProposal: (proposalId: string) => Promise<Proposal | null>;
  approveProposal: (proposalId: string) => Promise<{ success: boolean; result?: any; error?: string }>;
  rejectProposal: (proposalId: string, reason?: string) => Promise<{ success: boolean; error?: string }>;
  clearError: () => void;
}

export function useProposals(): UseProposalsReturn {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch all proposals for a specific case
   */
  const fetchProposals = useCallback(async (caseId: string, status?: string) => {
    try {
      setLoading(true);
      setError(null);

      const params = status ? `?status=${status}` : '';
      const response = await apiClient.get(`/proposals/case/${caseId}${params}`);

      if (response.data.success) {
        setProposals(response.data.proposals || []);
      } else {
        throw new Error(response.data.message || 'Failed to fetch proposals');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch proposals';
      setError(errorMessage);
      console.error('Error fetching proposals:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Fetch all pending proposals for the current user across all cases
   */
  const fetchPendingProposals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get('/proposals/pending');

      if (response.data.success) {
        setProposals(response.data.proposals || []);
      } else {
        throw new Error(response.data.message || 'Failed to fetch pending proposals');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch pending proposals';
      setError(errorMessage);
      console.error('Error fetching pending proposals:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Fetch a specific proposal by ID
   */
  const fetchProposal = useCallback(async (proposalId: string): Promise<Proposal | null> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get(`/proposals/${proposalId}`);

      if (response.data.success) {
        return response.data.proposal;
      } else {
        throw new Error(response.data.message || 'Failed to fetch proposal');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch proposal';
      setError(errorMessage);
      console.error('Error fetching proposal:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Approve a proposal and execute the proposed action
   */
  const approveProposal = useCallback(async (proposalId: string) => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post(`/proposals/${proposalId}/approve`);

      if (response.data.success) {
        // Remove the approved proposal from the list
        setProposals(prev => prev.filter(p => p.id !== proposalId));

        return {
          success: true,
          result: response.data.result
        };
      } else {
        throw new Error(response.data.detail || 'Failed to approve proposal');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to approve proposal';
      setError(errorMessage);
      console.error('Error approving proposal:', err);

      return {
        success: false,
        error: errorMessage
      };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Reject a proposal without executing the action
   */
  const rejectProposal = useCallback(async (proposalId: string, reason?: string) => {
    try {
      setLoading(true);
      setError(null);

      const params = reason ? `?reason=${encodeURIComponent(reason)}` : '';
      const response = await apiClient.post(`/proposals/${proposalId}/reject${params}`);

      if (response.data.success) {
        // Remove the rejected proposal from the list
        setProposals(prev => prev.filter(p => p.id !== proposalId));

        return { success: true };
      } else {
        throw new Error(response.data.detail || 'Failed to reject proposal');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reject proposal';
      setError(errorMessage);
      console.error('Error rejecting proposal:', err);

      return {
        success: false,
        error: errorMessage
      };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Clear the current error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    proposals,
    loading,
    error,
    fetchProposals,
    fetchPendingProposals,
    fetchProposal,
    approveProposal,
    rejectProposal,
    clearError,
  };
}
