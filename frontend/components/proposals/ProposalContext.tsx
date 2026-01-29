'use client';

/**
 * ProposalContext - Global state management for rule proposals
 *
 * Phase 3 of intelligent document recognition - "Glass Box" transparency
 *
 * Provides:
 * - Global pending proposal count (for header badge)
 * - Selected proposal state for drawer
 * - Actions for approve/reject/modify
 */

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import apiClient from '@/lib/api-client';
import type { RuleProposal } from '@/types';

interface ProposalContextState {
  // Global state
  pendingCount: number;
  isLoading: boolean;
  error: string | null;

  // Selected proposal for drawer
  selectedProposal: RuleProposal | null;
  isDrawerOpen: boolean;

  // Actions
  refreshPendingCount: () => Promise<void>;
  selectProposal: (proposal: RuleProposal) => void;
  clearSelection: () => void;
  approveProposal: (proposalId: string, notes?: string) => Promise<boolean>;
  rejectProposal: (proposalId: string, reason?: string) => Promise<boolean>;
  modifyProposal: (
    proposalId: string,
    modifications: ProposalModifications,
    notes?: string
  ) => Promise<boolean>;
  researchDocument: (documentId: string) => Promise<RuleProposal | null>;
}

interface ProposalModifications {
  proposed_trigger?: string;
  proposed_days?: number;
  proposed_priority?: string;
  proposed_calculation_method?: string;
}

const ProposalContext = createContext<ProposalContextState | undefined>(undefined);

interface ProposalProviderProps {
  children: ReactNode;
}

export function ProposalProvider({ children }: ProposalProviderProps) {
  const [pendingCount, setPendingCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProposal, setSelectedProposal] = useState<RuleProposal | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Fetch pending count
  const refreshPendingCount = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/v1/rule-proposals?status=pending&limit=1');
      setPendingCount(response.data.pending_count || 0);
    } catch (err) {
      console.error('Failed to fetch pending proposal count:', err);
    }
  }, []);

  // Select a proposal and open drawer
  const selectProposal = useCallback((proposal: RuleProposal) => {
    setSelectedProposal(proposal);
    setIsDrawerOpen(true);
  }, []);

  // Clear selection and close drawer
  const clearSelection = useCallback(() => {
    setSelectedProposal(null);
    setIsDrawerOpen(false);
  }, []);

  // Approve a proposal
  const approveProposal = useCallback(
    async (proposalId: string, notes?: string): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        await apiClient.post(`/api/v1/rule-proposals/${proposalId}/approve`, { notes });

        // Update count
        setPendingCount((prev) => Math.max(0, prev - 1));

        // Close drawer if this was the selected proposal
        if (selectedProposal?.id === proposalId) {
          clearSelection();
        }

        return true;
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        const errorMsg = axiosError.response?.data?.detail || 'Failed to approve proposal';
        setError(errorMsg);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [selectedProposal, clearSelection]
  );

  // Reject a proposal
  const rejectProposal = useCallback(
    async (proposalId: string, reason?: string): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        await apiClient.post(`/api/v1/rule-proposals/${proposalId}/reject`, { notes: reason });

        // Update count
        setPendingCount((prev) => Math.max(0, prev - 1));

        // Close drawer if this was the selected proposal
        if (selectedProposal?.id === proposalId) {
          clearSelection();
        }

        return true;
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        const errorMsg = axiosError.response?.data?.detail || 'Failed to reject proposal';
        setError(errorMsg);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [selectedProposal, clearSelection]
  );

  // Modify and approve a proposal
  const modifyProposal = useCallback(
    async (
      proposalId: string,
      modifications: ProposalModifications,
      notes?: string
    ): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        await apiClient.put(`/api/v1/rule-proposals/${proposalId}/modify`, {
          ...modifications,
          notes,
        });

        // Update count
        setPendingCount((prev) => Math.max(0, prev - 1));

        // Close drawer if this was the selected proposal
        if (selectedProposal?.id === proposalId) {
          clearSelection();
        }

        return true;
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        const errorMsg = axiosError.response?.data?.detail || 'Failed to modify proposal';
        setError(errorMsg);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [selectedProposal, clearSelection]
  );

  // Research deadlines for a document
  const researchDocument = useCallback(async (documentId: string): Promise<RuleProposal | null> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await apiClient.post(`/api/v1/documents/${documentId}/research-deadlines`);

      if (response.data.success && response.data.proposal_id) {
        // Fetch the full proposal
        const proposalResponse = await apiClient.get(
          `/api/v1/rule-proposals/${response.data.proposal_id}`
        );
        const proposal = proposalResponse.data;

        // Update count
        setPendingCount((prev) => prev + 1);

        // Open the drawer with the new proposal
        selectProposal(proposal);

        return proposal;
      }

      return null;
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Failed to research document';
      setError(errorMsg);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [selectProposal]);

  // Initial load
  useEffect(() => {
    refreshPendingCount();
  }, [refreshPendingCount]);

  const value: ProposalContextState = {
    pendingCount,
    isLoading,
    error,
    selectedProposal,
    isDrawerOpen,
    refreshPendingCount,
    selectProposal,
    clearSelection,
    approveProposal,
    rejectProposal,
    modifyProposal,
    researchDocument,
  };

  return <ProposalContext.Provider value={value}>{children}</ProposalContext.Provider>;
}

export function useProposalContext(): ProposalContextState {
  const context = useContext(ProposalContext);

  if (context === undefined) {
    throw new Error('useProposalContext must be used within a ProposalProvider');
  }

  return context;
}
