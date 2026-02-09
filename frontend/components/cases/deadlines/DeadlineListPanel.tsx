'use client';

import { useState, useCallback } from 'react';
import {
  Calendar,
  Search,
  Filter,
  ChevronDown,
  ChevronRight,
  Plus,
  Download,
  CheckSquare,
  X,
  Trash2,
  Edit3,
  Clock,
  MoreHorizontal,
  SlidersHorizontal,
  AlertTriangle,
} from 'lucide-react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';
import { useCaseDeadlineFilters, GroupBy, SortBy } from '@/hooks/useCaseDeadlineFilters';
import DeadlineRow from './DeadlineRow';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';
import { deadlineEvents } from '@/lib/eventBus';

interface OptimisticUpdateFns {
  updateDeadlineStatus: (id: string, status: string) => void;
  removeDeadline: (id: string) => void;
  updateDeadlineDate: (id: string, date: string) => void;
}

interface DeadlineListPanelProps {
  deadlines: Deadline[];
  triggers: Trigger[];
  caseId: string;
  onAddEvent?: () => void;
  onExportCalendar?: () => void;
  onRefresh?: () => void;
  onOptimisticUpdate?: OptimisticUpdateFns;
  onViewDeadline?: (deadline: Deadline) => void;
  onViewChain?: (triggerId: string) => void;
  defaultGroupBy?: GroupBy;
}

export default function DeadlineListPanel({
  deadlines,
  triggers,
  caseId,
  onAddEvent,
  onExportCalendar,
  onRefresh,
  onOptimisticUpdate,
  onViewDeadline,
  onViewChain,
  defaultGroupBy,
}: DeadlineListPanelProps) {
  const { showSuccess, showError } = useToast();

  // Filter/sort/group state
  const {
    filters,
    setSearch,
    setSelectedPriorities,
    setSelectedTypes,
    setSelectedStatuses,
    setSelectedTriggerId,
    clearFilters,
    hasActiveFilters,
    groupBy,
    setGroupBy,
    sortBy,
    setSortBy,
    sortDirection,
    setSortDirection,
    toggleGroup,
    filterOptions,
    groupedDeadlines,
    filteredDeadlines,
  } = useCaseDeadlineFilters(deadlines, triggers, defaultGroupBy);

  // UI state
  const [showFilters, setShowFilters] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [processing, setProcessing] = useState(false);

  // Selection handlers
  const toggleSelection = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(filteredDeadlines.map(d => d.id)));
  }, [filteredDeadlines]);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    setSelectionMode(false);
  }, []);

  // Deadline actions with optimistic updates
  const handleComplete = useCallback(async (id: string) => {
    // Optimistic update - immediately update UI
    onOptimisticUpdate?.updateDeadlineStatus(id, 'completed');

    try {
      await apiClient.patch(`/api/v1/deadlines/${id}/status?status=completed`);
      deadlineEvents.completed({ id });
      showSuccess('Deadline completed');
      // Refetch to ensure consistency (async, doesn't block)
      onRefresh?.();
    } catch (err) {
      // Revert optimistic update on error
      onOptimisticUpdate?.updateDeadlineStatus(id, 'pending');
      showError('Failed to complete deadline');
    }
  }, [showSuccess, showError, onRefresh, onOptimisticUpdate]);

  const handleDelete = useCallback(async (id: string) => {
    if (!confirm('Delete this deadline? This cannot be undone.')) return;

    // Optimistic update - immediately remove from UI
    onOptimisticUpdate?.removeDeadline(id);

    try {
      await apiClient.delete(`/api/v1/deadlines/${id}`);
      deadlineEvents.deleted(id);
      showSuccess('Deadline deleted');
      onRefresh?.();
    } catch (err) {
      // Can't easily revert delete - refetch to restore
      onRefresh?.();
      showError('Failed to delete deadline');
    }
  }, [showSuccess, showError, onRefresh, onOptimisticUpdate]);

  const handleReschedule = useCallback(async (id: string, newDate: Date) => {
    const newDateStr = newDate.toISOString().split('T')[0];

    // Optimistic update - immediately update date in UI
    onOptimisticUpdate?.updateDeadlineDate(id, newDateStr);

    try {
      await apiClient.patch(`/api/v1/deadlines/${id}/reschedule`, {
        new_date: newDateStr,
      });
      deadlineEvents.rescheduled({
        deadlineId: id,
        oldDate: '',
        newDate: newDate.toISOString(),
      });
      showSuccess('Deadline rescheduled');
      onRefresh?.();
    } catch (err) {
      // Refetch to restore correct date on error
      onRefresh?.();
      showError('Failed to reschedule deadline');
    }
  }, [showSuccess, showError, onRefresh, onOptimisticUpdate]);

  // Bulk actions with optimistic updates
  const handleBulkComplete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setProcessing(true);

    // Optimistic update - immediately mark all as completed
    Array.from(selectedIds).forEach(id => {
      onOptimisticUpdate?.updateDeadlineStatus(id, 'completed');
    });

    try {
      await Promise.all(
        Array.from(selectedIds).map(id =>
          apiClient.patch(`/api/v1/deadlines/${id}/status?status=completed`)
        )
      );
      deadlineEvents.bulkUpdated(Array.from(selectedIds).map(id => ({ id })));
      showSuccess(`${selectedIds.size} deadline(s) completed`);
      clearSelection();
      onRefresh?.();
    } catch (err) {
      // Revert on error
      Array.from(selectedIds).forEach(id => {
        onOptimisticUpdate?.updateDeadlineStatus(id, 'pending');
      });
      showError('Failed to complete deadlines');
    } finally {
      setProcessing(false);
    }
  }, [selectedIds, showSuccess, showError, clearSelection, onRefresh, onOptimisticUpdate]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} deadline(s)? This cannot be undone.`)) return;
    setProcessing(true);

    // Optimistic update - immediately remove all
    Array.from(selectedIds).forEach(id => {
      onOptimisticUpdate?.removeDeadline(id);
    });

    try {
      await Promise.all(
        Array.from(selectedIds).map(id => apiClient.delete(`/api/v1/deadlines/${id}`))
      );
      Array.from(selectedIds).forEach(id => deadlineEvents.deleted(id));
      showSuccess(`${selectedIds.size} deadline(s) deleted`);
      clearSelection();
      onRefresh?.();
    } catch (err) {
      // Refetch to restore on error
      onRefresh?.();
      showError('Failed to delete deadlines');
    } finally {
      setProcessing(false);
    }
  }, [selectedIds, showSuccess, showError, clearSelection, onRefresh, onOptimisticUpdate]);

  // Stats
  const activeCount = deadlines.filter(d => d.status === 'pending').length;
  const overdueCount = deadlines.filter(d =>
    d.status === 'pending' &&
    d.deadline_date &&
    new Date(d.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0))
  ).length;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <Calendar className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-slate-800">
              Deadlines
              <span className="text-sm font-normal text-slate-500 ml-2">
                ({activeCount} active{overdueCount > 0 && (
                  <span className="text-red-600">, {overdueCount} overdue</span>
                )})
              </span>
            </h3>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {!selectionMode ? (
              <>
                {onAddEvent && (
                  <button
                    onClick={onAddEvent}
                    className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span className="hidden sm:inline">Add Event</span>
                  </button>
                )}
                {onExportCalendar && (
                  <button
                    onClick={onExportCalendar}
                    className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Export to Calendar"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => setSelectionMode(true)}
                  className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                  title="Manage Deadlines"
                >
                  <CheckSquare className="w-4 h-4" />
                </button>
              </>
            ) : (
              <button
                onClick={clearSelection}
                className="flex items-center gap-1 px-3 py-1.5 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
                Cancel
              </button>
            )}
          </div>
        </div>

        {/* Search and Filter Bar */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search deadlines..."
              value={filters.search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1 px-3 py-2 text-sm border rounded-lg transition-colors ${
              hasActiveFilters
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-slate-300 text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Filter className="w-4 h-4" />
            <span className="hidden sm:inline">Filter</span>
            {hasActiveFilters && (
              <span className="w-5 h-5 bg-blue-600 text-white text-xs rounded-full flex items-center justify-center">
                {[
                  filters.priorities.length,
                  filters.types.length,
                  filters.statuses.length,
                  filters.triggerId ? 1 : 0,
                ].reduce((a, b) => a + b, 0)}
              </span>
            )}
          </button>

          {/* Group/Sort */}
          <div className="relative group">
            <button className="flex items-center gap-1 px-3 py-2 text-sm border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50">
              <SlidersHorizontal className="w-4 h-4" />
              <span className="hidden sm:inline">View</span>
            </button>

            {/* Dropdown */}
            <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-2 hidden group-hover:block z-20">
              <div className="px-3 py-1 text-xs font-semibold text-slate-500 uppercase">Group By</div>
              {(['date_range', 'priority', 'type', 'trigger', 'none'] as GroupBy[]).map(option => (
                <button
                  key={option}
                  onClick={() => setGroupBy(option)}
                  className={`w-full px-3 py-1.5 text-left text-sm hover:bg-slate-50 ${
                    groupBy === option ? 'text-blue-600 font-medium' : 'text-slate-700'
                  }`}
                >
                  {option === 'date_range' ? 'Date Range' :
                   option === 'none' ? 'No Grouping' :
                   option.charAt(0).toUpperCase() + option.slice(1)}
                </button>
              ))}

              <div className="border-t border-slate-100 my-1" />

              <div className="px-3 py-1 text-xs font-semibold text-slate-500 uppercase">Sort By</div>
              {(['deadline_date', 'priority', 'created_at', 'title'] as SortBy[]).map(option => (
                <button
                  key={option}
                  onClick={() => {
                    if (sortBy === option) {
                      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
                    } else {
                      setSortBy(option);
                      setSortDirection('asc');
                    }
                  }}
                  className={`w-full px-3 py-1.5 text-left text-sm hover:bg-slate-50 flex items-center justify-between ${
                    sortBy === option ? 'text-blue-600 font-medium' : 'text-slate-700'
                  }`}
                >
                  <span>
                    {option === 'deadline_date' ? 'Date' :
                     option === 'created_at' ? 'Created' :
                     option.charAt(0).toUpperCase() + option.slice(1)}
                  </span>
                  {sortBy === option && (
                    <span className="text-xs">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {/* Priority Filter */}
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Priority</label>
                <select
                  multiple
                  value={filters.priorities}
                  onChange={(e) => setSelectedPriorities(
                    Array.from(e.target.selectedOptions, opt => opt.value)
                  )}
                  className="w-full text-sm border border-slate-300 rounded-lg p-1.5"
                  size={3}
                >
                  {filterOptions.priorities.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>

              {/* Type Filter */}
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Type</label>
                <select
                  multiple
                  value={filters.types}
                  onChange={(e) => setSelectedTypes(
                    Array.from(e.target.selectedOptions, opt => opt.value)
                  )}
                  className="w-full text-sm border border-slate-300 rounded-lg p-1.5"
                  size={3}
                >
                  {filterOptions.types.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {/* Status Filter */}
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
                <select
                  multiple
                  value={filters.statuses}
                  onChange={(e) => setSelectedStatuses(
                    Array.from(e.target.selectedOptions, opt => opt.value)
                  )}
                  className="w-full text-sm border border-slate-300 rounded-lg p-1.5"
                  size={3}
                >
                  {filterOptions.statuses.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {/* Trigger Filter */}
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Trigger</label>
                <select
                  value={filters.triggerId || ''}
                  onChange={(e) => setSelectedTriggerId(e.target.value || null)}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2"
                >
                  <option value="">All Triggers</option>
                  {filterOptions.triggers.map(t => (
                    <option key={t.id} value={t.id}>{t.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="mt-2 text-sm text-blue-600 hover:text-blue-700"
              >
                Clear all filters
              </button>
            )}
          </div>
        )}

        {/* Bulk Action Bar */}
        {selectionMode && (
          <div className="mt-3 p-2 bg-blue-50 rounded-lg border border-blue-200 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-slate-700">
                {selectedIds.size} selected
              </span>
              <button
                onClick={selectAll}
                className="text-xs text-blue-600 hover:text-blue-700"
              >
                Select All ({filteredDeadlines.length})
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleBulkComplete}
                disabled={processing || selectedIds.size === 0}
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded border border-green-200 disabled:opacity-50"
              >
                <CheckSquare className="w-3 h-3" />
                Complete
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={processing || selectedIds.size === 0}
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded border border-red-200 disabled:opacity-50"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Deadline List */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredDeadlines.length === 0 ? (
          <div className="text-center py-12">
            <Calendar className="w-12 h-12 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-600">
              {hasActiveFilters ? 'No deadlines match your filters' : 'No deadlines yet'}
            </p>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="mt-2 text-sm text-blue-600 hover:text-blue-700"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {groupedDeadlines.map(group => (
              <div key={group.id}>
                {/* Group Header */}
                <button
                  onClick={() => toggleGroup(group.id)}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors ${
                    group.isOverdue
                      ? 'bg-red-100 text-red-800 hover:bg-red-200'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {group.isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  <span className="font-medium text-sm">{group.label}</span>
                  {group.isOverdue && (
                    <AlertTriangle className="w-4 h-4 ml-auto" />
                  )}
                </button>

                {/* Group Content */}
                {group.isExpanded && (
                  <div className="mt-2 space-y-2">
                    {group.deadlines.map(deadline => (
                      <DeadlineRow
                        key={deadline.id}
                        deadline={deadline}
                        triggers={triggers}
                        selectionMode={selectionMode}
                        isSelected={selectedIds.has(deadline.id)}
                        onToggleSelection={toggleSelection}
                        onComplete={handleComplete}
                        onDelete={handleDelete}
                        onReschedule={handleReschedule}
                        onClick={onViewDeadline ? () => onViewDeadline(deadline) : undefined}
                        onViewChain={onViewChain}
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
