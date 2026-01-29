'use client';

/**
 * TriggerAlertBar - Alert-only status bar
 *
 * Shows trigger status and deadline alerts with urgency-based color coding.
 * Removed Add button - all adding now goes through UnifiedAddEventModal.
 */

import { AlertTriangle, ChevronRight, Clock } from 'lucide-react';
import type { Trigger, Deadline } from '@/hooks/useCaseData';

interface TriggerAlertBarProps {
  triggers: Trigger[];
  deadlines: Deadline[];
  onEditTrigger?: (trigger: Trigger) => void;
}

export default function TriggerAlertBar({
  triggers,
  deadlines,
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

  // If no triggers at all, show setup prompt (no button - use main Add Event)
  if (triggers.length === 0) {
    return (
      <div className="panel-glass border-accent-info px-4 py-3 mb-4">
        <div className="flex items-center gap-3">
          <Clock className="w-5 h-5 text-accent-info" />
          <span className="text-text-primary font-medium">
            No triggers configured. Use &quot;Add Event&quot; to set a trigger and generate calculated deadlines.
          </span>
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

        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-accent-critical" />
          <span className="text-text-primary font-semibold">
            <strong className="text-accent-critical">{overdueDeadlines}</strong> overdue deadline{overdueDeadlines > 1 ? 's' : ''} require immediate attention
          </span>
          <span className="text-text-muted text-sm font-mono">
            ({totalPendingDeadlines} pending from {totalTriggers} trigger{totalTriggers > 1 ? 's' : ''})
          </span>
        </div>
      </div>
    );
  }

  // If pending triggers need attention
  if (pendingTriggers.length > 0) {
    const firstPending = pendingTriggers[0];
    return (
      <div className="panel-glass border-accent-warning glow-warning px-4 py-3 mb-4">
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
      </div>
    );
  }

  // All good - hide alert bar (deadlines are the primary content)
  return null;
}
