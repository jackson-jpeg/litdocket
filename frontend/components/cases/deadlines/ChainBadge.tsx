'use client';

/**
 * ChainBadge - Inline chain indicator
 *
 * Shows: ⛓️ 3 of 47 complete │ View chain →
 *
 * Displays trigger chain progress and allows viewing the full chain.
 */

import { Link2, ChevronRight, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';

interface ChainBadgeProps {
  trigger: Trigger;
  deadlines: Deadline[];
  onViewChain?: (e?: React.MouseEvent) => void;
  compact?: boolean;
}

export default function ChainBadge({
  trigger,
  deadlines,
  onViewChain,
  compact = false,
}: ChainBadgeProps) {
  // Count deadlines in this chain
  const chainDeadlines = deadlines.filter(
    d => d.trigger_event === trigger.trigger_type
  );

  const totalCount = chainDeadlines.length;
  const completedCount = chainDeadlines.filter(d => d.status === 'completed').length;
  const overdueCount = chainDeadlines.filter(d => {
    if (d.status === 'completed' || d.status === 'cancelled') return false;
    if (!d.deadline_date) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return new Date(d.deadline_date) < today;
  }).length;

  if (totalCount === 0) return null;

  const progressPercent = Math.round((completedCount / totalCount) * 100);
  const hasOverdue = overdueCount > 0;

  if (compact) {
    return (
      <button
        onClick={(e) => onViewChain?.(e)}
        className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded transition-colors ${
          hasOverdue
            ? 'bg-red-100 text-red-700 hover:bg-red-200'
            : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
        }`}
        title={`${completedCount} of ${totalCount} complete • Click to view chain`}
      >
        <Link2 className="w-3 h-3" />
        <span className="font-mono">{completedCount}/{totalCount}</span>
        {hasOverdue && <AlertTriangle className="w-3 h-3" />}
      </button>
    );
  }

  return (
    <button
      onClick={(e) => onViewChain?.(e)}
      className={`inline-flex items-center gap-2 px-2.5 py-1 text-xs rounded-lg border transition-colors ${
        hasOverdue
          ? 'bg-red-50 border-red-200 text-red-700 hover:bg-red-100'
          : 'bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100'
      }`}
    >
      <Link2 className="w-3.5 h-3.5" />

      <span className="font-medium">
        {trigger.title.length > 20 ? trigger.title.slice(0, 20) + '...' : trigger.title}
      </span>

      <span className="text-slate-400">│</span>

      <span className="flex items-center gap-1">
        {hasOverdue ? (
          <>
            <AlertTriangle className="w-3 h-3 text-red-500" />
            <span className="text-red-600 font-medium">{overdueCount} overdue</span>
          </>
        ) : completedCount === totalCount ? (
          <>
            <CheckCircle2 className="w-3 h-3 text-green-500" />
            <span className="text-green-600 font-medium">Complete</span>
          </>
        ) : (
          <span className="font-mono">{completedCount} of {totalCount}</span>
        )}
      </span>

      <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
    </button>
  );
}


/**
 * ChainProgressBar - Visual progress indicator
 *
 * Shows a thin progress bar with completion percentage
 */
interface ChainProgressBarProps {
  trigger: Trigger;
  deadlines: Deadline[];
  showLabel?: boolean;
}

export function ChainProgressBar({
  trigger,
  deadlines,
  showLabel = true,
}: ChainProgressBarProps) {
  const chainDeadlines = deadlines.filter(
    d => d.trigger_event === trigger.trigger_type
  );

  const totalCount = chainDeadlines.length;
  const completedCount = chainDeadlines.filter(d => d.status === 'completed').length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  if (totalCount === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all ${
            progressPercent === 100
              ? 'bg-green-500'
              : progressPercent >= 50
              ? 'bg-purple-500'
              : 'bg-amber-500'
          }`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-slate-500 font-mono min-w-[40px] text-right">
          {progressPercent}%
        </span>
      )}
    </div>
  );
}
