'use client';

/**
 * DeadlineList - Grouped Deadline List Component
 *
 * Displays deadlines in groups (by date, priority, or case).
 * Supports multiple view modes and filtering.
 *
 * Features:
 * - Group by: date, priority, case, trigger
 * - Expandable sections
 * - Empty state handling
 * - Loading skeleton
 */

import { useState, useMemo } from 'react';
import {
  Calendar,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Inbox,
} from 'lucide-react';
import type { Deadline, CalendarDeadline } from '@/types';
import { DeadlineCard } from './DeadlineCard';

type GroupBy = 'date' | 'priority' | 'case' | 'trigger' | 'none';

interface DeadlineListProps {
  deadlines: (Deadline | CalendarDeadline)[];
  loading?: boolean;
  groupBy?: GroupBy;
  onDeadlineClick?: (deadline: Deadline | CalendarDeadline) => void;
  onComplete?: (id: string) => void;
  showCase?: boolean;
  emptyMessage?: string;
  compact?: boolean;
}

interface GroupedDeadlines {
  key: string;
  label: string;
  deadlines: (Deadline | CalendarDeadline)[];
  isOverdue?: boolean;
  isPriority?: boolean;
}

export default function DeadlineList({
  deadlines,
  loading = false,
  groupBy = 'date',
  onDeadlineClick,
  onComplete,
  showCase = true,
  emptyMessage = 'No deadlines found',
  compact = false,
}: DeadlineListProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (key: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const groupedDeadlines = useMemo((): GroupedDeadlines[] => {
    if (groupBy === 'none' || deadlines.length === 0) {
      return [{
        key: 'all',
        label: 'All Deadlines',
        deadlines,
      }];
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (groupBy === 'date') {
      const overdue: (Deadline | CalendarDeadline)[] = [];
      const todayList: (Deadline | CalendarDeadline)[] = [];
      const thisWeek: (Deadline | CalendarDeadline)[] = [];
      const thisMonth: (Deadline | CalendarDeadline)[] = [];
      const later: (Deadline | CalendarDeadline)[] = [];
      const noDate: (Deadline | CalendarDeadline)[] = [];

      const weekFromNow = new Date(today);
      weekFromNow.setDate(weekFromNow.getDate() + 7);
      const monthFromNow = new Date(today);
      monthFromNow.setMonth(monthFromNow.getMonth() + 1);

      deadlines.forEach(d => {
        if (!d.deadline_date) {
          noDate.push(d);
          return;
        }

        const date = new Date(d.deadline_date);
        date.setHours(0, 0, 0, 0);

        if (d.status !== 'pending') {
          later.push(d); // Completed/cancelled go to later
          return;
        }

        if (date < today) {
          overdue.push(d);
        } else if (date.getTime() === today.getTime()) {
          todayList.push(d);
        } else if (date <= weekFromNow) {
          thisWeek.push(d);
        } else if (date <= monthFromNow) {
          thisMonth.push(d);
        } else {
          later.push(d);
        }
      });

      const groups: GroupedDeadlines[] = [];

      if (overdue.length > 0) {
        groups.push({
          key: 'overdue',
          label: `Overdue (${overdue.length})`,
          deadlines: overdue.sort((a, b) =>
            new Date(a.deadline_date!).getTime() - new Date(b.deadline_date!).getTime()
          ),
          isOverdue: true,
        });
      }

      if (todayList.length > 0) {
        groups.push({
          key: 'today',
          label: `Today (${todayList.length})`,
          deadlines: todayList,
        });
      }

      if (thisWeek.length > 0) {
        groups.push({
          key: 'this-week',
          label: `This Week (${thisWeek.length})`,
          deadlines: thisWeek.sort((a, b) =>
            new Date(a.deadline_date!).getTime() - new Date(b.deadline_date!).getTime()
          ),
        });
      }

      if (thisMonth.length > 0) {
        groups.push({
          key: 'this-month',
          label: `This Month (${thisMonth.length})`,
          deadlines: thisMonth.sort((a, b) =>
            new Date(a.deadline_date!).getTime() - new Date(b.deadline_date!).getTime()
          ),
        });
      }

      if (later.length > 0) {
        groups.push({
          key: 'later',
          label: `Later (${later.length})`,
          deadlines: later.sort((a, b) =>
            new Date(a.deadline_date!).getTime() - new Date(b.deadline_date!).getTime()
          ),
        });
      }

      if (noDate.length > 0) {
        groups.push({
          key: 'no-date',
          label: `No Date Set (${noDate.length})`,
          deadlines: noDate,
        });
      }

      return groups;
    }

    if (groupBy === 'priority') {
      const priorityOrder = ['fatal', 'critical', 'important', 'standard', 'informational'];
      const byPriority: Record<string, (Deadline | CalendarDeadline)[]> = {};

      deadlines.forEach(d => {
        const priority = d.priority?.toLowerCase() || 'standard';
        if (!byPriority[priority]) {
          byPriority[priority] = [];
        }
        byPriority[priority].push(d);
      });

      return priorityOrder
        .filter(p => byPriority[p]?.length > 0)
        .map(p => ({
          key: p,
          label: `${p.charAt(0).toUpperCase() + p.slice(1)} (${byPriority[p].length})`,
          deadlines: byPriority[p].sort((a, b) => {
            if (!a.deadline_date) return 1;
            if (!b.deadline_date) return -1;
            return new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime();
          }),
          isPriority: p === 'fatal' || p === 'critical',
        }));
    }

    if (groupBy === 'case') {
      const byCase: Record<string, {
        caseNumber: string;
        caseTitle: string;
        deadlines: (Deadline | CalendarDeadline)[];
      }> = {};

      deadlines.forEach(d => {
        const caseId = d.case_id;
        if (!byCase[caseId]) {
          byCase[caseId] = {
            caseNumber: (d as CalendarDeadline).case_number || 'Unknown Case',
            caseTitle: (d as CalendarDeadline).case_title || '',
            deadlines: [],
          };
        }
        byCase[caseId].deadlines.push(d);
      });

      return Object.entries(byCase).map(([caseId, data]) => ({
        key: caseId,
        label: `${data.caseNumber} - ${data.caseTitle} (${data.deadlines.length})`,
        deadlines: data.deadlines.sort((a, b) => {
          if (!a.deadline_date) return 1;
          if (!b.deadline_date) return -1;
          return new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime();
        }),
      }));
    }

    if (groupBy === 'trigger') {
      const byTrigger: Record<string, (Deadline | CalendarDeadline)[]> = {};

      deadlines.forEach(d => {
        const trigger = d.trigger_event || 'Manual Entry';
        if (!byTrigger[trigger]) {
          byTrigger[trigger] = [];
        }
        byTrigger[trigger].push(d);
      });

      return Object.entries(byTrigger).map(([trigger, items]) => ({
        key: trigger,
        label: `${trigger.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} (${items.length})`,
        deadlines: items.sort((a, b) => {
          if (!a.deadline_date) return 1;
          if (!b.deadline_date) return -1;
          return new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime();
        }),
      }));
    }

    return [{
      key: 'all',
      label: 'All Deadlines',
      deadlines,
    }];
  }, [deadlines, groupBy]);

  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="animate-pulse">
            <div className="h-4 bg-slate-200 rounded w-32 mb-2" />
            <div className="space-y-2">
              {[1, 2].map(j => (
                <div key={j} className="h-16 bg-slate-100 rounded border border-slate-200" />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Empty state
  if (deadlines.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-500">
        <Inbox className="w-12 h-12 mb-3 text-slate-300" />
        <p className="text-sm">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {groupedDeadlines.map(group => {
        const isCollapsed = collapsedGroups.has(group.key);

        return (
          <div key={group.key}>
            {/* Group Header */}
            {groupBy !== 'none' && (
              <button
                onClick={() => toggleGroup(group.key)}
                className={`
                  w-full flex items-center gap-2 px-3 py-2 text-left font-mono text-sm
                  hover:bg-slate-50 transition-colors rounded
                  ${group.isOverdue ? 'text-red-700 bg-red-50' : ''}
                  ${group.isPriority ? 'text-red-600' : 'text-slate-600'}
                `}
              >
                {isCollapsed ? (
                  <ChevronRight className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
                {group.isOverdue && <AlertTriangle className="w-4 h-4" />}
                {!group.isOverdue && groupBy === 'date' && <Calendar className="w-4 h-4" />}
                <span className="font-bold uppercase tracking-wide">{group.label}</span>
              </button>
            )}

            {/* Group Content */}
            {!isCollapsed && (
              <div className={`space-y-2 ${groupBy !== 'none' ? 'mt-2 ml-6' : ''}`}>
                {group.deadlines.map(deadline => (
                  <DeadlineCard
                    key={deadline.id}
                    deadline={deadline}
                    onClick={() => onDeadlineClick?.(deadline)}
                    onComplete={onComplete}
                    showCase={showCase && groupBy !== 'case'}
                    compact={compact}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
