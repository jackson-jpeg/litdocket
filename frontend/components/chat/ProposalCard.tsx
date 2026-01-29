/**
 * ProposalCard - Interactive approval UI for destructive AI tool calls
 *
 * Displays tool information and provides approve/reject/modify options.
 * Shows impact preview for cascade operations and bulk updates.
 *
 * Design: Paper & Steel - Professional light mode, hard edges, editorial typography
 */

import React, { useState } from 'react';
import { AlertTriangle, Check, X } from 'lucide-react';

interface ToolCallProposal {
  tool_id: string;
  tool_name: string;
  input: Record<string, unknown>;
  requires_approval: boolean;
  rationale?: string;
}

interface ProposalCardProps {
  toolCall: ToolCallProposal;
  approvalId: string;
  onApprove: (modifications?: Record<string, unknown>) => void;
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
  const [modifications, setModifications] = useState<Record<string, unknown>>({});
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

  // Type guard for preview data
  const preview = toolCall.input.preview as { affected_count?: number; changes?: Array<{ title: string; old_date: string; new_date: string }> } | undefined;

  return (
    <div className="bg-[#F5F2EB] border-2 border-[#C0392B] p-4 my-3">
      {/* Header - Paper & Steel */}
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-[#1A1A1A]">
        <AlertTriangle className="w-6 h-6 text-[#C0392B]" />
        <div className="flex-1">
          <h3 className="font-bold text-[#C0392B] text-sm uppercase tracking-wide">
            APPROVAL REQUIRED
          </h3>
          <p className="text-[#4A4A4A] text-sm font-mono mt-1">
            {icon} {formatToolName(toolCall.tool_name)}
          </p>
        </div>
      </div>

      {/* Warning - Paper & Steel */}
      {warning && (
        <div className="bg-[#FDFBF7] border-l-4 border-[#C0392B] p-3 mb-4">
          <p className="text-[#C0392B] text-sm font-medium flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {warning}
          </p>
        </div>
      )}

      {/* Rationale */}
      {toolCall.rationale && (
        <div className="mb-4 text-[#4A4A4A] text-sm italic border-l-2 border-[#888888] pl-3">
          "{toolCall.rationale}"
        </div>
      )}

      {/* Tool Parameters - Paper & Steel */}
      <div className="mb-4">
        <p className="text-[#1A1A1A] text-xs font-bold uppercase tracking-wide mb-2">
          Parameters
        </p>
        <pre className="bg-[#FDFBF7] border border-[#1A1A1A] p-3 text-xs overflow-auto max-h-48 text-[#1A1A1A] font-mono">
          {JSON.stringify(toolCall.input, null, 2)}
        </pre>
      </div>

      {/* Cascade Preview (if applicable) */}
      {toolCall.tool_name === 'apply_cascade_update' && preview && (
        <div className="mb-4">
          <p className="text-[#1A1A1A] text-xs font-bold uppercase tracking-wide mb-2">
            Affected Deadlines ({preview.affected_count || 0})
          </p>
          <div className="bg-[#FDFBF7] border border-[#1A1A1A] p-3 max-h-32 overflow-auto">
            <ul className="text-xs space-y-1 text-[#4A4A4A] font-mono">
              {preview.changes?.map((change, i: number) => (
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
        <div className="mb-4 bg-[#FDFBF7] border border-[#1A1A1A] p-3">
          <p className="text-[#1A1A1A] text-xs font-bold uppercase tracking-wide mb-2">
            Modify Parameters
          </p>
          <textarea
            className="w-full bg-white border border-[#1A1A1A] text-[#1A1A1A] p-2 text-sm font-mono focus:outline-none focus:border-[#2C3E50]"
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

      {/* Rejection Reason Input - Paper & Steel */}
      {showRejectInput && (
        <div className="mb-4">
          <input
            type="text"
            className="w-full bg-white border border-[#1A1A1A] text-[#1A1A1A] p-2 text-sm focus:outline-none focus:border-[#C0392B]"
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

      {/* Action Buttons - Paper & Steel (hard edges, no rounded) */}
      <div className="flex gap-2">
        <button
          onClick={handleApprove}
          className="flex-1 bg-[#2C3E50] hover:bg-[#1A1A1A] text-white font-semibold py-3 px-4 transition-colors flex items-center justify-center gap-2 uppercase tracking-wide text-sm"
        >
          <Check className="w-5 h-5" />
          Approve
        </button>

        <button
          onClick={() => {
            if (showRejectInput) {
              handleReject();
            } else {
              setShowRejectInput(true);
            }
          }}
          className="flex-1 bg-[#C0392B] hover:opacity-90 text-white font-semibold py-3 px-4 transition-opacity flex items-center justify-center gap-2 uppercase tracking-wide text-sm"
        >
          <X className="w-5 h-5" />
          {showRejectInput ? 'Confirm' : 'Reject'}
        </button>
      </div>

      {/* Additional Info */}
      <div className="mt-3 text-xs text-[#888888] text-center font-mono">
        Approval expires in 60 seconds if no action is taken
      </div>
    </div>
  );
}

// Simplified streaming indicator component - Paper & Steel styling
export function StreamingIndicator({ status }: { status: string }) {
  const statusMessages: Record<string, { icon: string; text: string; color: string }> = {
    loading_context: { icon: '📚', text: 'Loading case context...', color: 'text-[#2C3E50]' },
    building_context: { icon: '🔍', text: 'Analyzing case...', color: 'text-[#2C3E50]' },
    thinking: { icon: '🤔', text: 'AI is thinking...', color: 'text-[#1A1A1A]' },
    executing_tool: { icon: '⚙️', text: 'Executing action...', color: 'text-[#2C3E50]' },
  };

  const statusInfo = statusMessages[status] || {
    icon: '⏳',
    text: status || 'Processing...',
    color: 'text-[#888888]'
  };

  return (
    <div className={`flex items-center gap-2 ${statusInfo.color} text-sm font-mono`}>
      <span>{statusInfo.icon}</span>
      <span>{statusInfo.text}</span>
    </div>
  );
}
