'use client';

/**
 * TriggerAlertBar - Bloomberg Terminal Design
 *
 * System alert bar with neon accents and glow effects.
 * Shows trigger status with urgency-based color coding.
 */

import { AlertTriangle, ChevronRight, Plus, Clock, CheckCircle } from 'lucide-react';
import type { Trigger, Deadline } from '@/features/cases/hooks/useCaseData';

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
  // Find triggers that need attention
  const pendingTriggers = triggers.filter(t => {
    const relatedDeadlines = deadlines.filter(
      d => d.trigger_event === t.trigger_type
    );
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
      <div className="panel-glass border-accent-info px-4 py-3 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-accent-info" />
            <span className="text-text-primary font-medium">
              No triggers configured. Set a trigger event to generate calculated deadlines.
            </span>
          </div>
          {onAddTrigger && (
            <button
              onClick={onAddTrigger}
              className="btn-primary btn-sm"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Trigger
            </button>
          )}
        </div>
      </div>
    );
  }

  // If there are overdue deadlines, show critical alert with glow
  if (overdueDeadlines > 0) {
    return (
      <div className="panel-glass glow-critical border-accent-critical px-4 py-3 mb-4 relative">
        {/* Pulsing LED indicator */}
        <span className="absolute top-3 right-3 w-2 h-2 bg-accent-critical rounded-full animate-pulse-slow"></span>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-accent-critical" />
            <span className="text-text-primary font-semibold">
              <strong className="text-accent-critical">{overdueDeadlines}</strong> overdue deadline{overdueDeadlines > 1 ? 's' : ''} require immediate attention
            </span>
            <span className="text-text-muted text-sm font-mono">
              ({totalPendingDeadlines} pending from {totalTriggers} trigger{totalTriggers > 1 ? 's' : ''})
            </span>
          </div>
          {onAddTrigger && (
            <button
              onClick={onAddTrigger}
              className="btn-ghost btn-sm"
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
      <div className="panel-glass border-accent-warning glow-warning px-4 py-3 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-accent-warning" />
            <span className="text-text-primary font-medium">
              {pendingTriggers.length} trigger{pendingTriggers.length > 1 ? 's' : ''} require{pendingTriggers.length === 1 ? 's' : ''} attention:
            </span>
            <button
              onClick={() => onEditTrigger?.(firstPending)}
              className="flex items-center gap-1 text-accent-warning hover:text-accent-warning/80 font-medium"
            >
              [{firstPending.title}]
              <ChevronRight className="w-4 h-4" />
              [Configure]
            </button>
          </div>
          {onAddTrigger && (
            <button
              onClick={onAddTrigger}
              className="btn-ghost btn-sm"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Trigger
            </button>
          )}
        </div>
      </div>
    );
  }

  // All good - show success status
  return (
    <div className="panel-glass border-accent-success px-4 py-3 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-accent-success" />
          <span className="text-text-primary font-medium">
            {totalTriggers} trigger{totalTriggers > 1 ? 's' : ''} active
          </span>
          <span className="text-text-muted text-sm font-mono">
            ({totalPendingDeadlines} pending deadline{totalPendingDeadlines !== 1 ? 's' : ''})
          </span>
        </div>
        {onAddTrigger && (
          <button
            onClick={onAddTrigger}
            className="btn-ghost btn-sm"
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Trigger
          </button>
        )}
      </div>
    </div>
  );
}
