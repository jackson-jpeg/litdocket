'use client';

import { useState, useMemo } from 'react';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const locales = {
  'en-US': enUS,
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

interface Deadline {
  id: string;
  title: string;
  deadline_date: string;
  priority: string;
  case_id?: string;
  case_number?: string;
  status: string;
}

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  resource: Deadline;
}

interface CalendarViewProps {
  deadlines: Deadline[];
  onDeadlineClick?: (deadline: Deadline) => void;
}

export default function CalendarView({ deadlines, onDeadlineClick }: CalendarViewProps) {
  const [selectedPriority, setSelectedPriority] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');

  // Convert deadlines to calendar events
  const events: CalendarEvent[] = useMemo(() => {
    let filtered = deadlines;

    // Filter by priority
    if (selectedPriority !== 'all') {
      filtered = filtered.filter(d => d.priority === selectedPriority);
    }

    // Filter by status
    if (selectedStatus !== 'all') {
      filtered = filtered.filter(d => d.status === selectedStatus);
    }

    return filtered
      .filter(d => d.deadline_date)
      .map(deadline => ({
        id: deadline.id,
        title: deadline.title,
        start: new Date(deadline.deadline_date),
        end: new Date(deadline.deadline_date),
        resource: deadline,
      }));
  }, [deadlines, selectedPriority, selectedStatus]);

  // Custom event style getter
  const eventStyleGetter = (event: CalendarEvent) => {
    const deadline = event.resource;

    let backgroundColor = '#3B82F6'; // blue default
    let borderColor = '#2563EB';

    // Color by priority
    if (deadline.priority === 'fatal' || deadline.priority === 'critical') {
      backgroundColor = '#DC2626'; // red
      borderColor = '#B91C1C';
    } else if (deadline.priority === 'important' || deadline.priority === 'high') {
      backgroundColor = '#F59E0B'; // amber
      borderColor = '#D97706';
    } else if (deadline.priority === 'standard' || deadline.priority === 'medium') {
      backgroundColor = '#10B981'; // green
      borderColor = '#059669';
    } else if (deadline.priority === 'informational' || deadline.priority === 'low') {
      backgroundColor = '#6B7280'; // gray
      borderColor = '#4B5563';
    }

    // Dim if completed
    if (deadline.status === 'completed') {
      backgroundColor = '#D1D5DB';
      borderColor = '#9CA3AF';
    }

    return {
      style: {
        backgroundColor,
        borderColor,
        borderWidth: '2px',
        borderStyle: 'solid',
        borderRadius: '4px',
        opacity: deadline.status === 'completed' ? 0.6 : 1,
        color: 'white',
        fontSize: '12px',
        padding: '2px 4px',
      },
    };
  };

  const handleSelectEvent = (event: CalendarEvent) => {
    if (onDeadlineClick) {
      onDeadlineClick(event.resource);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      {/* Header with Filters */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Deadline Calendar
        </h2>

        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-slate-500" />

          {/* Priority Filter */}
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mb-4 text-sm">
        <span className="font-medium text-slate-700">Priority:</span>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-red-600 rounded"></div>
          <span className="text-slate-600">Fatal/Critical</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-amber-600 rounded"></div>
          <span className="text-slate-600">Important</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-green-600 rounded"></div>
          <span className="text-slate-600">Standard</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-gray-600 rounded"></div>
          <span className="text-slate-600">Informational</span>
        </div>
      </div>

      {/* Calendar */}
      <div style={{ height: '600px' }}>
        <Calendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          onSelectEvent={handleSelectEvent}
          eventPropGetter={eventStyleGetter}
          views={['month', 'week', 'day', 'agenda']}
          defaultView="month"
          popup
          selectable
          style={{ height: '100%' }}
        />
      </div>

      {/* Summary Stats */}
      <div className="mt-6 grid grid-cols-4 gap-4 pt-6 border-t border-slate-200">
        <div className="text-center">
          <p className="text-2xl font-bold text-blue-600">{events.length}</p>
          <p className="text-sm text-slate-600">Total Deadlines</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-red-600">
            {events.filter(e => e.resource.priority === 'fatal' || e.resource.priority === 'critical').length}
          </p>
          <p className="text-sm text-slate-600">Critical</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-green-600">
            {events.filter(e => e.resource.status === 'completed').length}
          </p>
          <p className="text-sm text-slate-600">Completed</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-slate-600">
            {events.filter(e => e.resource.status === 'pending').length}
          </p>
          <p className="text-sm text-slate-600">Pending</p>
        </div>
      </div>
    </div>
  );
}
