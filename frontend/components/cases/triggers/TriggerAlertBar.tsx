'use client';

/**
 * TriggerAlertBar - Sovereign Design System
 *
 * A system alert bar showing pending triggers that need attention.
 * Amber banner style, sits above the main data grid.
 *
 * "⚠️ 1 Trigger Event requires attention: [Trial Date Set] -> [Generate Pretrial Schedule]"
 */

import { AlertTriangle, ChevronRight, Plus, Clock } from 'lucide-react';
import type { Trigger, Deadline } from '@/hooks/useCaseData';

interface TriggerAlertBarProps {
  triggers: Trigger[];
  deadlines: Deadline[];
  onAddTrigger?: () => void;
  onEditTrigger?: (trigger: Trigger) => void;
}

export default function TriggerAlertBar({
  triggers,
  deadlines,
  onAddTrigger,
  onEditTrigger,
}: TriggerAlertBarProps) {
  // Find triggers that need attention (no date set, or have pending deadlines)
  const pendingTriggers = triggers.filter(t => {
    // Count deadlines from this trigger
    const relatedDeadlines = deadlines.filter(
      d => d.trigger_event === t.trigger_type
    );
    const pendingCount = relatedDeadlines.filter(
      d => d.status !== 'completed' && d.status !== 'cancelled'
    ).length;
    const overdueCount = relatedDeadlines.filter(d => {
      const isActive = d.status !== 'completed' && d.status !== 'cancelled';
      const isOverdue = d.deadline_date && new Date(d.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));
      return isActive && isOverdue;
    }).length;

    return overdueCount > 0 || !t.trigger_date;
  });

  // Count total stats
  const totalTriggers = triggers.length;
  const totalPendingDeadlines = deadlines.filter(
    d => d.status !== 'completed' && d.status !== 'cancelled'
  ).length;
  const overdueDeadlines = deadlines.filter(d => {
    const isActive = d.status !== 'completed' && d.status !== 'cancelled';
    const isOverdue = d.deadline_date && new Date(d.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));
    return isActive && isOverdue;
  }).length;

  // If no triggers at all, show setup prompt
  if (triggers.length === 0) {
    return (
      <div className="bg-blue-100 border-y-2 border-blue-600 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-blue-700" />
            <span className="text-blue-900 font-medium">
              No triggers configured. Set a trigger event to generate calculated deadlines.
            </span>
          </div>
          {onAddTrigger && (
            <button
              onClick={onAddTrigger}
              className="btn btn-primary btn-raised text-sm"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Trigger
            </button>
          )}
        </div>
      </div>
    );
  }

  // If there are overdue deadlines, show critical alert
  if (overdueDeadlines > 0) {
    return (
      <div className="bg-red-100 border-y-2 border-red-600 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-700" />
            <span className="text-red-900 font-medium">
              <strong>{overdueDeadlines}</strong> overdue deadline{overdueDeadlines > 1 ? 's' : ''} require immediate attention
            </span>
            <span className="text-red-700 text-sm">
              ({totalPendingDeadlines} pending total from {totalTriggers} trigger{totalTriggers > 1 ? 's' : ''})
            </span>
          </div>
          {onAddTrigger && (
            <button
              onClick={onAddTrigger}
              className="btn btn-secondary btn-raised text-sm"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Trigger
            </button>
          )}
        </div>
      </div>
    );
  }

  // If pending triggers need attention
  if (pendingTriggers.length > 0) {
    const firstPending = pendingTriggers[0];
    return (
      <div className="bg-amber-100 border-y-2 border-amber-600 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-700" />
            <span className="text-amber-900 font-medium">
              {pendingTriggers.length} trigger{pendingTriggers.length > 1 ? 's' : ''} require{pendingTriggers.length === 1 ? 's' : ''} attention:
            </span>
            <button
              onClick={() => onEditTrigger?.(firstPending)}
              className="flex items-center gap-1 text-amber-800 hover:text-amber-900 hover:underline font-medium"
            >
              [{firstPending.title}]
              <ChevronRight className="w-4 h-4" />
              [Configure]
            </button>
          </div>
          {onAddTrigger && (
            <button
              onClick={onAddTrigger}
              className="btn btn-secondary btn-raised text-sm"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Trigger
            </button>
          )}
        </div>
      </div>
    );
  }

  // All good - show status bar
  return (
    <div className="bg-green-100 border-y-2 border-green-600 px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-green-700 font-bold">✓</span>
          <span className="text-green-900 font-medium">
            {totalTriggers} trigger{totalTriggers > 1 ? 's' : ''} active
          </span>
          <span className="text-green-700 text-sm">
            ({totalPendingDeadlines} pending deadline{totalPendingDeadlines !== 1 ? 's' : ''})
          </span>
        </div>
        {onAddTrigger && (
          <button
            onClick={onAddTrigger}
            className="btn btn-secondary btn-raised text-sm"
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Trigger
          </button>
        )}
      </div>
    </div>
  );
}
