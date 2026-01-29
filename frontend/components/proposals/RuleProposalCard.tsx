'use client';

/**
 * RuleProposalCard - Displays AI-discovered rule proposals for attorney review
 *
 * Phase 3 of intelligent document recognition - "Glass Box" transparency
 *
 * Features:
 * - Shows AI reasoning and source citations
 * - Confidence indicator
 * - Conflict warnings
 * - Accept/Edit/Reject actions
 */

import React, { useState } from 'react';
import {
  AlertTriangle,
  Check,
  X,
  Edit3,
  BookOpen,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Clock,
  Shield,
  Lightbulb,
  Scale,
} from 'lucide-react';
import type { RuleProposal, RuleProposalConflict } from '@/types';

interface RuleProposalCardProps {
  proposal: RuleProposal;
  onApprove: (proposalId: string, notes?: string) => void;
  onReject: (proposalId: string, reason?: string) => void;
  onEdit: (proposal: RuleProposal) => void;
  onViewSource?: (proposal: RuleProposal) => void;
  isProcessing?: boolean;
}

// Priority colors for visual hierarchy
const priorityConfig: Record<string, { bg: string; text: string; badge: string }> = {
  fatal: { bg: 'bg-red-50', text: 'text-red-700', badge: 'bg-red-600' },
  critical: { bg: 'bg-orange-50', text: 'text-orange-700', badge: 'bg-orange-600' },
  important: { bg: 'bg-amber-50', text: 'text-amber-700', badge: 'bg-amber-600' },
  standard: { bg: 'bg-blue-50', text: 'text-blue-700', badge: 'bg-blue-600' },
  informational: { bg: 'bg-slate-50', text: 'text-slate-700', badge: 'bg-slate-500' },
};

// Confidence level indicator
function ConfidenceIndicator({ score }: { score?: number }) {
  if (!score) return null;

  const percentage = Math.round(score * 100);
  let color = 'bg-red-500';
  let label = 'Low';

  if (percentage >= 80) {
    color = 'bg-green-500';
    label = 'High';
  } else if (percentage >= 60) {
    color = 'bg-yellow-500';
    label = 'Medium';
  }

  return (
    <div className="flex items-center gap-2" title={`AI Confidence: ${percentage}%`}>
      <div className="w-16 h-2 bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs text-slate-500">{label} ({percentage}%)</span>
    </div>
  );
}

// Conflict warning component
function ConflictWarning({ conflict }: { conflict: RuleProposalConflict }) {
  const isError = conflict.severity === 'error';

  return (
    <div
      className={`flex items-start gap-2 p-2 rounded text-sm ${
        isError ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
      }`}
    >
      <AlertTriangle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isError ? 'text-red-500' : 'text-amber-500'}`} />
      <div>
        <span className="font-medium">{conflict.type.replace(/_/g, ' ')}: </span>
        {conflict.message}
        {conflict.existing_days && conflict.proposed_days && (
          <span className="block text-xs mt-1">
            Existing: {conflict.existing_days} days | Proposed: {conflict.proposed_days} days
          </span>
        )}
      </div>
    </div>
  );
}

export default function RuleProposalCard({
  proposal,
  onApprove,
  onReject,
  onEdit,
  onViewSource,
  isProcessing = false,
}: RuleProposalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  const priorityStyle = priorityConfig[proposal.proposed_priority] || priorityConfig.standard;
  const hasConflicts = proposal.conflicts && proposal.conflicts.length > 0;
  const hasWarnings = proposal.warnings && proposal.warnings.length > 0;

  const handleApprove = () => {
    onApprove(proposal.id);
  };

  const handleReject = () => {
    if (showRejectInput) {
      onReject(proposal.id, rejectionReason);
      setShowRejectInput(false);
      setRejectionReason('');
    } else {
      setShowRejectInput(true);
    }
  };

  return (
    <div
      className={`border-2 border-amber-400 rounded-xl overflow-hidden shadow-sm transition-all ${
        isProcessing ? 'opacity-50 pointer-events-none' : ''
      }`}
    >
      {/* Header - Always Visible */}
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1">
            <div className="p-2 bg-amber-100 rounded-lg">
              <Lightbulb className="w-5 h-5 text-amber-600" />
            </div>

            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-amber-600 uppercase tracking-wide">
                  AI Rule Discovery
                </span>
                {hasConflicts && (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                    Conflicts
                  </span>
                )}
              </div>

              <h4 className="font-semibold text-slate-800 text-base">
                {proposal.proposed_trigger}
              </h4>

              <div className="flex items-center gap-3 mt-2 text-sm">
                <span className={`px-2 py-0.5 rounded text-xs font-medium text-white ${priorityStyle.badge}`}>
                  {proposal.proposed_priority.toUpperCase()}
                </span>
                <span className="flex items-center gap-1 text-slate-600">
                  <Clock className="w-3.5 h-3.5" />
                  {proposal.proposed_days} days
                </span>
                {proposal.proposed_calculation_method && (
                  <span className="text-slate-500 text-xs">
                    ({proposal.proposed_calculation_method.replace(/_/g, ' ')})
                  </span>
                )}
              </div>
            </div>
          </div>

          <ConfidenceIndicator score={proposal.confidence_score} />
        </div>

        {/* Citation - Quick Preview */}
        {proposal.citation && (
          <div className="mt-3 flex items-center gap-2 text-sm">
            <Scale className="w-4 h-4 text-slate-500" />
            <span className="text-slate-700 font-medium">{proposal.citation}</span>
            {proposal.citation_url && (
              <a
                href={proposal.citation_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        )}
      </div>

      {/* Expandable Details */}
      <div className="border-t border-amber-200">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full px-4 py-2 flex items-center justify-between text-sm text-slate-600 hover:bg-slate-50 transition-colors"
        >
          <span className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            View AI Reasoning & Sources
          </span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {expanded && (
          <div className="px-4 pb-4 space-y-4 bg-white">
            {/* AI Reasoning */}
            {proposal.reasoning && (
              <div>
                <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">AI Reasoning</h5>
                <p className="text-sm text-slate-700 bg-slate-50 p-3 rounded-lg italic">
                  "{proposal.reasoning}"
                </p>
              </div>
            )}

            {/* Source Text */}
            {proposal.source_text && (
              <div>
                <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">Source Text</h5>
                <blockquote className="text-sm text-slate-700 bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
                  {proposal.source_text}
                </blockquote>
              </div>
            )}

            {/* Conflicts */}
            {hasConflicts && (
              <div>
                <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">Detected Conflicts</h5>
                <div className="space-y-2">
                  {proposal.conflicts!.map((conflict, idx) => (
                    <ConflictWarning key={idx} conflict={conflict} />
                  ))}
                </div>
              </div>
            )}

            {/* Warnings */}
            {hasWarnings && (
              <div>
                <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">Warnings</h5>
                <ul className="space-y-1">
                  {proposal.warnings!.map((warning, idx) => (
                    <li key={idx} className="text-sm text-amber-700 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* View Full Source Button */}
            {onViewSource && (
              <button
                onClick={() => onViewSource(proposal)}
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                <ExternalLink className="w-4 h-4" />
                View Full Research Context
              </button>
            )}
          </div>
        )}
      </div>

      {/* Rejection Reason Input */}
      {showRejectInput && (
        <div className="px-4 pb-4 bg-white border-t border-slate-100">
          <input
            type="text"
            placeholder="Reason for rejection (optional)..."
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleReject();
              if (e.key === 'Escape') {
                setShowRejectInput(false);
                setRejectionReason('');
              }
            }}
            autoFocus
          />
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-stretch border-t border-amber-200">
        <button
          onClick={handleApprove}
          disabled={isProcessing}
          className="flex-1 flex items-center justify-center gap-2 py-3 bg-green-50 text-green-700 hover:bg-green-100 font-medium text-sm transition-colors border-r border-amber-200 disabled:opacity-50"
        >
          <Check className="w-4 h-4" />
          Accept & Save
        </button>

        <button
          onClick={() => onEdit(proposal)}
          disabled={isProcessing}
          className="flex-1 flex items-center justify-center gap-2 py-3 bg-blue-50 text-blue-700 hover:bg-blue-100 font-medium text-sm transition-colors border-r border-amber-200 disabled:opacity-50"
        >
          <Edit3 className="w-4 h-4" />
          Edit
        </button>

        <button
          onClick={handleReject}
          disabled={isProcessing}
          className="flex-1 flex items-center justify-center gap-2 py-3 bg-red-50 text-red-700 hover:bg-red-100 font-medium text-sm transition-colors disabled:opacity-50"
        >
          <X className="w-4 h-4" />
          {showRejectInput ? 'Confirm Reject' : 'Reject'}
        </button>
      </div>
    </div>
  );
}

// Compact version for lists
export function RuleProposalCardCompact({
  proposal,
  onApprove,
  onReject,
  onEdit,
  isProcessing = false,
}: Omit<RuleProposalCardProps, 'onViewSource'>) {
  const priorityStyle = priorityConfig[proposal.proposed_priority] || priorityConfig.standard;
  const hasConflicts = proposal.conflicts && proposal.conflicts.length > 0;

  return (
    <div
      className={`flex items-center gap-4 p-3 border-l-4 border-amber-400 bg-amber-50 rounded-r-lg ${
        isProcessing ? 'opacity-50 pointer-events-none' : ''
      }`}
    >
      <Lightbulb className="w-5 h-5 text-amber-600 flex-shrink-0" />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs text-amber-600 font-semibold">NEW RULE</span>
          {hasConflicts && (
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          )}
        </div>
        <p className="text-sm font-medium text-slate-800 truncate">
          {proposal.proposed_trigger}
        </p>
        <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
          <span className={`px-1.5 py-0.5 rounded text-white ${priorityStyle.badge}`}>
            {proposal.proposed_priority}
          </span>
          <span>{proposal.proposed_days} days</span>
          {proposal.citation && <span>| {proposal.citation}</span>}
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onApprove(proposal.id)}
          disabled={isProcessing}
          className="p-2 text-green-600 hover:bg-green-100 rounded-lg transition-colors"
          title="Approve"
        >
          <Check className="w-4 h-4" />
        </button>
        <button
          onClick={() => onEdit(proposal)}
          disabled={isProcessing}
          className="p-2 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors"
          title="Edit"
        >
          <Edit3 className="w-4 h-4" />
        </button>
        <button
          onClick={() => onReject(proposal.id)}
          disabled={isProcessing}
          className="p-2 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
          title="Reject"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
