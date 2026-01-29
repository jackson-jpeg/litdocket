'use client';

import { useState, useMemo, useCallback } from 'react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';

export type GroupBy = 'date_range' | 'priority' | 'type' | 'trigger' | 'none';
export type SortBy = 'deadline_date' | 'priority' | 'created_at' | 'title';
export type SortDirection = 'asc' | 'desc';

export interface DeadlineFilters {
  search: string;
  priorities: string[];
  types: string[];
  statuses: string[];
  triggerId: string | null;
}

export interface DeadlineGroup {
  id: string;
  label: string;
  deadlines: Deadline[];
  isOverdue?: boolean;
  isExpanded: boolean;
}

const PRIORITY_ORDER: Record<string, number> = {
  fatal: 0,
  critical: 1,
  high: 2,
  important: 3,
  medium: 4,
  standard: 5,
  low: 6,
  informational: 7,
};

export function useCaseDeadlineFilters(deadlines: Deadline[], triggers: Trigger[]) {
  // Filter state
  const [search, setSearch] = useState('');
  const [selectedPriorities, setSelectedPriorities] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [selectedTriggerId, setSelectedTriggerId] = useState<string | null>(null);

  // Group/sort state
  const [groupBy, setGroupBy] = useState<GroupBy>('date_range');
  const [sortBy, setSortBy] = useState<SortBy>('deadline_date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Expanded groups state
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(['overdue', 'this_week', 'this_month'])
  );

  // Toggle group expansion
  const toggleGroup = useCallback((groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }, []);

  // Get unique values for filter dropdowns
  const filterOptions = useMemo(() => {
    const priorities = new Set<string>();
    const types = new Set<string>();
    const statuses = new Set<string>();

    deadlines.forEach(d => {
      if (d.priority) priorities.add(d.priority);
      if (d.deadline_type) types.add(d.deadline_type);
      if (d.status) statuses.add(d.status);
    });

    return {
      priorities: Array.from(priorities).sort((a, b) =>
        (PRIORITY_ORDER[a] ?? 99) - (PRIORITY_ORDER[b] ?? 99)
      ),
      types: Array.from(types).sort(),
      statuses: Array.from(statuses).sort(),
      triggers: triggers.map(t => ({ id: t.id, label: t.title, type: t.trigger_type })),
    };
  }, [deadlines, triggers]);

  // Apply filters to deadlines
  const filteredDeadlines = useMemo(() => {
    return deadlines.filter(deadline => {
      // Search filter
      if (search) {
        const searchLower = search.toLowerCase();
        const matchesSearch =
          deadline.title.toLowerCase().includes(searchLower) ||
          deadline.description?.toLowerCase().includes(searchLower) ||
          deadline.applicable_rule?.toLowerCase().includes(searchLower) ||
          deadline.action_required?.toLowerCase().includes(searchLower);
        if (!matchesSearch) return false;
      }

      // Priority filter
      if (selectedPriorities.length > 0 && !selectedPriorities.includes(deadline.priority)) {
        return false;
      }

      // Type filter
      if (selectedTypes.length > 0 && (!deadline.deadline_type || !selectedTypes.includes(deadline.deadline_type))) {
        return false;
      }

      // Status filter
      if (selectedStatuses.length > 0 && !selectedStatuses.includes(deadline.status)) {
        return false;
      }

      // Trigger filter (match by trigger_event field)
      if (selectedTriggerId) {
        const trigger = triggers.find(t => t.id === selectedTriggerId);
        if (trigger && deadline.trigger_event !== trigger.trigger_type) {
          return false;
        }
      }

      return true;
    });
  }, [deadlines, search, selectedPriorities, selectedTypes, selectedStatuses, selectedTriggerId, triggers]);

  // Sort deadlines
  const sortedDeadlines = useMemo(() => {
    const sorted = [...filteredDeadlines].sort((a, b) => {
      let comparison = 0;

      switch (sortBy) {
        case 'deadline_date':
          const dateA = a.deadline_date ? new Date(a.deadline_date).getTime() : Infinity;
          const dateB = b.deadline_date ? new Date(b.deadline_date).getTime() : Infinity;
          comparison = dateA - dateB;
          break;
        case 'priority':
          comparison = (PRIORITY_ORDER[a.priority] ?? 99) - (PRIORITY_ORDER[b.priority] ?? 99);
          break;
        case 'created_at':
          const createdA = a.created_at ? new Date(a.created_at).getTime() : 0;
          const createdB = b.created_at ? new Date(b.created_at).getTime() : 0;
          comparison = createdA - createdB;
          break;
        case 'title':
          comparison = a.title.localeCompare(b.title);
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return sorted;
  }, [filteredDeadlines, sortBy, sortDirection]);

  // Group deadlines
  const groupedDeadlines = useMemo((): DeadlineGroup[] => {
    if (groupBy === 'none') {
      return [{
        id: 'all',
        label: `All Deadlines (${sortedDeadlines.length})`,
        deadlines: sortedDeadlines,
        isExpanded: true,
      }];
    }

    const groups = new Map<string, Deadline[]>();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    sortedDeadlines.forEach(deadline => {
      let groupKey: string;

      switch (groupBy) {
        case 'date_range':
          if (!deadline.deadline_date) {
            groupKey = 'no_date';
          } else {
            const date = new Date(deadline.deadline_date);
            date.setHours(0, 0, 0, 0);
            const diffDays = Math.ceil((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

            if (deadline.status === 'completed') {
              groupKey = 'completed';
            } else if (diffDays < 0) {
              groupKey = 'overdue';
            } else if (diffDays === 0) {
              groupKey = 'today';
            } else if (diffDays <= 7) {
              groupKey = 'this_week';
            } else if (diffDays <= 30) {
              groupKey = 'this_month';
            } else {
              groupKey = 'later';
            }
          }
          break;

        case 'priority':
          groupKey = deadline.priority || 'standard';
          break;

        case 'type':
          groupKey = deadline.deadline_type || 'other';
          break;

        case 'trigger':
          groupKey = deadline.trigger_event || 'manual';
          break;

        default:
          groupKey = 'all';
      }

      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey)!.push(deadline);
    });

    // Convert to array and add labels
    const result: DeadlineGroup[] = [];

    if (groupBy === 'date_range') {
      const dateRangeOrder = ['overdue', 'today', 'this_week', 'this_month', 'later', 'no_date', 'completed'];
      const dateRangeLabels: Record<string, string> = {
        overdue: 'Overdue',
        today: 'Today',
        this_week: 'This Week',
        this_month: 'This Month',
        later: 'Later',
        no_date: 'No Date Set',
        completed: 'Completed',
      };

      dateRangeOrder.forEach(key => {
        const deadlines = groups.get(key);
        if (deadlines && deadlines.length > 0) {
          result.push({
            id: key,
            label: `${dateRangeLabels[key]} (${deadlines.length})`,
            deadlines,
            isOverdue: key === 'overdue',
            isExpanded: expandedGroups.has(key),
          });
        }
      });
    } else if (groupBy === 'priority') {
      const priorityOrder = ['fatal', 'critical', 'high', 'important', 'medium', 'standard', 'low', 'informational'];
      const priorityLabels: Record<string, string> = {
        fatal: 'Fatal',
        critical: 'Critical',
        high: 'High Priority',
        important: 'Important',
        medium: 'Medium Priority',
        standard: 'Standard',
        low: 'Low Priority',
        informational: 'Informational',
      };

      priorityOrder.forEach(key => {
        const deadlines = groups.get(key);
        if (deadlines && deadlines.length > 0) {
          result.push({
            id: key,
            label: `${priorityLabels[key] || key} (${deadlines.length})`,
            deadlines,
            isExpanded: expandedGroups.has(key),
          });
        }
      });
    } else if (groupBy === 'type') {
      Array.from(groups.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .forEach(([key, deadlines]) => {
          result.push({
            id: key,
            label: `${key.charAt(0).toUpperCase() + key.slice(1)} (${deadlines.length})`,
            deadlines,
            isExpanded: expandedGroups.has(key),
          });
        });
    } else if (groupBy === 'trigger') {
      // Manual first, then triggers alphabetically
      const manual = groups.get('manual');
      if (manual && manual.length > 0) {
        result.push({
          id: 'manual',
          label: `Manual Deadlines (${manual.length})`,
          deadlines: manual,
          isExpanded: expandedGroups.has('manual'),
        });
      }

      Array.from(groups.entries())
        .filter(([key]) => key !== 'manual')
        .sort((a, b) => a[0].localeCompare(b[0]))
        .forEach(([key, deadlines]) => {
          const trigger = triggers.find(t => t.trigger_type === key);
          const label = trigger?.title || key;
          result.push({
            id: key,
            label: `${label} (${deadlines.length})`,
            deadlines,
            isExpanded: expandedGroups.has(key),
          });
        });
    }

    return result;
  }, [sortedDeadlines, groupBy, expandedGroups, triggers]);

  // Clear all filters
  const clearFilters = useCallback(() => {
    setSearch('');
    setSelectedPriorities([]);
    setSelectedTypes([]);
    setSelectedStatuses([]);
    setSelectedTriggerId(null);
  }, []);

  // Check if any filters are active
  const hasActiveFilters = search ||
    selectedPriorities.length > 0 ||
    selectedTypes.length > 0 ||
    selectedStatuses.length > 0 ||
    selectedTriggerId !== null;

  return {
    // Filter state
    filters: {
      search,
      priorities: selectedPriorities,
      types: selectedTypes,
      statuses: selectedStatuses,
      triggerId: selectedTriggerId,
    },
    // Filter setters
    setSearch,
    setSelectedPriorities,
    setSelectedTypes,
    setSelectedStatuses,
    setSelectedTriggerId,
    clearFilters,
    hasActiveFilters,

    // Sort/group state
    groupBy,
    setGroupBy,
    sortBy,
    setSortBy,
    sortDirection,
    setSortDirection,

    // Group expansion
    expandedGroups,
    toggleGroup,

    // Options for dropdowns
    filterOptions,

    // Results
    filteredDeadlines,
    sortedDeadlines,
    groupedDeadlines,
  };
}
