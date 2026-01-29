'use client';

/**
 * Docket Page - Unified Deadline Management Center
 *
 * Replaces the separate Calendar page with a more powerful view:
 * - Collapsible mini-calendar for date selection
 * - Deadline list as primary view (grouped by date)
 * - Full calendar view toggle
 * - Stats overview
 * - Quick filters
 * - Global "Add Trigger" action
 *
 * This is the central hub for cross-case deadline management.
 */

import { useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  Calendar as CalendarIcon,
  List,
  Filter,
  Download,
  Plus,
  RefreshCw,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
} from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, isSameMonth, addMonths, subMonths } from 'date-fns';

import { useDeadlines, CalendarDeadline } from '@/features/deadlines';
import { UnifiedDeadlineModal } from '@/features/deadlines';
import DeadlineList from '@/features/deadlines/components/DeadlineList';
import { useToast } from '@/shared/components/ui/Toast';
import apiClient from '@/lib/api-client';
import { deadlineEvents } from '@/lib/eventBus';

type ViewMode = 'list' | 'calendar';
type GroupBy = 'date' | 'priority' | 'case';

export default function DocketPage() {
  const router = useRouter();
  const { showSuccess, showError } = useToast();

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [groupBy, setGroupBy] = useState<GroupBy>('date');
  const [showMiniCalendar, setShowMiniCalendar] = useState(true);

  // Filter state
  const [selectedPriority, setSelectedPriority] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('pending');
  const [selectedCaseId, setSelectedCaseId] = useState('all');
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Mini calendar state
  const [calendarMonth, setCalendarMonth] = useState(new Date());

  // Modal state
  const [selectedDeadline, setSelectedDeadline] = useState<CalendarDeadline | null>(null);

  // Get deadline data
  const {
    deadlines,
    cases,
    loading,
    error,
    refetch,
    updateDeadlineStatus,
    deleteDeadline,
    overdueDeadlines,
    todayDeadlines,
    upcomingDeadlines,
    stats,
  } = useDeadlines({
    status: selectedStatus === 'all' ? undefined : selectedStatus,
    priority: selectedPriority === 'all' ? undefined : selectedPriority,
    caseId: selectedCaseId === 'all' ? undefined : selectedCaseId,
  });

  // Filter deadlines by selected date
  const filteredDeadlines = useMemo(() => {
    if (!selectedDate) return deadlines;

    return deadlines.filter(d => {
      if (!d.deadline_date) return false;
      const deadlineDate = new Date(d.deadline_date);
      return isSameDay(deadlineDate, selectedDate);
    });
  }, [deadlines, selectedDate]);

  // Get deadlines by date for mini-calendar dots
  const deadlinesByDate = useMemo(() => {
    const map = new Map<string, { count: number; hasOverdue: boolean; hasCritical: boolean }>();

    deadlines.forEach(d => {
      if (!d.deadline_date || d.status !== 'pending') return;

      const dateKey = format(new Date(d.deadline_date), 'yyyy-MM-dd');
      const existing = map.get(dateKey) || { count: 0, hasOverdue: false, hasCritical: false };

      const isOverdue = new Date(d.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));
      const isCritical = d.priority === 'fatal' || d.priority === 'critical';

      map.set(dateKey, {
        count: existing.count + 1,
        hasOverdue: existing.hasOverdue || isOverdue,
        hasCritical: existing.hasCritical || isCritical,
      });
    });

    return map;
  }, [deadlines]);

  // Handle complete deadline
  const handleComplete = useCallback(async (id: string) => {
    const success = await updateDeadlineStatus(id, 'completed');
    if (success) {
      showSuccess('Deadline completed');
      deadlineEvents.completed({ id });
    } else {
      showError('Failed to complete deadline');
    }
  }, [updateDeadlineStatus, showSuccess, showError]);

  // Handle delete deadline
  const handleDelete = useCallback(async (id: string) => {
    const success = await deleteDeadline(id);
    if (success) {
      showSuccess('Deadline deleted');
      deadlineEvents.deleted(id);
      setSelectedDeadline(null);
    } else {
      showError('Failed to delete deadline');
    }
  }, [deleteDeadline, showSuccess, showError]);

  // Handle iCal export
  const handleExportICal = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/v1/deadlines/export/ical', {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'litdocket_deadlines.ics');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      showSuccess('Calendar exported');
    } catch (err) {
      showError('Failed to export calendar');
    }
  }, [showSuccess, showError]);

  // Generate mini-calendar days
  const calendarDays = useMemo(() => {
    const start = startOfMonth(calendarMonth);
    const end = endOfMonth(calendarMonth);
    const days = eachDayOfInterval({ start, end });

    // Pad start to align with week
    const startDay = start.getDay();
    const paddedDays: (Date | null)[] = Array(startDay).fill(null);
    paddedDays.push(...days);

    // Pad end to complete week
    while (paddedDays.length % 7 !== 0) {
      paddedDays.push(null);
    }

    return paddedDays;
  }, [calendarMonth]);

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600 font-mono text-sm">Loading docket...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-slate-800 mb-2">Failed to load docket</h2>
          <p className="text-slate-600 mb-4">{error}</p>
          <button
            onClick={refetch}
            className="px-4 py-2 bg-slate-800 text-white hover:bg-slate-700 transition-colors rounded-lg"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const today = new Date();

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          {/* Title */}
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Docket</h1>
              <p className="text-sm text-slate-500">
                {stats.pending} pending deadlines across {cases.length} cases
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              {/* View toggle */}
              <div className="flex items-center border border-slate-300 rounded overflow-hidden">
                <button
                  onClick={() => setViewMode('list')}
                  className={`px-3 py-1.5 text-sm flex items-center gap-1.5 transition-colors ${
                    viewMode === 'list'
                      ? 'bg-slate-800 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <List className="w-4 h-4" />
                  List
                </button>
                <button
                  onClick={() => setViewMode('calendar')}
                  className={`px-3 py-1.5 text-sm flex items-center gap-1.5 transition-colors ${
                    viewMode === 'calendar'
                      ? 'bg-slate-800 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <LayoutGrid className="w-4 h-4" />
                  Calendar
                </button>
              </div>

              {/* Export */}
              <button
                onClick={handleExportICal}
                className="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-50 rounded text-sm flex items-center gap-1.5"
              >
                <Download className="w-4 h-4" />
                Export
              </button>

              {/* Refresh */}
              <button
                onClick={refetch}
                className="p-2 border border-slate-300 text-slate-600 hover:bg-slate-50 rounded"
              >
                <RefreshCw className="w-4 h-4" />
              </button>

              {/* Add Trigger */}
              <button
                onClick={() => router.push('/cases')}
                className="px-4 py-2 bg-slate-800 text-white hover:bg-slate-700 transition-colors text-sm font-medium flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Trigger
              </button>
            </div>
          </div>

          {/* Filters Row */}
          <div className="flex items-center gap-4 mt-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />

              {/* Status filter */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="text-sm px-2 py-1.5 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
              </select>

              {/* Priority filter */}
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
                className="text-sm px-2 py-1.5 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Priority</option>
                <option value="fatal">Fatal</option>
                <option value="critical">Critical</option>
                <option value="important">Important</option>
                <option value="standard">Standard</option>
              </select>

              {/* Case filter */}
              <select
                value={selectedCaseId}
                onChange={(e) => setSelectedCaseId(e.target.value)}
                className="text-sm px-2 py-1.5 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Cases</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.case_number}
                  </option>
                ))}
              </select>

              {/* Group by (list view only) */}
              {viewMode === 'list' && (
                <select
                  value={groupBy}
                  onChange={(e) => setGroupBy(e.target.value as GroupBy)}
                  className="text-sm px-2 py-1.5 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="date">Group by Date</option>
                  <option value="priority">Group by Priority</option>
                  <option value="case">Group by Case</option>
                </select>
              )}
            </div>

            {/* Clear date filter */}
            {selectedDate && (
              <button
                onClick={() => setSelectedDate(null)}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Clear date filter: {format(selectedDate, 'MMM d')}
              </button>
            )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex gap-6">
        {/* Sidebar - Mini Calendar & Stats */}
        {showMiniCalendar && (
          <aside className="w-80 bg-white border border-slate-200 rounded-lg flex-shrink-0 overflow-hidden">
            {/* Stats Cards */}
            <div className="p-4 border-b border-slate-200">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-red-50 border border-red-200 p-3">
                  <div className="flex items-center gap-2 text-red-700">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-2xl font-bold">{stats.overdue}</span>
                  </div>
                  <p className="text-xs text-red-600 mt-1">Overdue</p>
                </div>
                <div className="bg-amber-50 border border-amber-200 p-3">
                  <div className="flex items-center gap-2 text-amber-700">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-2xl font-bold">{stats.critical}</span>
                  </div>
                  <p className="text-xs text-amber-600 mt-1">Critical</p>
                </div>
                <div className="bg-blue-50 border border-blue-200 p-3">
                  <div className="flex items-center gap-2 text-blue-700">
                    <Clock className="w-4 h-4" />
                    <span className="text-2xl font-bold">{stats.pending}</span>
                  </div>
                  <p className="text-xs text-blue-600 mt-1">Pending</p>
                </div>
                <div className="bg-green-50 border border-green-200 p-3">
                  <div className="flex items-center gap-2 text-green-700">
                    <CheckCircle2 className="w-4 h-4" />
                    <span className="text-2xl font-bold">{stats.completedThisMonth}</span>
                  </div>
                  <p className="text-xs text-green-600 mt-1">Done (month)</p>
                </div>
              </div>
            </div>

            {/* Mini Calendar */}
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-mono text-sm font-bold text-slate-700 uppercase">
                  {format(calendarMonth, 'MMMM yyyy')}
                </h3>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setCalendarMonth(subMonths(calendarMonth, 1))}
                    className="p-1 hover:bg-slate-100 rounded"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setCalendarMonth(addMonths(calendarMonth, 1))}
                    className="p-1 hover:bg-slate-100 rounded"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Day headers */}
              <div className="grid grid-cols-7 gap-1 mb-1">
                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => (
                  <div key={i} className="text-center text-xs font-mono text-slate-400 py-1">
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar grid */}
              <div className="grid grid-cols-7 gap-1">
                {calendarDays.map((day, i) => {
                  if (!day) {
                    return <div key={i} className="h-8" />;
                  }

                  const dateKey = format(day, 'yyyy-MM-dd');
                  const dayData = deadlinesByDate.get(dateKey);
                  const isToday = isSameDay(day, today);
                  const isSelected = selectedDate && isSameDay(day, selectedDate);
                  const isCurrentMonth = isSameMonth(day, calendarMonth);

                  return (
                    <button
                      key={i}
                      onClick={() => setSelectedDate(isSelected ? null : day)}
                      className={`
                        relative h-8 text-sm font-mono rounded transition-colors
                        ${isCurrentMonth ? 'text-slate-700' : 'text-slate-300'}
                        ${isToday ? 'bg-blue-600 text-white font-bold' : ''}
                        ${isSelected && !isToday ? 'bg-slate-800 text-white' : ''}
                        ${!isSelected && !isToday ? 'hover:bg-slate-100' : ''}
                        ${dayData?.hasOverdue ? 'ring-1 ring-red-400' : ''}
                      `}
                    >
                      {format(day, 'd')}
                      {/* Deadline indicator dots */}
                      {dayData && dayData.count > 0 && (
                        <div className="absolute bottom-0.5 left-1/2 -translate-x-1/2 flex gap-0.5">
                          <div className={`w-1 h-1 rounded-full ${
                            dayData.hasOverdue ? 'bg-red-500' :
                            dayData.hasCritical ? 'bg-amber-500' : 'bg-blue-500'
                          }`} />
                          {dayData.count > 3 && (
                            <div className="w-1 h-1 rounded-full bg-slate-400" />
                          )}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Overdue Section */}
            {overdueDeadlines.length > 0 && (
              <div className="p-4 border-t border-slate-200">
                <h3 className="font-mono text-xs font-bold text-red-700 uppercase mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Overdue ({overdueDeadlines.length})
                </h3>
                <div className="space-y-2">
                  {overdueDeadlines.slice(0, 5).map(d => (
                    <button
                      key={d.id}
                      onClick={() => setSelectedDeadline(d)}
                      className="w-full text-left p-2 bg-red-50 border border-red-200 hover:bg-red-100 transition-colors"
                    >
                      <p className="text-sm font-medium text-red-800 truncate">{d.title}</p>
                      <p className="text-xs text-red-600 font-mono">
                        {d.deadline_date ? format(new Date(d.deadline_date), 'MMM d') : 'No date'}
                      </p>
                    </button>
                  ))}
                  {overdueDeadlines.length > 5 && (
                    <p className="text-xs text-red-600 text-center">
                      +{overdueDeadlines.length - 5} more
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Today Section */}
            {todayDeadlines.length > 0 && (
              <div className="p-4 border-t border-slate-200">
                <h3 className="font-mono text-xs font-bold text-blue-700 uppercase mb-3 flex items-center gap-2">
                  <CalendarIcon className="w-4 h-4" />
                  Today ({todayDeadlines.length})
                </h3>
                <div className="space-y-2">
                  {todayDeadlines.map(d => (
                    <button
                      key={d.id}
                      onClick={() => setSelectedDeadline(d)}
                      className="w-full text-left p-2 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-colors"
                    >
                      <p className="text-sm font-medium text-blue-800 truncate">{d.title}</p>
                      <p className="text-xs text-blue-600">{d.case_number}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </aside>
        )}

        {/* Main Content Area */}
        <main className="flex-1">
          {viewMode === 'list' ? (
            <DeadlineList
              deadlines={filteredDeadlines}
              groupBy={groupBy}
              onDeadlineClick={(d) => setSelectedDeadline(d as CalendarDeadline)}
              onComplete={handleComplete}
              showCase={selectedCaseId === 'all'}
              emptyMessage={
                selectedDate
                  ? `No deadlines on ${format(selectedDate, 'MMMM d, yyyy')}`
                  : 'No deadlines found'
              }
            />
          ) : (
            /* Full Calendar View - can integrate react-big-calendar here */
            <div className="bg-white border border-slate-200 p-6 text-center">
              <CalendarIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">
                Full calendar view coming soon.
              </p>
              <p className="text-sm text-slate-400 mt-2">
                Use List view for now, or click dates in the mini-calendar.
              </p>
            </div>
          )}
        </main>
      </div>

      {/* Deadline Detail Modal */}
      <UnifiedDeadlineModal
        isOpen={!!selectedDeadline}
        deadline={selectedDeadline}
        onClose={() => setSelectedDeadline(null)}
        onUpdate={refetch}
        onComplete={handleComplete}
        onDelete={handleDelete}
        showCaseLink={true}
      />
    </div>
  );
}
