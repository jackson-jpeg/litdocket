'use client';

import { useState, useEffect, useMemo } from 'react';
import { apiClient } from '@/lib/api-client';
import {
  FileText,
  Calendar,
  Clock,
  Users,
  Scale,
  AlertTriangle,
  CheckCircle,
  Circle,
  ChevronDown,
  ChevronUp,
  Filter,
} from 'lucide-react';

interface TimelineEvent {
  id: string;
  type: string;
  subtype: string | null;
  title: string;
  description: string | null;
  date: string;
  end_date: string | null;
  status: string;
  priority: string;
  location: string | null;
  participants: Array<{ name: string; role: string }>;
}

const EVENT_ICONS: Record<string, typeof FileText> = {
  filing: FileText,
  deadline: Clock,
  hearing: Scale,
  discovery: FileText,
  deposition: Users,
  mediation: Users,
  trial: Scale,
  ruling: Scale,
  milestone: CheckCircle,
  custom: Circle,
};

const EVENT_COLORS: Record<string, string> = {
  filing: 'bg-blue-500',
  deadline: 'bg-red-500',
  hearing: 'bg-purple-500',
  discovery: 'bg-green-500',
  deposition: 'bg-yellow-500',
  mediation: 'bg-orange-500',
  trial: 'bg-indigo-500',
  ruling: 'bg-pink-500',
  milestone: 'bg-teal-500',
  custom: 'bg-gray-500',
};

const STATUS_STYLES: Record<string, string> = {
  scheduled: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  cancelled: 'bg-gray-100 text-gray-800',
  pending: 'bg-yellow-100 text-yellow-800',
  overdue: 'bg-red-100 text-red-800',
};

const PRIORITY_STYLES: Record<string, string> = {
  critical: 'border-l-red-500',
  high: 'border-l-orange-500',
  standard: 'border-l-blue-500',
  low: 'border-l-gray-400',
};

interface CaseTimelineProps {
  caseId: string;
  className?: string;
}

export default function CaseTimeline({ caseId, className = '' }: CaseTimelineProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [filterTypes, setFilterTypes] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchTimeline();
  }, [caseId]);

  const fetchTimeline = async () => {
    try {
      const response = await apiClient.get(`/api/v1/case-intelligence/cases/${caseId}/timeline`);
      setEvents(response.data || []);
    } catch (error) {
      console.error('Failed to fetch timeline:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleEvent = (eventId: string) => {
    setExpandedEvents((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(eventId)) {
        newSet.delete(eventId);
      } else {
        newSet.add(eventId);
      }
      return newSet;
    });
  };

  const toggleFilter = (type: string) => {
    setFilterTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const eventTypes = useMemo(() => {
    const types = new Set(events.map((e) => e.type));
    return Array.from(types);
  }, [events]);

  const filteredEvents = useMemo(() => {
    if (filterTypes.length === 0) return events;
    return events.filter((e) => filterTypes.includes(e.type));
  }, [events, filterTypes]);

  // Group events by date
  const groupedEvents = useMemo(() => {
    const groups: Record<string, TimelineEvent[]> = {};
    filteredEvents.forEach((event) => {
      const date = new Date(event.date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
      if (!groups[date]) groups[date] = [];
      groups[date].push(event);
    });
    return groups;
  }, [filteredEvents]);

  const today = new Date().toDateString();

  if (loading) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Filters */}
      <div className="mb-4">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <Filter className="w-4 h-4" />
          Filter Events
          {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showFilters && (
          <div className="mt-2 flex flex-wrap gap-2">
            {eventTypes.map((type) => (
              <button
                key={type}
                onClick={() => toggleFilter(type)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  filterTypes.length === 0 || filterTypes.includes(type)
                    ? `${EVENT_COLORS[type] || 'bg-gray-500'} text-white`
                    : 'bg-gray-200 text-gray-600'
                }`}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Timeline */}
      {Object.keys(groupedEvents).length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Calendar className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>No events on the timeline</p>
          <p className="text-sm mt-1">Events from deadlines and case activities will appear here</p>
        </div>
      ) : (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200"></div>

          <div className="space-y-8">
            {Object.entries(groupedEvents).map(([date, dateEvents]) => {
              const isToday = new Date(dateEvents[0].date).toDateString() === today;
              const isPast = new Date(dateEvents[0].date) < new Date();

              return (
                <div key={date} className="relative">
                  {/* Date marker */}
                  <div className="flex items-center gap-3 mb-4">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center z-10 ${
                        isToday
                          ? 'bg-blue-600 text-white'
                          : isPast
                          ? 'bg-gray-400 text-white'
                          : 'bg-white border-2 border-gray-300 text-gray-600'
                      }`}
                    >
                      <Calendar className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{date}</h3>
                      {isToday && (
                        <span className="text-xs text-blue-600 font-medium">Today</span>
                      )}
                    </div>
                  </div>

                  {/* Events for this date */}
                  <div className="ml-12 space-y-3">
                    {dateEvents.map((event) => {
                      const IconComponent = EVENT_ICONS[event.type] || Circle;
                      const isExpanded = expandedEvents.has(event.id);

                      return (
                        <div
                          key={event.id}
                          className={`bg-white rounded-lg border shadow-sm overflow-hidden border-l-4 ${
                            PRIORITY_STYLES[event.priority] || PRIORITY_STYLES.standard
                          }`}
                        >
                          <button
                            onClick={() => toggleEvent(event.id)}
                            className="w-full p-4 text-left hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex items-start gap-3">
                              <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                  EVENT_COLORS[event.type] || 'bg-gray-500'
                                } text-white flex-shrink-0`}
                              >
                                <IconComponent className="w-4 h-4" />
                              </div>

                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <h4 className="font-medium text-gray-900">{event.title}</h4>
                                  <span
                                    className={`px-2 py-0.5 rounded-full text-xs ${
                                      STATUS_STYLES[event.status] || STATUS_STYLES.pending
                                    }`}
                                  >
                                    {event.status}
                                  </span>
                                </div>

                                <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                                  <span className="capitalize">{event.type}</span>
                                  {event.subtype && (
                                    <>
                                      <span>•</span>
                                      <span className="capitalize">{event.subtype}</span>
                                    </>
                                  )}
                                  {event.location && (
                                    <>
                                      <span>•</span>
                                      <span>{event.location}</span>
                                    </>
                                  )}
                                </div>
                              </div>

                              {isExpanded ? (
                                <ChevronUp className="w-5 h-5 text-gray-400" />
                              ) : (
                                <ChevronDown className="w-5 h-5 text-gray-400" />
                              )}
                            </div>
                          </button>

                          {isExpanded && (
                            <div className="px-4 pb-4 pt-2 border-t bg-gray-50">
                              {event.description && (
                                <p className="text-sm text-gray-600 mb-3">{event.description}</p>
                              )}

                              {event.participants && event.participants.length > 0 && (
                                <div className="mb-3">
                                  <h5 className="text-xs font-medium text-gray-500 mb-1">
                                    Participants
                                  </h5>
                                  <div className="flex flex-wrap gap-2">
                                    {event.participants.map((p, i) => (
                                      <span
                                        key={i}
                                        className="px-2 py-1 bg-white rounded text-xs text-gray-700 border"
                                      >
                                        {p.name} ({p.role})
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              <div className="text-xs text-gray-500">
                                {new Date(event.date).toLocaleTimeString('en-US', {
                                  hour: 'numeric',
                                  minute: '2-digit',
                                })}
                                {event.end_date &&
                                  ` - ${new Date(event.end_date).toLocaleTimeString('en-US', {
                                    hour: 'numeric',
                                    minute: '2-digit',
                                  })}`}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
