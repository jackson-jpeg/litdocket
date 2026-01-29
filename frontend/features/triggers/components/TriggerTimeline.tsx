'use client';

/**
 * TriggerTimeline - Horizontal Trigger Chain Visualization
 *
 * Displays triggers as a horizontal timeline showing:
 * - Trigger events with dates
 * - Deadline counts per trigger
 * - Visual connection between triggers
 * - Quick add trigger action
 *
 * Used in Case Workspace for at-a-glance trigger overview.
 */

import { useMemo } from 'react';
import {
  Calendar,
  Zap,
  Plus,
  AlertTriangle,
  ChevronRight,
  Gavel,
  FileText,
  Scale,
  Clock,
} from 'lucide-react';
import { formatDeadlineDate } from '@/lib/formatters';

// Trigger type from useCaseData
export interface TriggerData {
  id: string;
  title: string;
  trigger_type: string;
  trigger_date: string;
  status?: string;
  deadlines?: Array<{
    id: string;
    status: string;
    priority: string;
    is_overdue?: boolean;
  }>;
  child_deadlines_count?: number;
}

interface TriggerTimelineProps {
  triggers: TriggerData[];
  onTriggerClick?: (trigger: TriggerData) => void;
  onAddTrigger?: () => void;
  compact?: boolean;
  className?: string;
}

// Icon mapping for trigger types
const TRIGGER_ICONS: Record<string, React.ReactNode> = {
  trial_date: <Gavel className="w-4 h-4" />,
  complaint_served: <FileText className="w-4 h-4" />,
  motion_filed: <Scale className="w-4 h-4" />,
  discovery_deadline: <Clock className="w-4 h-4" />,
  default: <Zap className="w-4 h-4" />,
};

// Category colors
const TRIGGER_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  trial: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-700' },
  pleading: { bg: 'bg-blue-50', border: 'border-blue-300', text: 'text-blue-700' },
  discovery: { bg: 'bg-amber-50', border: 'border-amber-300', text: 'text-amber-700' },
  motion: { bg: 'bg-purple-50', border: 'border-purple-300', text: 'text-purple-700' },
  default: { bg: 'bg-slate-50', border: 'border-slate-300', text: 'text-slate-700' },
};

function getTriggerCategory(triggerType: string): string {
  if (triggerType.includes('trial')) return 'trial';
  if (triggerType.includes('complaint') || triggerType.includes('answer')) return 'pleading';
  if (triggerType.includes('discovery')) return 'discovery';
  if (triggerType.includes('motion')) return 'motion';
  return 'default';
}

export default function TriggerTimeline({
  triggers,
  onTriggerClick,
  onAddTrigger,
  compact = false,
  className = '',
}: TriggerTimelineProps) {
  // Sort triggers by date
  const sortedTriggers = useMemo(() => {
    return [...triggers]
      .filter(t => t.status !== 'cancelled')
      .sort((a, b) => new Date(a.trigger_date).getTime() - new Date(b.trigger_date).getTime());
  }, [triggers]);

  // Calculate stats for each trigger
  const triggersWithStats = useMemo(() => {
    return sortedTriggers.map(trigger => {
      const deadlines = trigger.deadlines || [];
      const total = deadlines.length || trigger.child_deadlines_count || 0;
      const pending = deadlines.filter(d => d.status === 'pending').length;
      const overdue = deadlines.filter(d => d.is_overdue).length;
      const critical = deadlines.filter(d =>
        d.priority === 'fatal' || d.priority === 'critical'
      ).length;

      return {
        ...trigger,
        stats: { total, pending, overdue, critical },
      };
    });
  }, [sortedTriggers]);

  if (compact) {
    return (
      <div className={`flex items-center gap-2 overflow-x-auto pb-2 ${className}`}>
        {triggersWithStats.map((trigger, index) => {
          const category = getTriggerCategory(trigger.trigger_type);
          const colors = TRIGGER_COLORS[category] || TRIGGER_COLORS.default;
          const hasOverdue = trigger.stats.overdue > 0;

          return (
            <div key={trigger.id} className="flex items-center gap-2 flex-shrink-0">
              {index > 0 && (
                <ChevronRight className="w-4 h-4 text-slate-300" />
              )}
              <button
                onClick={() => onTriggerClick?.(trigger)}
                className={`
                  flex items-center gap-2 px-3 py-1.5 border rounded-full
                  hover:shadow-sm transition-all
                  ${colors.bg} ${colors.border}
                  ${hasOverdue ? 'ring-2 ring-red-300' : ''}
                `}
              >
                <span className={colors.text}>
                  {TRIGGER_ICONS[trigger.trigger_type] || TRIGGER_ICONS.default}
                </span>
                <span className={`text-sm font-medium ${colors.text}`}>
                  {formatDeadlineDate(trigger.trigger_date)}
                </span>
                <span className="text-xs bg-white/80 px-1.5 py-0.5 rounded-full text-slate-600 font-mono">
                  {trigger.stats.pending}
                </span>
              </button>
            </div>
          );
        })}

        {onAddTrigger && (
          <button
            onClick={onAddTrigger}
            className="flex items-center gap-1 px-3 py-1.5 border-2 border-dashed border-slate-300 rounded-full text-slate-500 hover:border-slate-400 hover:text-slate-600 transition-colors flex-shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span className="text-sm">Add</span>
          </button>
        )}
      </div>
    );
  }

  // Full timeline view
  return (
    <div className={`bg-slate-50 border border-slate-200 ${className}`}>
      {/* Header */}
      <div className="px-4 py-2 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">
            Trigger Timeline
          </span>
        </div>
        {onAddTrigger && (
          <button
            onClick={onAddTrigger}
            className="flex items-center gap-1 text-xs font-bold text-blue-700 hover:text-blue-900 uppercase tracking-wide"
          >
            <Plus className="w-3 h-3" />
            Add Event
          </button>
        )}
      </div>

      {/* Timeline */}
      {sortedTriggers.length === 0 ? (
        <div className="p-6 text-center">
          <Zap className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No trigger events yet</p>
          {onAddTrigger && (
            <button
              onClick={onAddTrigger}
              className="mt-3 px-4 py-2 bg-slate-800 text-white text-sm font-medium hover:bg-slate-700 transition-colors"
            >
              Add First Trigger
            </button>
          )}
        </div>
      ) : (
        <div className="p-4">
          <div className="flex items-start gap-4 overflow-x-auto pb-2">
            {triggersWithStats.map((trigger, index) => {
              const category = getTriggerCategory(trigger.trigger_type);
              const colors = TRIGGER_COLORS[category] || TRIGGER_COLORS.default;
              const hasOverdue = trigger.stats.overdue > 0;
              const hasCritical = trigger.stats.critical > 0;

              return (
                <div key={trigger.id} className="flex items-start gap-4 flex-shrink-0">
                  {/* Connector line */}
                  {index > 0 && (
                    <div className="flex items-center self-center">
                      <div className="w-8 h-0.5 bg-slate-300" />
                      <ChevronRight className="w-4 h-4 text-slate-400 -ml-1" />
                    </div>
                  )}

                  {/* Trigger Card */}
                  <button
                    onClick={() => onTriggerClick?.(trigger)}
                    className={`
                      relative w-48 border text-left transition-all
                      hover:shadow-md
                      ${colors.bg} ${colors.border}
                      ${hasOverdue ? 'ring-2 ring-red-400 ring-offset-1' : ''}
                    `}
                  >
                    {/* Alert badge */}
                    {hasOverdue && (
                      <div className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                        <AlertTriangle className="w-3 h-3 text-white" />
                      </div>
                    )}

                    {/* Header */}
                    <div className={`px-3 py-2 border-b ${colors.border}`}>
                      <div className="flex items-center gap-2">
                        <span className={colors.text}>
                          {TRIGGER_ICONS[trigger.trigger_type] || TRIGGER_ICONS.default}
                        </span>
                        <span className={`font-mono text-xs uppercase ${colors.text}`}>
                          {trigger.trigger_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="px-3 py-2">
                      <p className="font-serif text-sm text-slate-800 truncate">
                        {trigger.title}
                      </p>
                      <div className="flex items-center gap-1 mt-1 text-slate-600">
                        <Calendar className="w-3 h-3" />
                        <span className="font-mono text-xs">
                          {formatDeadlineDate(trigger.trigger_date)}
                        </span>
                      </div>
                    </div>

                    {/* Stats Footer */}
                    <div className={`px-3 py-2 border-t ${colors.border} flex items-center gap-3`}>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-slate-500">Pending:</span>
                        <span className={`text-xs font-bold ${trigger.stats.pending > 0 ? 'text-slate-800' : 'text-slate-400'}`}>
                          {trigger.stats.pending}
                        </span>
                      </div>
                      {trigger.stats.overdue > 0 && (
                        <div className="flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3 text-red-500" />
                          <span className="text-xs font-bold text-red-600">
                            {trigger.stats.overdue}
                          </span>
                        </div>
                      )}
                      {hasCritical && !hasOverdue && (
                        <div className="w-2 h-2 bg-red-500 rounded-full" title="Has critical deadlines" />
                      )}
                    </div>
                  </button>
                </div>
              );
            })}

            {/* Add Trigger Card */}
            {onAddTrigger && (
              <button
                onClick={onAddTrigger}
                className="w-48 h-full min-h-[120px] border-2 border-dashed border-slate-300 bg-white flex flex-col items-center justify-center gap-2 text-slate-400 hover:border-slate-400 hover:text-slate-500 transition-colors flex-shrink-0"
              >
                <Plus className="w-6 h-6" />
                <span className="text-sm font-medium">Add Trigger</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
