'use client';

/**
 * DeadlineChainView - Dependency Tree Visualization
 *
 * Shows the trigger → deadline chain as a tree structure:
 *
 * Trigger: Trial Date (Mar 15, 2025)
 *          │
 *          ├──[-90d]── Discovery Cutoff (Dec 15) ✓
 *          │              └──[-30d]── Last Interrogatories ✓
 *          │
 *          ├──[-60d]── Expert Reports Due (Jan 14)
 *          │              └──[-30d]── Rebuttal Reports (Feb 13)
 *          │
 *          ├──[-30d]── Final Witness List (Feb 13)
 *          └──[-7d]── Pretrial Conference (Mar 8)
 */

import { useState, useMemo } from 'react';
import {
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  Circle,
  AlertTriangle,
  Clock,
  Zap,
  X,
  Calendar,
} from 'lucide-react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';

interface DeadlineChainViewProps {
  trigger: Trigger;
  deadlines: Deadline[];
  onSelectDeadline?: (deadline: Deadline) => void;
  onClose?: () => void;
}

interface ChainNode {
  id: string;
  title: string;
  deadline_date: string | null | undefined;
  priority: string;
  status: string;
  days_from_trigger: number;
  applicable_rule?: string;
  isOverdue: boolean | null;
  isCompleted: boolean;
  depth: number;
}

const PRIORITY_COLORS: Record<string, string> = {
  fatal: 'border-red-600 bg-red-50',
  critical: 'border-red-500 bg-red-50',
  high: 'border-orange-500 bg-orange-50',
  important: 'border-amber-500 bg-amber-50',
  medium: 'border-yellow-500 bg-yellow-50',
  standard: 'border-blue-500 bg-blue-50',
  low: 'border-slate-400 bg-slate-50',
  informational: 'border-gray-400 bg-gray-50',
};

export default function DeadlineChainView({
  trigger,
  deadlines,
  onSelectDeadline,
  onClose,
}: DeadlineChainViewProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(['all']));

  // Build chain nodes from deadlines
  const chainNodes = useMemo((): ChainNode[] => {
    const triggerDate = trigger.trigger_date ? new Date(trigger.trigger_date) : null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Filter deadlines that belong to this trigger
    const triggerDeadlines = deadlines.filter(
      d => d.trigger_event === trigger.trigger_type
    );

    // Calculate days from trigger and sort
    return triggerDeadlines
      .map(d => {
        const deadlineDate = d.deadline_date ? new Date(d.deadline_date) : null;
        let daysFromTrigger = 0;

        if (triggerDate && deadlineDate) {
          daysFromTrigger = Math.round(
            (deadlineDate.getTime() - triggerDate.getTime()) / (1000 * 60 * 60 * 24)
          );
        }

        const isCompleted = d.status === 'completed';
        const isOverdue = !isCompleted && deadlineDate && deadlineDate < today;

        return {
          id: d.id,
          title: d.title,
          deadline_date: d.deadline_date,
          priority: d.priority || 'standard',
          status: d.status,
          days_from_trigger: daysFromTrigger,
          applicable_rule: d.applicable_rule,
          isOverdue,
          isCompleted,
          depth: 1,
        };
      })
      .sort((a, b) => a.days_from_trigger - b.days_from_trigger);
  }, [trigger, deadlines]);

  // Group by time periods
  const groupedNodes = useMemo(() => {
    const groups: Record<string, ChainNode[]> = {
      before: [],  // Negative days (before trigger)
      week_0: [],  // Day 0-7
      week_1: [],  // Day 8-14
      week_2: [],  // Day 15-21
      month_1: [], // Day 22-30
      month_2: [], // Day 31-60
      month_3: [], // Day 61-90
      later: [],   // Day 91+
    };

    chainNodes.forEach(node => {
      const days = node.days_from_trigger;
      if (days < 0) groups.before.push(node);
      else if (days <= 7) groups.week_0.push(node);
      else if (days <= 14) groups.week_1.push(node);
      else if (days <= 21) groups.week_2.push(node);
      else if (days <= 30) groups.month_1.push(node);
      else if (days <= 60) groups.month_2.push(node);
      else if (days <= 90) groups.month_3.push(node);
      else groups.later.push(node);
    });

    return groups;
  }, [chainNodes]);

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'TBD';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDays = (days: number) => {
    if (days === 0) return '±0d';
    if (days > 0) return `+${days}d`;
    return `${days}d`;
  };

  const toggleGroup = (groupId: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  // Stats
  const totalCount = chainNodes.length;
  const completedCount = chainNodes.filter(n => n.isCompleted).length;
  const overdueCount = chainNodes.filter(n => n.isOverdue).length;

  const GROUP_LABELS: Record<string, string> = {
    before: 'Before Trigger',
    week_0: 'Week 1 (Days 0-7)',
    week_1: 'Week 2 (Days 8-14)',
    week_2: 'Week 3 (Days 15-21)',
    month_1: 'Month 1 (Days 22-30)',
    month_2: 'Month 2 (Days 31-60)',
    month_3: 'Month 3 (Days 61-90)',
    later: 'Later (90+ Days)',
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-gradient-to-r from-purple-50 to-indigo-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Zap className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-800">
                  Dependency Chain
                </h2>
                <p className="text-sm text-slate-600">
                  {trigger.title} • {formatDate(trigger.trigger_date)}
                </p>
              </div>
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg hover:bg-slate-200 transition-colors"
              >
                <X className="w-5 h-5 text-slate-500" />
              </button>
            )}
          </div>

          {/* Stats Bar */}
          <div className="flex items-center gap-4 mt-4 text-sm">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-slate-300" />
              <span className="text-slate-600">{totalCount} total</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-slate-600">{completedCount} complete</span>
            </div>
            {overdueCount > 0 && (
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <span className="text-red-600 font-medium">{overdueCount} overdue</span>
              </div>
            )}
          </div>
        </div>

        {/* Chain Visualization */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Trigger Node (Root) */}
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-purple-600 rounded-lg text-white">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <div className="font-medium text-slate-900">{trigger.title}</div>
              <div className="text-sm text-slate-500 font-mono">
                {formatDate(trigger.trigger_date)} • TRIGGER EVENT
              </div>
            </div>
          </div>

          {/* Tree Lines */}
          <div className="ml-5 border-l-2 border-purple-300 pl-6 space-y-4">
            {Object.entries(groupedNodes).map(([groupId, nodes]) => {
              if (nodes.length === 0) return null;

              const isExpanded = expandedNodes.has(groupId) || expandedNodes.has('all');
              const groupHasOverdue = nodes.some(n => n.isOverdue);

              return (
                <div key={groupId}>
                  {/* Group Header */}
                  <button
                    onClick={() => toggleGroup(groupId)}
                    className={`flex items-center gap-2 w-full text-left py-1.5 px-2 rounded-lg transition-colors ${
                      groupHasOverdue
                        ? 'bg-red-50 hover:bg-red-100 text-red-800'
                        : 'bg-slate-50 hover:bg-slate-100 text-slate-700'
                    }`}
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                    <span className="font-medium text-sm">{GROUP_LABELS[groupId]}</span>
                    <span className="text-xs text-slate-500">({nodes.length})</span>
                    {groupHasOverdue && (
                      <AlertTriangle className="w-4 h-4 text-red-500 ml-auto" />
                    )}
                  </button>

                  {/* Group Items */}
                  {isExpanded && (
                    <div className="mt-2 ml-6 space-y-2">
                      {nodes.map((node, index) => (
                        <div
                          key={node.id}
                          className="relative"
                        >
                          {/* Connector Line */}
                          <div className="absolute -left-6 top-3 w-6 h-px bg-slate-300" />

                          {/* Node */}
                          <button
                            onClick={() => {
                              const deadline = deadlines.find(d => d.id === node.id);
                              if (deadline && onSelectDeadline) {
                                onSelectDeadline(deadline);
                              }
                            }}
                            className={`w-full text-left p-3 rounded-lg border-l-4 transition-colors ${
                              PRIORITY_COLORS[node.priority] || PRIORITY_COLORS.standard
                            } ${
                              node.isCompleted ? 'opacity-60' : ''
                            } hover:shadow-sm`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              {/* Status Icon */}
                              <div className="flex-shrink-0 mt-0.5">
                                {node.isCompleted ? (
                                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                                ) : node.isOverdue ? (
                                  <AlertTriangle className="w-5 h-5 text-red-500" />
                                ) : (
                                  <Circle className="w-5 h-5 text-slate-300" />
                                )}
                              </div>

                              {/* Content */}
                              <div className="flex-1 min-w-0">
                                <div className={`font-medium text-sm ${
                                  node.isCompleted ? 'line-through text-slate-500' : 'text-slate-900'
                                }`}>
                                  {node.title}
                                </div>
                                <div className="flex items-center gap-2 mt-1 text-xs">
                                  <span className="font-mono text-purple-600">
                                    {formatDays(node.days_from_trigger)}
                                  </span>
                                  {node.applicable_rule && (
                                    <>
                                      <span className="text-slate-300">•</span>
                                      <span className="text-slate-500 truncate">
                                        {node.applicable_rule.split(' ')[0]}
                                      </span>
                                    </>
                                  )}
                                </div>
                              </div>

                              {/* Date */}
                              <div className={`text-sm font-mono flex-shrink-0 ${
                                node.isOverdue ? 'text-red-600 font-medium' :
                                node.isCompleted ? 'text-slate-400' : 'text-slate-600'
                              }`}>
                                {formatDate(node.deadline_date)}
                              </div>
                            </div>
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-500">
              Progress: {completedCount} of {totalCount} complete
              ({Math.round((completedCount / totalCount) * 100) || 0}%)
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setExpandedNodes(new Set(['all']))}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Expand All
              </button>
              <span className="text-slate-300">|</span>
              <button
                onClick={() => setExpandedNodes(new Set())}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Collapse All
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
