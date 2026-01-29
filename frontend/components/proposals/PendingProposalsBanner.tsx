'use client';

/**
 * PendingProposalsBanner - Alert banner for pending rule proposals
 *
 * Phase 3 of intelligent document recognition - "Glass Box" transparency
 *
 * Shows when there are AI-discovered rules awaiting attorney review
 */

import React from 'react';
import { Lightbulb, ChevronRight, X, AlertCircle } from 'lucide-react';
import type { RuleProposal } from '@/types';

interface PendingProposalsBannerProps {
  proposals: RuleProposal[];
  onViewAll?: () => void;
  onViewProposal?: (proposal: RuleProposal) => void;
  onDismiss?: () => void;
  compact?: boolean;
}

export default function PendingProposalsBanner({
  proposals,
  onViewAll,
  onViewProposal,
  onDismiss,
  compact = false,
}: PendingProposalsBannerProps) {
  if (proposals.length === 0) return null;

  const hasConflicts = proposals.some(p => p.conflicts && p.conflicts.length > 0);

  if (compact) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 border-l-4 border-amber-400 rounded-r">
        <Lightbulb className="w-4 h-4 text-amber-600" />
        <span className="text-sm text-amber-800">
          <span className="font-semibold">{proposals.length}</span> AI-discovered rule
          {proposals.length > 1 ? 's' : ''} pending review
        </span>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="ml-auto text-xs text-amber-700 hover:text-amber-900 font-medium flex items-center gap-1"
          >
            Review
            <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-100 rounded-lg">
            <Lightbulb className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h4 className="font-semibold text-amber-800 flex items-center gap-2">
              AI Rule Discovery
              {hasConflicts && (
                <span className="flex items-center gap-1 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                  <AlertCircle className="w-3 h-3" />
                  Conflicts
                </span>
              )}
            </h4>
            <p className="text-sm text-amber-700">
              {proposals.length} new rule{proposals.length > 1 ? 's' : ''} discovered from your
              documents
            </p>
          </div>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 text-amber-500 hover:text-amber-700 hover:bg-amber-100 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Proposal List Preview */}
      <div className="space-y-2 mb-3">
        {proposals.slice(0, 3).map((proposal) => (
          <button
            key={proposal.id}
            onClick={() => onViewProposal?.(proposal)}
            className="w-full text-left flex items-center gap-3 p-2 bg-white/50 hover:bg-white rounded-lg transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">
                {proposal.proposed_trigger}
              </p>
              <p className="text-xs text-slate-500">
                {proposal.proposed_days} days | {proposal.proposed_priority}
                {proposal.citation && ` | ${proposal.citation}`}
              </p>
            </div>
            {proposal.conflicts && proposal.conflicts.length > 0 && (
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
            )}
            <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-slate-600 flex-shrink-0" />
          </button>
        ))}
      </div>

      {/* View All Button */}
      {onViewAll && (
        <button
          onClick={onViewAll}
          className="w-full py-2 text-sm font-medium text-amber-700 hover:text-amber-900 bg-amber-100 hover:bg-amber-200 rounded-lg transition-colors flex items-center justify-center gap-1"
        >
          Review All Proposals
          <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

// Header badge component for global pending count
export function ProposalCountBadge({
  count,
  onClick,
}: {
  count: number;
  onClick?: () => void;
}) {
  if (count === 0) return null;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-100 text-amber-700 rounded-full hover:bg-amber-200 transition-colors"
      title={`${count} pending rule proposal${count > 1 ? 's' : ''}`}
    >
      <Lightbulb className="w-4 h-4" />
      <span className="text-sm font-medium">{count}</span>
    </button>
  );
}
