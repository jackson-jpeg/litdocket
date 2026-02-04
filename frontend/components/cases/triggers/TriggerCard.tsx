'use client';

/**
 * TriggerCard - Responsive Trigger Event Display
 *
 * Desktop (lg+): Single row layout
 * Mobile/Vertical: Stacked card layout for readability
 */

import { useState } from 'react';
import {
  ChevronRight,
  ChevronDown,
  MoreHorizontal,
  Edit2,
  RefreshCw,
  Trash2,
  AlertTriangle,
  Clock,
  Check,
  CornerDownRight,
  Calendar
} from 'lucide-react';
import type { Trigger } from '@/hooks/useCaseData';

interface TriggerCardProps {
  trigger: Trigger;
  onEdit?: (trigger: Trigger) => void;
  onRecalculate?: (triggerId: string) => void;
  onDelete?: (triggerId: string) => void;
  isRecalculating?: boolean;
}

export default function TriggerCard({
  trigger,
  onEdit,
  onRecalculate,
  onDelete,
  isRecalculating
}: TriggerCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  // V2: Use pre-calculated nested data from API (no client-side filtering)
  const childDeadlines = trigger.child_deadlines || [];
  const overdueCount = trigger.status_summary?.overdue || 0;

  // Strict Date Formatting
  const formatDate = (d: string) => new Date(d).toLocaleDateString('en-US', {
    month: '2-digit', day: '2-digit', year: 'numeric'
  });

  const formatDateShort = (d: string) => new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric'
  });

  return (
    <div className={`group ${isExpanded ? 'bg-surface' : 'bg-paper hover:bg-surface'}`}>

      {/* 1. MASTER ROW - Responsive: stacked on mobile, horizontal on desktop */}
      <div className="px-3 py-3 lg:px-4 lg:py-3">
        {/* Desktop Layout (lg+) */}
        <div className="hidden lg:flex items-center gap-4">
          {/* Expand Toggle */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-ink-muted hover:text-ink transition-colors flex-shrink-0"
          >
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>

          {/* Date Badge (Monospace) */}
          <div className="flex flex-col items-center justify-center border border-ink px-2 py-1 bg-paper min-w-[80px] flex-shrink-0">
            <span className="text-[10px] uppercase text-ink-secondary font-mono font-bold tracking-wider">DATE</span>
            <span className="font-mono text-sm font-medium text-ink">
              {formatDate(trigger.trigger_date)}
            </span>
          </div>

          {/* Title & Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="font-serif text-ink font-medium truncate">
                {trigger.title}
              </h4>
              {overdueCount > 0 && (
                <span className="bg-fatal/10 text-fatal text-[10px] font-mono font-bold px-1.5 py-0.5 border border-fatal uppercase tracking-wide flex-shrink-0">
                  {overdueCount} Critical
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 mt-1">
              <span className="text-xs text-ink-secondary font-mono truncate">
                {trigger.trigger_type}
              </span>
              <span className="text-xs text-ink-secondary flex-shrink-0">
                {childDeadlines.length} events
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="relative flex-shrink-0">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 text-ink-muted hover:text-ink hover:bg-surface"
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile/Vertical Layout (< lg) - Stacked Card */}
        <div className="lg:hidden">
          {/* Row 1: Expand + Title */}
          <div className="flex items-start gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-ink-muted hover:text-ink transition-colors flex-shrink-0 mt-1"
            >
              {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>

            <div className="flex-1 min-w-0">
              <h4 className="font-serif text-ink font-medium text-base leading-snug">
                {trigger.title}
              </h4>
              <span className="text-xs text-ink-secondary font-mono">
                {trigger.trigger_type}
              </span>
            </div>

            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 text-ink-muted hover:text-ink hover:bg-surface flex-shrink-0"
            >
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>

          {/* Row 2: Date + Badges */}
          <div className="flex items-center gap-2 mt-2 ml-7 flex-wrap">
            <div className="flex items-center gap-1.5 text-sm text-ink bg-surface border border-ink/20 px-2 py-1">
              <Calendar className="w-3.5 h-3.5" />
              <span className="font-mono font-medium">{formatDate(trigger.trigger_date)}</span>
            </div>

            <span className="text-xs text-ink-secondary bg-surface border border-ink/20 px-2 py-1">
              {childDeadlines.length} events
            </span>

            {overdueCount > 0 && (
              <span className="bg-fatal/10 text-fatal text-xs font-mono font-bold px-2 py-1 border border-fatal flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {overdueCount} overdue
              </span>
            )}
          </div>
        </div>

        {/* Dropdown Menu (shared) */}
        {showMenu && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setShowMenu(false)}
            />
            <div className="absolute right-2 lg:right-4 mt-1 w-48 bg-paper border-2 border-ink shadow-modal z-20 text-sm overflow-hidden">
              <button
                onClick={() => { onEdit?.(trigger); setShowMenu(false); }}
                className="w-full text-left px-4 py-3 hover:bg-surface flex items-center gap-2 text-ink"
              >
                <Edit2 className="w-4 h-4" /> Edit Date
              </button>
              <button
                onClick={() => { onRecalculate?.(trigger.id); setShowMenu(false); }}
                className="w-full text-left px-4 py-3 hover:bg-surface flex items-center gap-2 text-ink"
              >
                <RefreshCw className={`w-4 h-4 ${isRecalculating ? 'animate-spin' : ''}`} />
                Recalculate
              </button>
              <div className="border-t border-ink/20"></div>
              <button
                onClick={() => { onDelete?.(trigger.id); setShowMenu(false); }}
                className="w-full text-left px-4 py-3 hover:bg-fatal/10 text-fatal flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" /> Delete
              </button>
            </div>
          </>
        )}
      </div>

      {/* 2. DETAIL CASCADE - Responsive */}
      {isExpanded && (
        <div className="px-3 pb-4 lg:pl-8 lg:pr-4">
          <div className="border-l-2 border-ink/30 pl-3 lg:pl-4 space-y-1">

            {/* Header for Cascade */}
            <div className="flex items-center gap-2 text-xs text-ink-muted font-mono font-medium uppercase tracking-wider mb-2 pt-2">
              <CornerDownRight className="w-3 h-3" />
              Generated Deadlines
            </div>

            {childDeadlines.length === 0 ? (
              <div className="text-sm text-ink-muted italic py-2">No deadlines generated yet.</div>
            ) : (
              <>
                {/* Desktop Table View (lg+) */}
                <table className="hidden lg:table w-full text-sm border-collapse">
                  <thead>
                    <tr className="text-left text-xs text-ink-secondary font-mono uppercase border-b border-ink/20">
                      <th className="py-1 font-normal w-8"></th>
                      <th className="py-1 font-normal w-24">Due Date</th>
                      <th className="py-1 font-normal">Action</th>
                      <th className="py-1 font-normal w-24 text-right">Rule</th>
                    </tr>
                  </thead>
                  <tbody className="font-mono text-xs">
                    {childDeadlines.map(dl => {
                      const isOverdue = dl.is_overdue;
                      const isDone = dl.status === 'completed';

                      return (
                        <tr key={dl.id} className={`group hover:bg-paper transition-colors ${isDone ? 'opacity-50' : ''}`}>
                          <td className="py-2 align-top">
                            {isOverdue ? (
                              <AlertTriangle className="w-3 h-3 text-fatal" />
                            ) : isDone ? (
                              <Check className="w-3 h-3 text-status-success" />
                            ) : (
                              <div className="w-1.5 h-1.5 bg-ink/30 mt-1"></div>
                            )}
                          </td>
                          <td className={`py-2 align-top font-medium ${isOverdue ? 'text-fatal' : 'text-ink'}`}>
                            {dl.deadline_date ? formatDate(dl.deadline_date) : 'TBD'}
                          </td>
                          <td className="py-2 align-top font-sans text-ink pr-4 min-w-0">
                            <span className="block truncate">{dl.title}</span>
                          </td>
                          <td className="py-2 align-top text-right text-ink-muted truncate max-w-[150px]" title={dl.applicable_rule}>
                            {dl.applicable_rule?.split(' ')[0] || 'RULE'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {/* Mobile Card View (< lg) */}
                <div className="lg:hidden space-y-2">
                  {childDeadlines.map(dl => {
                    const isOverdue = dl.is_overdue;
                    const isDone = dl.status === 'completed';

                    return (
                      <div
                        key={dl.id}
                        className={`p-3 bg-paper border-l-4 ${
                          isOverdue ? 'border-fatal' :
                          isDone ? 'border-status-success opacity-60' :
                          'border-ink/30'
                        }`}
                      >
                        {/* Row 1: Status + Title */}
                        <div className="flex items-start gap-2">
                          <div className="flex-shrink-0 mt-0.5">
                            {isOverdue ? (
                              <AlertTriangle className="w-4 h-4 text-fatal" />
                            ) : isDone ? (
                              <Check className="w-4 h-4 text-status-success" />
                            ) : (
                              <Clock className="w-4 h-4 text-ink-muted" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-medium ${isDone ? 'line-through text-ink-muted' : 'text-ink'}`}>
                              {dl.title}
                            </p>
                          </div>
                        </div>

                        {/* Row 2: Date + Rule */}
                        <div className="flex items-center justify-between mt-2 ml-6">
                          <span className={`text-sm font-mono font-medium ${isOverdue ? 'text-fatal' : 'text-ink-secondary'}`}>
                            {dl.deadline_date ? formatDateShort(dl.deadline_date) : 'TBD'}
                          </span>
                          <span className="text-xs font-mono text-ink-muted truncate max-w-[120px]" title={dl.applicable_rule}>
                            {dl.applicable_rule?.split(' ')[0] || ''}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
