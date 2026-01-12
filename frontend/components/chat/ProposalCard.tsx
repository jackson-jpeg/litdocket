/**
 * ProposalCard - Interactive approval UI for destructive AI tool calls
 *
 * Displays tool information and provides approve/reject/modify options.
 * Shows impact preview for cascade operations and bulk updates.
 */

import React, { useState } from 'react';
import { AlertTriangle, Check, X, Edit } from 'lucide-react';

interface ToolCallProposal {
  tool_id: string;
  tool_name: string;
  input: Record<string, any>;
  requires_approval: boolean;
  rationale?: string;
}

interface ProposalCardProps {
  toolCall: ToolCallProposal;
  approvalId: string;
  onApprove: (modifications?: Record<string, any>) => void;
  onReject: (reason: string) => void;
}

function formatToolName(toolName: string): string {
  return toolName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getToolIcon(toolName: string): string {
  if (toolName.includes('delete')) return '🗑️';
  if (toolName.includes('update')) return '✏️';
  if (toolName.includes('bulk')) return '📦';
  if (toolName.includes('cascade')) return '🔄';
  if (toolName.includes('close')) return '🔒';
  return '⚙️';
}

function getToolWarning(toolName: string): string | null {
  if (toolName === 'delete_deadline') {
    return '⚠️ This will permanently delete the deadline.';
  }
  if (toolName === 'bulk_update_deadlines') {
    return '⚠️ This will update multiple deadlines at once.';
  }
  if (toolName === 'delete_document') {
    return '⚠️ This will permanently delete the document.';
  }
  if (toolName === 'close_case') {
    return '⚠️ This will archive the case and all its deadlines.';
  }
  if (toolName === 'apply_cascade_update') {
    return '⚠️ This will recalculate and update dependent deadlines.';
  }
  return null;
}

export function ProposalCard({
  toolCall,
  approvalId,
  onApprove,
  onReject
}: ProposalCardProps) {
  const [isModifying, setIsModifying] = useState(false);
  const [modifications, setModifications] = useState<Record<string, any>>({});
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  const handleApprove = () => {
    if (Object.keys(modifications).length > 0) {
      onApprove(modifications);
    } else {
      onApprove();
    }
  };

  const handleReject = () => {
    onReject(rejectionReason || 'User rejected');
  };

  const warning = getToolWarning(toolCall.tool_name);
  const icon = getToolIcon(toolCall.tool_name);

  return (
    <div className="proposal-card bg-amber-900/20 border-2 border-amber-500 rounded-lg p-4 my-3 animate-pulse-subtle">
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <AlertTriangle className="w-6 h-6 text-amber-500 animate-pulse" />
        <div className="flex-1">
          <h3 className="font-bold text-amber-500 text-lg">
            APPROVAL REQUIRED
          </h3>
          <p className="text-amber-300 text-sm">
            {icon} {formatToolName(toolCall.tool_name)}
          </p>
        </div>
      </div>

      {/* Warning */}
      {warning && (
        <div className="bg-red-900/30 border border-red-500/50 rounded p-3 mb-3 text-red-300 text-sm">
          {warning}
        </div>
      )}

      {/* Rationale */}
      {toolCall.rationale && (
        <div className="mb-3 text-slate-300 text-sm italic">
          "{toolCall.rationale}"
        </div>
      )}

      {/* Tool Parameters */}
      <div className="mb-3">
        <p className="text-white text-sm font-semibold mb-2">Parameters:</p>
        <pre className="bg-slate-800 p-3 rounded text-xs overflow-auto max-h-48 text-slate-300">
          {JSON.stringify(toolCall.input, null, 2)}
        </pre>
      </div>

      {/* Cascade Preview (if applicable) */}
      {toolCall.tool_name === 'apply_cascade_update' && toolCall.input.preview && (
        <div className="mb-3">
          <p className="text-white text-sm font-semibold mb-2">
            Affected Deadlines ({toolCall.input.preview.affected_count || 0}):
          </p>
          <div className="bg-slate-800 p-3 rounded max-h-32 overflow-auto">
            <ul className="text-xs space-y-1 text-slate-300">
              {toolCall.input.preview.changes?.map((change: any, i: number) => (
                <li key={i}>
                  • {change.title}: {change.old_date} → {change.new_date}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Modification Interface (optional feature) */}
      {isModifying && (
        <div className="mb-3 bg-slate-800 p-3 rounded">
          <p className="text-white text-sm font-semibold mb-2">Modify Parameters:</p>
          <textarea
            className="w-full bg-slate-700 text-white p-2 rounded text-sm font-mono"
            rows={4}
            placeholder="Enter JSON modifications..."
            value={JSON.stringify(modifications, null, 2)}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                setModifications(parsed);
              } catch {
                // Invalid JSON, ignore
              }
            }}
          />
        </div>
      )}

      {/* Rejection Reason Input */}
      {showRejectInput && (
        <div className="mb-3">
          <input
            type="text"
            className="w-full bg-slate-700 text-white p-2 rounded text-sm"
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
          className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded transition-colors flex items-center justify-center gap-2"
        >
          <Check className="w-5 h-5" />
          Approve
        </button>

        {/* Optional: Modify button */}
        {/* <button
          onClick={() => setIsModifying(!isModifying)}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded transition-colors flex items-center justify-center gap-2"
        >
          <Edit className="w-5 h-5" />
          {isModifying ? 'Cancel' : 'Modify'}
        </button> */}

        <button
          onClick={() => {
            if (showRejectInput) {
              handleReject();
            } else {
              setShowRejectInput(true);
            }
          }}
          className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-4 rounded transition-colors flex items-center justify-center gap-2"
        >
          <X className="w-5 h-5" />
          {showRejectInput ? 'Confirm Reject' : 'Reject'}
        </button>
      </div>

      {/* Additional Info */}
      <div className="mt-3 text-xs text-slate-400 text-center">
        Approval expires in 60 seconds if no action is taken
      </div>
    </div>
  );
}

// Simplified streaming indicator component
export function StreamingIndicator({ status }: { status: string }) {
  const statusMessages: Record<string, { icon: string; text: string; color: string }> = {
    loading_context: { icon: '📚', text: 'Loading case context...', color: 'text-blue-400' },
    building_context: { icon: '🔍', text: 'Analyzing case...', color: 'text-blue-400' },
    thinking: { icon: '🤔', text: 'AI is thinking...', color: 'text-cyan-400' },
    executing_tool: { icon: '⚙️', text: 'Executing action...', color: 'text-green-400' },
  };

  const statusInfo = statusMessages[status] || {
    icon: '⏳',
    text: status || 'Processing...',
    color: 'text-slate-400'
  };

  return (
    <div className={`flex items-center gap-2 ${statusInfo.color} text-sm animate-pulse`}>
      <span>{statusInfo.icon}</span>
      <span>{statusInfo.text}</span>
    </div>
  );
}
