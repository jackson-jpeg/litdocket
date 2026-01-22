'use client';

import { useState, useMemo, useCallback } from 'react';
import { Calendar, dateFnsLocalizer, View } from 'react-big-calendar';
import withDragAndDrop from 'react-big-calendar/lib/addons/dragAndDrop';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import Tippy from '@tippyjs/react';
import 'tippy.js/dist/tippy.css';
import { CalendarDeadline } from '@/hooks/useCalendarDeadlines';
import { parseLocalDate } from '@/lib/formatters';

import 'react-big-calendar/lib/css/react-big-calendar.css';
import 'react-big-calendar/lib/addons/dragAndDrop/styles.css';

const locales = { 'en-US': enUS };

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: () => startOfWeek(new Date(), { weekStartsOn: 0 }),
  getDay,
  locales,
});

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  resource: CalendarDeadline;
}

// Create DnD-enabled calendar - cast to any to avoid complex type issues
const DnDCalendar: any = withDragAndDrop(Calendar);

interface CalendarGridProps {
  deadlines: CalendarDeadline[];
  onEventClick: (deadline: CalendarDeadline) => void;
  onEventDrop: (deadlineId: string, newDate: Date) => Promise<void>;
  onSelectSlot: (date: Date) => void;
  selectedPriority: string;
  selectedStatus: string;
  selectedCaseId: string;
  navigateToDate?: Date;
}

export default function CalendarGrid({
  deadlines,
  onEventClick,
  onEventDrop,
  onSelectSlot,
  selectedPriority,
  selectedStatus,
  selectedCaseId,
  navigateToDate,
}: CalendarGridProps) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [currentView, setCurrentView] = useState<View>('month');
  const [highlightedDate, setHighlightedDate] = useState<Date | null>(null);

  // Update current date when navigateToDate changes
  if (navigateToDate && navigateToDate.getTime() !== currentDate.getTime()) {
    setCurrentDate(navigateToDate);
    // Set highlighted date and clear after 2 seconds
    setHighlightedDate(navigateToDate);
    setTimeout(() => {
      setHighlightedDate(null);
    }, 2000);
  }

  // Convert deadlines to calendar events with filtering
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

    // Filter by case
    if (selectedCaseId !== 'all') {
      filtered = filtered.filter(d => d.case_id === selectedCaseId);
    }

    return filtered
      .filter(d => d.deadline_date) // Only include deadlines with dates
      .map(deadline => ({
        id: deadline.id,
        title: deadline.title,
        start: parseLocalDate(deadline.deadline_date!),
        end: parseLocalDate(deadline.deadline_date!),
        allDay: true,
        resource: deadline,
      }));
  }, [deadlines, selectedPriority, selectedStatus, selectedCaseId]);

  // Group deadlines by date for indicator dots
  const deadlinesByDate = useMemo(() => {
    const grouped = new Map<string, CalendarDeadline[]>();

    deadlines
      .filter(d => d.deadline_date)
      .forEach(deadline => {
        const dateKey = format(parseLocalDate(deadline.deadline_date!), 'yyyy-MM-dd');
        if (!grouped.has(dateKey)) {
          grouped.set(dateKey, []);
        }
        grouped.get(dateKey)!.push(deadline);
      });

    return grouped;
  }, [deadlines]);

  // Custom event styling
  const eventStyleGetter = useCallback((event: CalendarEvent) => {
    const deadline = event.resource;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const eventDate = new Date(event.start);
    eventDate.setHours(0, 0, 0, 0);

    const isOverdue = eventDate < today && deadline.status === 'pending';
    const isCompleted = deadline.status === 'completed';

    let backgroundColor = '#3B82F6'; // blue default
    let borderColor = '#2563EB';
    let borderStyle = 'solid';

    // Priority colors
    if (deadline.priority === 'fatal' || deadline.priority === 'critical') {
      backgroundColor = '#DC2626';
      borderColor = '#B91C1C';
    } else if (deadline.priority === 'important') {
      backgroundColor = '#F59E0B';
      borderColor = '#D97706';
    } else if (deadline.priority === 'standard') {
      backgroundColor = '#10B981';
      borderColor = '#059669';
    } else if (deadline.priority === 'informational') {
      backgroundColor = '#6B7280';
      borderColor = '#4B5563';
    }

    // Overdue styling - dashed border, keep priority color
    if (isOverdue) {
      borderStyle = 'dashed';
      borderColor = '#DC2626';
    }

    // Completed styling
    if (isCompleted) {
      backgroundColor = '#D1D5DB';
      borderColor = '#9CA3AF';
    }

    return {
      style: {
        backgroundColor,
        borderColor,
        borderWidth: isOverdue ? '3px' : '2px',
        borderStyle,
        borderRadius: '4px',
        opacity: isCompleted ? 0.5 : 1,
        color: 'white',
        fontSize: '11px',
        padding: '2px 4px',
        cursor: 'pointer',
      },
    };
  }, []);

  // Handle event selection
  const handleSelectEvent = useCallback((event: CalendarEvent) => {
    onEventClick(event.resource);
  }, [onEventClick]);

  // Handle slot selection (click on empty date)
  const handleSelectSlot = useCallback(({ start }: { start: Date }) => {
    onSelectSlot(start);
  }, [onSelectSlot]);

  // Handle drag and drop
  const handleEventDrop = useCallback(async ({ event, start }: { event: CalendarEvent; start: Date | string }) => {
    await onEventDrop(event.id, new Date(start));
  }, [onEventDrop]);

  // Navigation handlers
  const goToToday = () => setCurrentDate(new Date());
  const goToPrev = () => {
    const newDate = new Date(currentDate);
    if (currentView === 'month') {
      newDate.setMonth(newDate.getMonth() - 1);
    } else if (currentView === 'week') {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setDate(newDate.getDate() - 1);
    }
    setCurrentDate(newDate);
  };
  const goToNext = () => {
    const newDate = new Date(currentDate);
    if (currentView === 'month') {
      newDate.setMonth(newDate.getMonth() + 1);
    } else if (currentView === 'week') {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setDate(newDate.getDate() + 1);
    }
    setCurrentDate(newDate);
  };

  // Format current date display
  const dateLabel = useMemo(() => {
    if (currentView === 'month') {
      return format(currentDate, 'MMMM yyyy');
    } else if (currentView === 'week') {
      const weekStart = startOfWeek(currentDate);
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 6);
      return `${format(weekStart, 'MMM d')} - ${format(weekEnd, 'MMM d, yyyy')}`;
    } else if (currentView === 'day') {
      return format(currentDate, 'EEEE, MMMM d, yyyy');
    }
    return format(currentDate, 'MMMM yyyy');
  }, [currentDate, currentView]);

  // Custom month date header with deadline indicator dots
  const MonthDateHeader = useCallback(({ label, date }: { label: string; date: Date }) => {
    const dateKey = format(date, 'yyyy-MM-dd');
    const dayDeadlines = deadlinesByDate.get(dateKey) || [];

    // Get unique priority levels for this date
    const priorities = new Set(dayDeadlines.map(d => d.priority));
    const hasCritical = priorities.has('fatal') || priorities.has('critical');
    const hasImportant = priorities.has('important');
    const hasStandard = priorities.has('standard');
    const hasInfo = priorities.has('informational');

    // Count by priority
    const criticalCount = dayDeadlines.filter(d => d.priority === 'fatal' || d.priority === 'critical').length;
    const importantCount = dayDeadlines.filter(d => d.priority === 'important').length;
    const standardCount = dayDeadlines.filter(d => d.priority === 'standard').length;
    const infoCount = dayDeadlines.filter(d => d.priority === 'informational').length;

    // Tooltip content
    const tooltipContent = dayDeadlines.length > 0 ? (
      <div className="text-xs">
        <div className="font-semibold mb-1">{dayDeadlines.length} deadline{dayDeadlines.length !== 1 ? 's' : ''}</div>
        {criticalCount > 0 && <div className="text-red-200">{criticalCount} Critical</div>}
        {importantCount > 0 && <div className="text-amber-200">{importantCount} Important</div>}
        {standardCount > 0 && <div className="text-green-200">{standardCount} Standard</div>}
        {infoCount > 0 && <div className="text-gray-300">{infoCount} Info</div>}
        {dayDeadlines[0] && (
          <div className="mt-1 pt-1 border-t border-gray-600 text-gray-300">
            Next: {dayDeadlines[0].title}
          </div>
        )}
      </div>
    ) : null;

    const dateCell = (
      <div className="flex flex-col items-center">
        <span>{label}</span>
        {dayDeadlines.length > 0 && (
          <div className="flex items-center gap-0.5 mt-0.5">
            {hasCritical && <div className="w-1.5 h-1.5 rounded-full bg-red-600"></div>}
            {hasImportant && <div className="w-1.5 h-1.5 rounded-full bg-amber-500"></div>}
            {hasStandard && <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>}
            {hasInfo && <div className="w-1.5 h-1.5 rounded-full bg-gray-500"></div>}
          </div>
        )}
      </div>
    );

    if (dayDeadlines.length === 0) {
      return dateCell;
    }

    return (
      <Tippy
        content={tooltipContent}
        placement="top"
        theme="dark"
        arrow={true}
      >
        <span className="cursor-help">
          {dateCell}
        </span>
      </Tippy>
    );
  }, [deadlinesByDate]);

  return (
    <div className="flex flex-col h-full">
      {/* Custom Toolbar */}
      <div className="flex items-center justify-between p-4 bg-white border-b border-slate-200">
        {/* Navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={goToToday}
            className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Today
          </button>
          <div className="flex items-center">
            <button
              onClick={goToPrev}
              className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <ChevronLeft className="w-5 h-5 text-slate-600" />
            </button>
            <button
              onClick={goToNext}
              className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <ChevronRight className="w-5 h-5 text-slate-600" />
            </button>
          </div>
          <h2 className="text-lg font-semibold text-slate-800 ml-2">{dateLabel}</h2>
        </div>

        {/* View Switcher */}
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
          {(['month', 'week', 'day', 'agenda'] as View[]).map((view) => (
            <button
              key={view}
              onClick={() => setCurrentView(view)}
              className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                currentView === view
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-800'
              }`}
            >
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-4 py-2 bg-slate-50 border-b border-slate-200 text-xs">
        <span className="font-medium text-slate-600">Priority:</span>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-600 rounded"></div>
          <span className="text-slate-600">Critical/Fatal</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-amber-500 rounded"></div>
          <span className="text-slate-600">Important</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-green-500 rounded"></div>
          <span className="text-slate-600">Standard</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-gray-500 rounded"></div>
          <span className="text-slate-600">Info</span>
        </div>
        <span className="text-slate-400">|</span>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 border-2 border-dashed border-red-600 rounded"></div>
          <span className="text-slate-600">Overdue</span>
        </div>
        <span className="text-slate-400">|</span>
        <div className="flex items-center gap-1">
          <div className="flex gap-0.5">
            <div className="w-1.5 h-1.5 bg-red-600 rounded-full"></div>
            <div className="w-1.5 h-1.5 bg-amber-500 rounded-full"></div>
          </div>
          <span className="text-slate-600">Deadline Indicators</span>
        </div>
      </div>

      {/* Calendar */}
      <div className="flex-1 p-4 bg-white">
        <DnDCalendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          date={currentDate}
          onNavigate={setCurrentDate}
          view={currentView}
          onView={setCurrentView}
          onSelectEvent={handleSelectEvent}
          onSelectSlot={handleSelectSlot}
          onEventDrop={handleEventDrop}
          eventPropGetter={eventStyleGetter}
          selectable
          resizable={false}
          popup
          toolbar={false}
          style={{ height: '100%' }}
          components={{
            month: {
              dateHeader: MonthDateHeader,
            },
          }}
          dayPropGetter={(date: Date) => {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const d = new Date(date);
            d.setHours(0, 0, 0, 0);

            // Check if this date is highlighted
            const isHighlighted = highlightedDate &&
              d.getTime() === new Date(highlightedDate.getFullYear(), highlightedDate.getMonth(), highlightedDate.getDate()).getTime();

            if (isHighlighted) {
              return {
                className: 'highlighted-date',
                style: {
                  backgroundColor: '#DBEAFE',
                  animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1)',
                },
              };
            }

            if (d.getTime() === today.getTime()) {
              return {
                style: {
                  backgroundColor: '#EFF6FF',
                },
              };
            }
            return {};
          }}
        />
      </div>
    </div>
  );
}
