'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Scale, ArrowLeft, Loader2, Filter, RefreshCw, Sparkles, LayoutGrid } from 'lucide-react';
import Link from 'next/link';
import { useCalendarDeadlines, CalendarDeadline } from '@/hooks/useCalendarDeadlines';
import { useToast } from '@/components/Toast';
import { deadlineEvents } from '@/lib/eventBus';
import apiClient from '@/lib/api-client';

import DeadlineSidebar from '@/components/calendar/DeadlineSidebar';
import CalendarGrid from '@/components/calendar/CalendarGrid';
import IntelligentCalendar from '@/components/calendar/IntelligentCalendar';
import DeadlineDetailModal from '@/components/calendar/DeadlineDetailModal';
import CreateDeadlineModal from '@/components/calendar/CreateDeadlineModal';
import { ToolSuggestionBanner } from '@/components/ContextualToolCard';

export default function CalendarPage() {
  const router = useRouter();
  const { showSuccess, showError, showWarning } = useToast();

  // Filters state
  const [selectedPriority, setSelectedPriority] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedCaseId, setSelectedCaseId] = useState('all');

  // Calendar view mode (basic vs intelligent with AI suggestions)
  const [viewMode, setViewMode] = useState<'basic' | 'intelligent'>('basic');

  // Modal state
  const [selectedDeadline, setSelectedDeadline] = useState<CalendarDeadline | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createModalDate, setCreateModalDate] = useState<Date | null>(null);

  // Calendar navigation state
  const [calendarNavigateDate, setCalendarNavigateDate] = useState<Date | undefined>(undefined);

  // Get calendar data
  const {
    deadlines,
    cases,
    loading,
    error,
    refetch,
    rescheduleDeadline,
    createDeadline,
    updateDeadlineStatus,
    overdueDeadlines,
    upcomingDeadlines,
    stats,
  } = useCalendarDeadlines();

  // Handle deadline click
  const handleDeadlineClick = useCallback((deadline: CalendarDeadline) => {
    setSelectedDeadline(deadline);
  }, []);

  // Handle drag-drop reschedule
  const handleEventDrop = useCallback(async (deadlineId: string, newDate: Date) => {
    const success = await rescheduleDeadline(deadlineId, newDate);
    if (success) {
      showSuccess('Deadline rescheduled');
      deadlineEvents.rescheduled({
        deadlineId,
        oldDate: '', // Not tracking old date here
        newDate: newDate.toISOString(),
      });
    } else {
      showError('Failed to reschedule deadline');
    }
  }, [rescheduleDeadline, showSuccess, showError]);

  // Handle slot selection (create new deadline)
  const handleSelectSlot = useCallback((date: Date) => {
    if (cases.length === 0) {
      showWarning('Create a case first before adding deadlines');
      return;
    }
    setCreateModalDate(date);
    setCreateModalOpen(true);
  }, [cases.length, showWarning]);

  // Handle create deadline
  const handleCreateDeadline = useCallback(async (data: any) => {
    const result = await createDeadline(data);
    if (result) {
      showSuccess(`Deadline "${result.title}" created`);
      deadlineEvents.created(result);
      return result;
    }
    return null;
  }, [createDeadline, showSuccess]);

  // Handle complete deadline
  const handleCompleteDeadline = useCallback(async (deadlineId: string) => {
    const success = await updateDeadlineStatus(deadlineId, 'completed');
    if (success) {
      showSuccess('Deadline completed');
      deadlineEvents.completed({ id: deadlineId });
    } else {
      showError('Failed to complete deadline');
    }
  }, [updateDeadlineStatus, showSuccess, showError]);

  // Handle delete deadline
  const handleDeleteDeadline = useCallback(async (deadlineId: string) => {
    try {
      await apiClient.delete(`/api/v1/deadlines/${deadlineId}`);
      showSuccess('Deadline deleted successfully');
      deadlineEvents.deleted(deadlineId);
      refetch(); // Refresh calendar data
    } catch (err) {
      console.error('Failed to delete deadline:', err);
      showError('Failed to delete deadline');
      throw err; // Re-throw so modal can handle it
    }
  }, [showSuccess, showError, refetch]);

  // Handle iCal export
  const handleExportICal = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/v1/deadlines/export/ical', {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'all_deadlines.ics');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      showSuccess('Calendar exported successfully');
    } catch (err) {
      console.error('Failed to export calendar:', err);
      showError('Failed to export calendar');
    }
  }, [showSuccess, showError]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Loading calendar...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Scale className="w-8 h-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-slate-800 mb-2">Failed to load calendar</h2>
          <p className="text-slate-600 mb-4">{error}</p>
          <button
            onClick={refetch}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 flex-shrink-0">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Scale className="w-7 h-7 text-blue-600" />
              <div>
                <h1 className="text-lg font-bold text-slate-800">LitDocket</h1>
                <p className="text-xs text-slate-500">Master Deadline Calendar</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Filters */}
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400" />

                {/* Case Filter */}
                <select
                  value={selectedCaseId}
                  onChange={(e) => setSelectedCaseId(e.target.value)}
                  className="text-sm px-2 py-1.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Cases</option>
                  {cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.case_number}
                    </option>
                  ))}
                </select>

                {/* Priority Filter */}
                <select
                  value={selectedPriority}
                  onChange={(e) => setSelectedPriority(e.target.value)}
                  className="text-sm px-2 py-1.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Priorities</option>
                  <option value="fatal">Fatal</option>
                  <option value="critical">Critical</option>
                  <option value="important">Important</option>
                  <option value="standard">Standard</option>
                  <option value="informational">Informational</option>
                </select>

                {/* Status Filter */}
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="text-sm px-2 py-1.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              {/* View Mode Toggle */}
              <div className="flex items-center border border-slate-300 rounded-lg overflow-hidden">
                <button
                  onClick={() => setViewMode('basic')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors ${
                    viewMode === 'basic'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                  title="Basic Calendar"
                >
                  <LayoutGrid className="w-4 h-4" />
                  Basic
                </button>
                <button
                  onClick={() => setViewMode('intelligent')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors ${
                    viewMode === 'intelligent'
                      ? 'bg-purple-600 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                  title="AI-Powered Calendar with Workload Analysis"
                >
                  <Sparkles className="w-4 h-4" />
                  AI Mode
                </button>
              </div>

              {/* Refresh */}
              <button
                onClick={refetch}
                className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4" />
              </button>

              {/* Back to Dashboard */}
              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Dashboard</span>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Tool Suggestion Banner - Show when no deadlines */}
      {deadlines.length === 0 && !loading && (
        <div className="flex-shrink-0 px-4 pb-3 bg-slate-100">
          <ToolSuggestionBanner
            toolId="calculator"
            message="No deadlines yet? Calculate one now"
          />
        </div>
      )}

      {/* Main Content - Sidebar + Calendar */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <DeadlineSidebar
          overdueDeadlines={overdueDeadlines}
          upcomingDeadlines={upcomingDeadlines}
          stats={stats}
          allDeadlines={deadlines}
          onDeadlineClick={handleDeadlineClick}
          onExportICal={handleExportICal}
          onQuickComplete={handleCompleteDeadline}
          onNavigateToDate={setCalendarNavigateDate}
        />

        {/* Calendar - Basic or Intelligent */}
        <div className="flex-1 overflow-hidden">
          {viewMode === 'basic' ? (
            <CalendarGrid
              deadlines={deadlines}
              onEventClick={handleDeadlineClick}
              onEventDrop={handleEventDrop}
              onSelectSlot={handleSelectSlot}
              selectedPriority={selectedPriority}
              selectedStatus={selectedStatus}
              selectedCaseId={selectedCaseId}
              navigateToDate={calendarNavigateDate}
            />
          ) : (
            <IntelligentCalendar showAISuggestions={true} />
          )}
        </div>
      </div>

      {/* Modals */}
      <DeadlineDetailModal
        deadline={selectedDeadline}
        onClose={() => setSelectedDeadline(null)}
        onComplete={handleCompleteDeadline}
        onDelete={handleDeleteDeadline}
      />

      <CreateDeadlineModal
        isOpen={createModalOpen}
        initialDate={createModalDate}
        cases={cases}
        onClose={() => {
          setCreateModalOpen(false);
          setCreateModalDate(null);
        }}
        onCreate={handleCreateDeadline}
      />
    </div>
  );
}
