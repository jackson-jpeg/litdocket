'use client';

/**
 * PendingApprovalsIndicator - AI Staging Area UI
 *
 * The "Four-Eyes Guardrail" indicator.
 * Shows flashing amber when AI has proposed actions awaiting human approval.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabase';

interface PendingAction {
  id: string;
  action_type: string;
  target_table: string;
  payload: Record<string, unknown>;
  confidence: number;
  reasoning: string | null;
  source_text: string | null;
  created_at: string;
  expires_at: string;
}

interface PendingApprovalsIndicatorProps {
  onViewAll?: () => void;
  className?: string;
}

export function PendingApprovalsIndicator({
  onViewAll,
  className = '',
}: PendingApprovalsIndicatorProps) {
  const [count, setCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  const fetchCount = useCallback(async () => {
    try {
      const { data, error } = await supabase.rpc('get_pending_actions_count');

      if (error) throw error;
      setCount(data || 0);
    } catch (err) {
      console.error('Failed to fetch pending actions count:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchCount();
  }, [fetchCount]);

  // Subscribe to real-time changes
  useEffect(() => {
    const channel = supabase
      .channel('pending_actions_changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'pending_docket_actions',
        },
        () => {
          // Refetch count on any change
          fetchCount();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchCount]);

  if (loading) {
    return null;
  }

  if (count === 0) {
    return null;
  }

  return (
    <button
      onClick={onViewAll}
      className={`
        relative flex items-center gap-2 px-3 py-1
        bg-warning/20 border border-warning
        text-warning text-sm font-medium
        animate-pulse hover:animate-none
        ${className}
      `}
      title={`${count} AI-proposed action${count > 1 ? 's' : ''} awaiting your approval`}
    >
      {/* Amber flashing dot */}
      <span className="relative flex h-3 w-3">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75" />
        <span className="relative inline-flex rounded-full h-3 w-3 bg-warning" />
      </span>

      <span>
        {count} Pending Approval{count > 1 ? 's' : ''}
      </span>
    </button>
  );
}

/**
 * PendingApprovalsPanel - Full panel to review AI proposals
 */
interface PendingApprovalsPanelProps {
  onClose?: () => void;
  className?: string;
}

export function PendingApprovalsPanel({
  onClose,
  className = '',
}: PendingApprovalsPanelProps) {
  const [actions, setActions] = useState<PendingAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);

  const fetchActions = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('pending_docket_actions')
        .select('*')
        .eq('status', 'pending')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setActions(data || []);
    } catch (err) {
      console.error('Failed to fetch pending actions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  const handleApprove = async (actionId: string) => {
    setProcessing(actionId);
    try {
      const { error } = await supabase.rpc('approve_pending_action', {
        action_id: actionId,
        review_notes: 'Approved via UI',
      });

      if (error) throw error;
      fetchActions();
    } catch (err) {
      console.error('Failed to approve action:', err);
      alert('Failed to approve: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (actionId: string) => {
    const reason = prompt('Rejection reason (required):');
    if (!reason) return;

    setProcessing(actionId);
    try {
      const { error } = await supabase.rpc('reject_pending_action', {
        action_id: actionId,
        rejection_reason: reason,
      });

      if (error) throw error;
      fetchActions();
    } catch (err) {
      console.error('Failed to reject action:', err);
      alert('Failed to reject: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setProcessing(null);
    }
  };

  const formatActionType = (type: string) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.9) return 'badge-success';
    if (confidence >= 0.7) return 'badge-info';
    if (confidence >= 0.5) return 'badge-warning';
    return 'badge-critical';
  };

  return (
    <div className={`window-frame ${className}`}>
      <div className="window-titlebar flex items-center justify-between">
        <span className="window-titlebar-text">AI Proposals Awaiting Approval</span>
        {onClose && (
          <button onClick={onClose} className="text-white hover:bg-white/20 px-2">
            ×
          </button>
        )}
      </div>

      <div className="window-content max-h-96 overflow-y-auto classic-scrollbar">
        {loading ? (
          <div className="text-center py-8 text-grey-500">Loading...</div>
        ) : actions.length === 0 ? (
          <div className="text-center py-8 text-grey-500">
            No pending approvals
          </div>
        ) : (
          <div className="space-y-2">
            {actions.map((action) => (
              <div
                key={action.id}
                className="panel-inset p-3"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="badge-info font-mono text-xs">
                      {formatActionType(action.action_type)}
                    </span>
                    <span className={`ml-2 ${getConfidenceBadge(action.confidence)}`}>
                      {Math.round(action.confidence * 100)}% confident
                    </span>
                  </div>
                  <span className="text-xs text-grey-400">
                    {new Date(action.created_at).toLocaleString()}
                  </span>
                </div>

                {/* Payload preview */}
                <div className="mb-2">
                  {action.action_type === 'CREATE_DEADLINE' && (
                    <div className="text-sm">
                      <p className="font-semibold">
                        {(action.payload as { title?: string }).title || 'Untitled'}
                      </p>
                      <p className="text-grey-600">
                        Due: {(action.payload as { deadline_date?: string }).deadline_date || 'Unknown'}
                      </p>
                    </div>
                  )}
                  {action.action_type === 'CREATE_TRIGGER' && (
                    <div className="text-sm">
                      <p className="font-semibold">
                        {(action.payload as { trigger_type?: string }).trigger_type || 'Unknown trigger'}
                      </p>
                      <p className="text-grey-600">
                        Date: {(action.payload as { trigger_date?: string }).trigger_date || 'Unknown'}
                      </p>
                    </div>
                  )}
                </div>

                {/* AI Reasoning */}
                {action.reasoning && (
                  <div className="bg-surface p-2 mb-2 text-xs">
                    <span className="font-semibold text-grey-600">AI Reasoning: </span>
                    <span className="text-grey-700">{action.reasoning}</span>
                  </div>
                )}

                {/* Source text excerpt */}
                {action.source_text && (
                  <div className="bg-surface p-2 mb-2 text-xs border-l-2 border-navy">
                    <span className="font-semibold text-grey-600">Source: </span>
                    <span className="text-grey-700 italic">
                      "{action.source_text.slice(0, 150)}
                      {action.source_text.length > 150 ? '...' : ''}"
                    </span>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={() => handleApprove(action.id)}
                    disabled={processing === action.id}
                    className="btn-beveled-primary text-xs px-3 py-1"
                  >
                    {processing === action.id ? 'Processing...' : 'Approve'}
                  </button>
                  <button
                    onClick={() => handleReject(action.id)}
                    disabled={processing === action.id}
                    className="btn-beveled text-xs px-3 py-1"
                  >
                    Reject
                  </button>
                  <button
                    className="btn-beveled text-xs px-3 py-1"
                    title="View full details"
                  >
                    Details
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-grey-300 bg-surface-dark px-3 py-2 text-xs text-grey-600">
        AI proposals require human approval before affecting the docket.
        The AI is the researcher; you are the signer.
      </div>
    </div>
  );
}

export default PendingApprovalsIndicator;
