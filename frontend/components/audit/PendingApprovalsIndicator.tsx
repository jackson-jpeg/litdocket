'use client';

/**
 * PendingApprovalsIndicator - AI Staging Area UI
 *
 * The "Four-Eyes Guardrail" indicator.
 * Shows flashing amber when AI has proposed actions awaiting human approval.
 */

import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api-client';

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
      const response = await apiClient.get('/api/v1/audit/pending/count');
      setCount(response.data?.count || 0);
    } catch (err) {
      // Silently fail - this is a non-critical UI element
      setCount(0);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and polling
  useEffect(() => {
    fetchCount();

    // Poll every 30 seconds for updates
    const interval = setInterval(fetchCount, 30000);

    return () => clearInterval(interval);
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
        relative flex items-center gap-2 px-3 py-1.5
        bg-amber-50 border border-amber-400
        text-amber-700 text-sm font-medium rounded-lg
        animate-pulse hover:animate-none hover:bg-amber-100
        transition-colors
        ${className}
      `}
      title={`${count} AI-proposed action${count > 1 ? 's' : ''} awaiting your approval`}
    >
      {/* Amber flashing dot */}
      <span className="relative flex h-3 w-3">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500" />
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
      const response = await apiClient.get('/api/v1/audit/pending');
      setActions(response.data || []);
    } catch (err) {
      setActions([]);
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
      await apiClient.post(`/api/v1/audit/actions/${actionId}/approve`, {
        review_notes: 'Approved via UI',
      });
      fetchActions();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      alert('Failed to approve: ' + (axiosError.response?.data?.detail || 'Unknown error'));
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (actionId: string) => {
    const reason = prompt('Rejection reason (required):');
    if (!reason) return;

    setProcessing(actionId);
    try {
      await apiClient.post(`/api/v1/audit/actions/${actionId}/reject`, {
        rejection_reason: reason,
      });
      fetchActions();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      alert('Failed to reject: ' + (axiosError.response?.data?.detail || 'Unknown error'));
    } finally {
      setProcessing(null);
    }
  };

  const formatActionType = (type: string) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  const getConfidenceBadgeColor = (confidence: number) => {
    if (confidence >= 0.9) return 'bg-green-100 text-green-700';
    if (confidence >= 0.7) return 'bg-blue-100 text-blue-700';
    if (confidence >= 0.5) return 'bg-amber-100 text-amber-700';
    return 'bg-red-100 text-red-700';
  };

  return (
    <div className={`bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-800 text-white">
        <span className="font-semibold">AI Proposals Awaiting Approval</span>
        {onClose && (
          <button onClick={onClose} className="text-white hover:bg-white/20 px-2 py-1 rounded">
            ×
          </button>
        )}
      </div>

      {/* Content */}
      <div className="max-h-96 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center py-8 text-slate-500">Loading...</div>
        ) : actions.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            No pending approvals
          </div>
        ) : (
          <div className="space-y-3">
            {actions.map((action) => (
              <div
                key={action.id}
                className="border border-slate-200 rounded-lg p-4 bg-slate-50"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                      {formatActionType(action.action_type)}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${getConfidenceBadgeColor(action.confidence)}`}>
                      {Math.round(action.confidence * 100)}% confident
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {new Date(action.created_at).toLocaleString()}
                  </span>
                </div>

                {/* Payload preview */}
                <div className="mb-2">
                  {action.action_type === 'CREATE_DEADLINE' && (
                    <div className="text-sm">
                      <p className="font-semibold text-slate-900">
                        {(action.payload as { title?: string }).title || 'Untitled'}
                      </p>
                      <p className="text-slate-600">
                        Due: {(action.payload as { deadline_date?: string }).deadline_date || 'Unknown'}
                      </p>
                    </div>
                  )}
                  {action.action_type === 'CREATE_TRIGGER' && (
                    <div className="text-sm">
                      <p className="font-semibold text-slate-900">
                        {(action.payload as { trigger_type?: string }).trigger_type || 'Unknown trigger'}
                      </p>
                      <p className="text-slate-600">
                        Date: {(action.payload as { trigger_date?: string }).trigger_date || 'Unknown'}
                      </p>
                    </div>
                  )}
                </div>

                {/* AI Reasoning */}
                {action.reasoning && (
                  <div className="bg-white p-2 mb-2 text-xs rounded border border-slate-200">
                    <span className="font-semibold text-slate-600">AI Reasoning: </span>
                    <span className="text-slate-700">{action.reasoning}</span>
                  </div>
                )}

                {/* Source text excerpt */}
                {action.source_text && (
                  <div className="bg-white p-2 mb-2 text-xs border-l-2 border-blue-500 rounded">
                    <span className="font-semibold text-slate-600">Source: </span>
                    <span className="text-slate-700 italic">
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
                    className="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {processing === action.id ? 'Processing...' : 'Approve'}
                  </button>
                  <button
                    onClick={() => handleReject(action.id)}
                    disabled={processing === action.id}
                    className="px-3 py-1.5 bg-slate-200 text-slate-700 text-xs font-medium rounded hover:bg-slate-300 disabled:opacity-50 transition-colors"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600">
        AI proposals require human approval before affecting the docket.
        The AI is the researcher; you are the signer.
      </div>
    </div>
  );
}

export default PendingApprovalsIndicator;
