/**
 * ProposalApprovalCard - Phase 7 Step 11: Safety Rails
 *
 * Displays AI-proposed actions from database that require user approval.
 * Different from ProposalCard which is for real-time blocking approvals.
 *
 * This component:
 * - Fetches proposal details from API
 * - Shows preview summary and affected items
 * - Provides Approve/Reject buttons
 * - Handles approval/rejection via API
 * - Emits events for UI updates
 */

'use client';

import React, { useState } from 'react';
import { AlertTriangle, Check, X, Clock, Sparkles } from 'lucide-react';
import { Proposal } from '@/types';
import { useProposals } from '@/hooks/useProposals';
import { deadlineEvents } from '@/lib/eventBus';

interface ProposalApprovalCardProps {
  proposal: Proposal;
  onApprovalComplete?: () => void;
}

export function ProposalApprovalCard({ proposal, onApprovalComplete }: ProposalApprovalCardProps) {
  const { approveProposal, rejectProposal, loading } = useProposals();
  const [localLoading, setLocalLoading] = useState(false);
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    setLocalLoading(true);
    setError(null);

    try {
      const result = await approveProposal(proposal.id);

      if (result.success) {
        // Emit event for deadline creation
        if (proposal.action_type === 'create_deadline') {
          deadlineEvents.created({ id: result.result?.resource_id });
        } else if (proposal.action_type === 'update_deadline') {
          deadlineEvents.updated({ id: result.result?.resource_id });
        } else if (proposal.action_type === 'delete_deadline') {
          deadlineEvents.deleted(result.result?.resource_id);
        }

        // Callback to parent
        if (onApprovalComplete) {
          onApprovalComplete();
        }
      } else {
        setError(result.error || 'Failed to approve proposal');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve proposal');
    } finally {
      setLocalLoading(false);
    }
  };

  const handleReject = async () => {
    setLocalLoading(true);
    setError(null);

    try {
      const result = await rejectProposal(proposal.id, rejectionReason);

      if (result.success) {
        // Callback to parent
        if (onApprovalComplete) {
          onApprovalComplete();
        }
      } else {
        setError(result.error || 'Failed to reject proposal');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject proposal');
    } finally {
      setLocalLoading(false);
    }
  };

  const getActionIcon = () => {
    if (proposal.action_type === 'create_deadline') return '📅';
    if (proposal.action_type === 'update_deadline') return '✏️';
    if (proposal.action_type === 'delete_deadline') return '🗑️';
    if (proposal.action_type === 'move_deadline') return '🔄';
    if (proposal.action_type === 'update_case') return '📋';
    return '⚙️';
  };

  const getActionLabel = () => {
    return proposal.action_type.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <div className="proposal-card bg-amber-900/20 border-2 border-amber-500 rounded p-4 my-3">
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <AlertTriangle className="w-6 h-6 text-amber-500" />
        <div className="flex-1">
          <h3 className="font-bold text-amber-500 text-lg flex items-center gap-2">
            <Sparkles className="w-5 h-5" />
            APPROVAL REQUIRED
          </h3>
          <p className="text-amber-300 text-sm">
            {getActionIcon()} {getActionLabel()}
          </p>
        </div>
        <div className="flex items-center gap-2 text-amber-400 text-xs">
          <Clock className="w-4 h-4" />
          {new Date(proposal.created_at).toLocaleTimeString()}
        </div>
      </div>

      {/* Preview Summary */}
      {proposal.preview_summary && (
        <div className="bg-slate-800 border border-slate-700 rounded p-3 mb-3">
          <p className="text-white font-semibold mb-1">Action:</p>
          <p className="text-slate-300">{proposal.preview_summary}</p>
        </div>
      )}

      {/* AI Reasoning */}
      {proposal.ai_reasoning && (
        <div className="mb-3 text-slate-300 text-sm italic border-l-2 border-cyan-500 pl-3">
          <span className="text-cyan-400 font-semibold">AI: </span>
          "{proposal.ai_reasoning}"
        </div>
      )}

      {/* Affected Items */}
      {proposal.affected_items && Object.keys(proposal.affected_items).length > 0 && (
        <div className="mb-3">
          <p className="text-white text-sm font-semibold mb-2">Impact:</p>
          <div className="bg-slate-800 p-3 rounded text-xs text-slate-300">
            {proposal.affected_items.estimated_deadlines && (
              <p>• Will create {proposal.affected_items.estimated_deadlines} deadlines</p>
            )}
            {proposal.affected_items.dependent_deadlines !== undefined && (
              <p>• Affects {proposal.affected_items.dependent_deadlines} dependent deadlines</p>
            )}
            {proposal.affected_items.type && (
              <p>• Type: {proposal.affected_items.type.replace('_', ' ')}</p>
            )}
          </div>
        </div>
      )}

      {/* Action Data (for power users) */}
      <details className="mb-3">
        <summary className="text-slate-400 text-xs cursor-pointer hover:text-slate-300">
          Show technical details
        </summary>
        <pre className="bg-slate-900 p-3 rounded text-xs overflow-auto max-h-48 text-slate-400 mt-2">
          {JSON.stringify(proposal.action_data, null, 2)}
        </pre>
      </details>

      {/* Error Display */}
      {error && (
        <div className="bg-red-900/30 border border-red-500/50 rounded p-3 mb-3 text-red-300 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Rejection Reason Input */}
      {showRejectInput && (
        <div className="mb-3">
          <input
            type="text"
            className="w-full bg-slate-700 text-white p-2 rounded text-sm border border-slate-600 focus:border-red-500 focus:outline-none"
            placeholder="Reason for rejection (optional)"
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleReject();
              }
            }}
          />
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleApprove}
          disabled={loading || localLoading}
          className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded transition-colors flex items-center justify-center gap-2"
        >
          <Check className="w-5 h-5" />
          {localLoading ? 'Approving...' : 'Approve'}
        </button>

        <button
          onClick={() => {
            if (showRejectInput) {
              handleReject();
            } else {
              setShowRejectInput(true);
            }
          }}
          disabled={loading || localLoading}
          className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-red-800 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded transition-colors flex items-center justify-center gap-2"
        >
          <X className="w-5 h-5" />
          {showRejectInput ? (localLoading ? 'Rejecting...' : 'Confirm Reject') : 'Reject'}
        </button>
      </div>

      {/* Info */}
      <div className="mt-3 text-xs text-slate-400 text-center">
        Proposal ID: {proposal.id.substring(0, 8)}...
      </div>
    </div>
  );
}

/**
 * ProposalList - Display multiple proposals
 */
interface ProposalListProps {
  proposals: Proposal[];
  onProposalResolved?: () => void;
}

export function ProposalList({ proposals, onProposalResolved }: ProposalListProps) {
  if (proposals.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        <Check className="w-12 h-12 mx-auto mb-3 text-green-500" />
        <p>No pending proposals</p>
        <p className="text-sm mt-1">All AI actions have been reviewed</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {proposals.map(proposal => (
        <ProposalApprovalCard
          key={proposal.id}
          proposal={proposal}
          onApprovalComplete={onProposalResolved}
        />
      ))}
    </div>
  );
}
