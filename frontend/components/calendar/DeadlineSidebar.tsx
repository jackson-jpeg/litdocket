'use client';

import { useState } from 'react';
import {
  AlertTriangle,
  Clock,
  Calendar,
  CheckCircle2,
  Download,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import { CalendarDeadline } from '@/hooks/useCalendarDeadlines';

interface DeadlineSidebarProps {
  overdueDeadlines: CalendarDeadline[];
  upcomingDeadlines: CalendarDeadline[];
  stats: {
    total: number;
    pending: number;
    overdue: number;
    critical: number;
    completedThisMonth: number;
  };
  onDeadlineClick: (deadline: CalendarDeadline) => void;
  onExportICal: () => void;
  onQuickComplete: (deadlineId: string) => void;
}

export default function DeadlineSidebar({
  overdueDeadlines,
  upcomingDeadlines,
  stats,
  onDeadlineClick,
  onExportICal,
  onQuickComplete,
}: DeadlineSidebarProps) {
  const [overdueExpanded, setOverdueExpanded] = useState(true);
  const [upcomingExpanded, setUpcomingExpanded] = useState(true);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'fatal':
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'important':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'standard':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const diffTime = date.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays === -1) return 'Yesterday';
    if (diffDays < -1) return `${Math.abs(diffDays)} days overdue`;
    if (diffDays <= 7) return `In ${diffDays} days`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const DeadlineItem = ({ deadline, isOverdue = false }: { deadline: CalendarDeadline; isOverdue?: boolean }) => (
    <div
      className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
        isOverdue ? 'bg-red-50 border-red-200 hover:bg-red-100' : 'bg-white border-slate-200 hover:bg-slate-50'
      }`}
      onClick={() => onDeadlineClick(deadline)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className={`font-medium text-sm truncate ${isOverdue ? 'text-red-900' : 'text-slate-900'}`}>
            {deadline.title}
          </p>
          <p className="text-xs text-slate-500 truncate mt-0.5">
            {deadline.case_number}
          </p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onQuickComplete(deadline.id);
          }}
          className="p-1 rounded hover:bg-green-100 text-slate-400 hover:text-green-600 transition-colors"
          title="Mark complete"
        >
          <CheckCircle2 className="w-4 h-4" />
        </button>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className={`text-xs px-2 py-0.5 rounded-full border ${getPriorityColor(deadline.priority)}`}>
          {deadline.priority}
        </span>
        <span className={`text-xs ${isOverdue ? 'text-red-600 font-medium' : 'text-slate-500'}`}>
          {formatDate(deadline.deadline_date!)}
        </span>
      </div>
    </div>
  );

  return (
    <div className="w-80 bg-slate-50 border-r border-slate-200 flex flex-col h-full overflow-hidden">
      {/* Stats Header */}
      <div className="p-4 bg-white border-b border-slate-200">
        <h2 className="font-semibold text-slate-800 mb-3">Deadline Overview</h2>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-100 rounded-lg p-2 text-center">
            <p className="text-2xl font-bold text-slate-800">{stats.pending}</p>
            <p className="text-xs text-slate-500">Pending</p>
          </div>
          <div className={`rounded-lg p-2 text-center ${stats.overdue > 0 ? 'bg-red-100' : 'bg-green-100'}`}>
            <p className={`text-2xl font-bold ${stats.overdue > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {stats.overdue}
            </p>
            <p className={`text-xs ${stats.overdue > 0 ? 'text-red-600' : 'text-green-600'}`}>Overdue</p>
          </div>
          <div className={`rounded-lg p-2 text-center ${stats.critical > 0 ? 'bg-amber-100' : 'bg-slate-100'}`}>
            <p className={`text-2xl font-bold ${stats.critical > 0 ? 'text-amber-600' : 'text-slate-600'}`}>
              {stats.critical}
            </p>
            <p className="text-xs text-slate-500">Critical</p>
          </div>
          <div className="bg-green-100 rounded-lg p-2 text-center">
            <p className="text-2xl font-bold text-green-600">{stats.completedThisMonth}</p>
            <p className="text-xs text-green-600">Done (Month)</p>
          </div>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Overdue Section */}
        {overdueDeadlines.length > 0 && (
          <div>
            <button
              onClick={() => setOverdueExpanded(!overdueExpanded)}
              className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg bg-red-100 text-red-800 hover:bg-red-200 transition-colors"
            >
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                <span className="font-medium text-sm">Overdue ({overdueDeadlines.length})</span>
              </div>
              {overdueExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
            {overdueExpanded && (
              <div className="mt-2 space-y-2">
                {overdueDeadlines.slice(0, 10).map((deadline) => (
                  <DeadlineItem key={deadline.id} deadline={deadline} isOverdue />
                ))}
                {overdueDeadlines.length > 10 && (
                  <p className="text-xs text-center text-red-600">
                    +{overdueDeadlines.length - 10} more overdue
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Upcoming Section */}
        <div>
          <button
            onClick={() => setUpcomingExpanded(!upcomingExpanded)}
            className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg bg-blue-100 text-blue-800 hover:bg-blue-200 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span className="font-medium text-sm">Next 7 Days ({upcomingDeadlines.length})</span>
            </div>
            {upcomingExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
          {upcomingExpanded && (
            <div className="mt-2 space-y-2">
              {upcomingDeadlines.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">
                  No deadlines in the next 7 days
                </p>
              ) : (
                <>
                  {upcomingDeadlines.slice(0, 10).map((deadline) => (
                    <DeadlineItem key={deadline.id} deadline={deadline} />
                  ))}
                  {upcomingDeadlines.length > 10 && (
                    <p className="text-xs text-center text-slate-500">
                      +{upcomingDeadlines.length - 10} more upcoming
                    </p>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Export Button */}
      <div className="p-4 border-t border-slate-200 bg-white">
        <button
          onClick={onExportICal}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Download className="w-4 h-4" />
          <span className="text-sm font-medium">Export to Calendar</span>
        </button>
        <p className="text-xs text-slate-500 text-center mt-2">
          Download .ics file for Outlook, Google Calendar, etc.
        </p>
      </div>
    </div>
  );
}
