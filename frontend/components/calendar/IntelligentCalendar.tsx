'use client';

import React, { useState, useEffect } from 'react';
import { Calendar as CalendarIcon, AlertTriangle, Sparkles, ChevronLeft, ChevronRight } from 'lucide-react';
import apiClient from '@/lib/api-client';
import { eventBus } from '@/lib/eventBus';

interface Deadline {
  id: string;
  title: string;
  deadline_date: string;
  priority: 'FATAL' | 'CRITICAL' | 'IMPORTANT' | 'STANDARD' | 'INFORMATIONAL';
  status: string;
  case_id: string;
  case_number?: string;
  is_dependent: boolean;
  is_trigger: boolean;
}

interface DayData {
  date: string;
  deadlines: Deadline[];
  risk_score: number;
  intensity: 'low' | 'medium' | 'high' | 'very_high' | 'extreme';
}

interface AISuggestion {
  date: string;
  risk_score: number;
  ai_recommendations: Array<{
    deadline_title: string;
    deadline_id?: string;
    move_to_date: string;
    reason: string;
  }>;
  summary: string;
}

interface IntelligentCalendarProps {
  userId?: string;
  showAISuggestions?: boolean;
}

export default function IntelligentCalendar({ userId, showAISuggestions = true }: IntelligentCalendarProps) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [calendarData, setCalendarData] = useState<Map<string, DayData>>(new Map());
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggedDeadline, setDraggedDeadline] = useState<Deadline | null>(null);
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);

  useEffect(() => {
    fetchCalendarData();

    // Listen for deadline changes
    const handleDeadlineChange = () => {
      fetchCalendarData();
    };

    eventBus.on('deadline:created', handleDeadlineChange);
    eventBus.on('deadline:updated', handleDeadlineChange);
    eventBus.on('deadline:deleted', handleDeadlineChange);

    return () => {
      eventBus.off('deadline:created', handleDeadlineChange);
      eventBus.off('deadline:updated', handleDeadlineChange);
      eventBus.off('deadline:deleted', handleDeadlineChange);
    };
  }, [currentDate]);

  const fetchCalendarData = async () => {
    setLoading(true);
    try {
      // Fetch deadlines for the month
      const startOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
      const endOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);

      const deadlinesResponse = await apiClient.get('/api/v1/deadlines', {
        params: {
          start_date: startOfMonth.toISOString().split('T')[0],
          end_date: endOfMonth.toISOString().split('T')[0],
          status: 'pending'
        }
      });

      // Fetch workload analysis
      const workloadResponse = await apiClient.get('/api/v1/workload/analysis', {
        params: { days_ahead: 60 }
      });

      // Organize deadlines by date
      const dataMap = new Map<string, DayData>();
      const deadlines = deadlinesResponse.data.data || deadlinesResponse.data || [];

      deadlines.forEach((deadline: Deadline) => {
        if (!deadline.deadline_date) return;

        const dateKey = deadline.deadline_date.split('T')[0];
        if (!dataMap.has(dateKey)) {
          const heatmapData = workloadResponse.data.data.workload_heatmap[dateKey] || {
            risk_score: 0,
            deadline_count: 0,
            intensity: 'low'
          };

          dataMap.set(dateKey, {
            date: dateKey,
            deadlines: [],
            risk_score: heatmapData.risk_score,
            intensity: heatmapData.intensity
          });
        }

        dataMap.get(dateKey)!.deadlines.push(deadline);
      });

      setCalendarData(dataMap);

      if (showAISuggestions) {
        setAiSuggestions(workloadResponse.data.data.ai_suggestions || []);
      }
    } catch (error) {
      console.error('Failed to fetch calendar data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDragStart = (deadline: Deadline, e: React.DragEvent) => {
    setDraggedDeadline(deadline);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (date: string, e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setHoveredDate(date);
  };

  const handleDragLeave = () => {
    setHoveredDate(null);
  };

  const handleDrop = async (newDate: string, e: React.DragEvent) => {
    e.preventDefault();
    setHoveredDate(null);

    if (!draggedDeadline) return;

    // Check if it's a trigger deadline
    const isTrigger = draggedDeadline.is_trigger || draggedDeadline.is_dependent;

    if (isTrigger) {
      const confirmed = window.confirm(
        `This deadline is ${draggedDeadline.is_trigger ? 'a trigger' : 'part of a trigger chain'}. ` +
        `Moving it will ${draggedDeadline.is_trigger ? 'cascade-update all dependent deadlines' : 'may affect other deadlines'}. Continue?`
      );

      if (!confirmed) {
        setDraggedDeadline(null);
        return;
      }
    }

    try {
      await apiClient.put(`/deadlines/${draggedDeadline.id}`, {
        deadline_date: newDate,
        cascade_update: draggedDeadline.is_trigger
      });

      // Refresh calendar
      await fetchCalendarData();

      // Emit event
      eventBus.emit('deadline:updated', { id: draggedDeadline.id });

      // Show success message
      showToast(`Deadline moved to ${new Date(newDate).toLocaleDateString()}`, 'success');
    } catch (error) {
      console.error('Failed to move deadline:', error);
      showToast('Failed to move deadline', 'error');
    } finally {
      setDraggedDeadline(null);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'FATAL':
        return 'bg-red-600 border-red-700';
      case 'CRITICAL':
        return 'bg-orange-500 border-orange-600';
      case 'IMPORTANT':
        return 'bg-yellow-500 border-yellow-600';
      case 'STANDARD':
        return 'bg-blue-500 border-blue-600';
      default:
        return 'bg-gray-400 border-gray-500';
    }
  };

  const getIntensityColor = (intensity: string) => {
    switch (intensity) {
      case 'extreme':
        return 'bg-red-100 border-red-300';
      case 'very_high':
        return 'bg-red-50 border-red-200';
      case 'high':
        return 'bg-orange-50 border-orange-200';
      case 'medium':
        return 'bg-yellow-50 border-yellow-200';
      case 'low':
        return 'bg-green-50 border-green-200';
      default:
        return 'bg-white border-gray-200';
    }
  };

  const generateCalendarDays = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startPadding = firstDay.getDay();
    const totalDays = lastDay.getDate();

    const days = [];

    // Add padding for first week
    for (let i = 0; i < startPadding; i++) {
      days.push(null);
    }

    // Add actual days
    for (let day = 1; day <= totalDays; day++) {
      const date = new Date(year, month, day);
      const dateString = date.toISOString().split('T')[0];
      const dayData = calendarData.get(dateString);

      days.push({
        date: dateString,
        dayOfMonth: day,
        dayData: dayData || {
          date: dateString,
          deadlines: [],
          risk_score: 0,
          intensity: 'low' as const
        },
        isToday: dateString === new Date().toISOString().split('T')[0],
        isPast: date < new Date()
      });
    }

    return days;
  };

  const changeMonth = (offset: number) => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + offset, 1));
  };

  const days = generateCalendarDays();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <CalendarIcon className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Intelligent Calendar</h2>
            <p className="text-sm text-gray-600">
              Drag deadlines to reschedule • Color intensity = workload risk
            </p>
          </div>
        </div>

        {/* Month Navigation */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => changeMonth(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h3 className="text-lg font-semibold min-w-[200px] text-center">
            {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
          </h3>
          <button
            onClick={() => changeMonth(1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* AI Suggestions Banner */}
      {showAISuggestions && aiSuggestions.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-medium text-purple-900 mb-2">
                AI found {aiSuggestions.length} high-risk day{aiSuggestions.length > 1 ? 's' : ''} that could be rebalanced
              </p>
              <div className="space-y-2">
                {aiSuggestions.slice(0, 2).map((suggestion, i) => (
                  <div key={i} className="text-sm text-purple-700">
                    <span className="font-medium">{new Date(suggestion.date).toLocaleDateString()}:</span> {suggestion.summary}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Calendar Grid */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* Day Headers */}
        <div className="grid grid-cols-7 gap-px bg-gray-200">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="bg-gray-50 py-2 text-center text-sm font-semibold text-gray-700">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Days */}
        <div className="grid grid-cols-7 gap-px bg-gray-200">
          {days.map((day, index) => {
            if (!day) {
              return <div key={`empty-${index}`} className="bg-white min-h-[120px]"></div>;
            }

            const isHovered = hoveredDate === day.date;

            return (
              <div
                key={day.date}
                className={`
                  bg-white min-h-[120px] p-2 transition-all
                  ${getIntensityColor(day.dayData.intensity)}
                  ${day.isToday ? 'ring-2 ring-blue-500' : ''}
                  ${day.isPast ? 'opacity-60' : ''}
                  ${isHovered ? 'ring-2 ring-purple-500 scale-[1.02]' : ''}
                `}
                onDragOver={(e) => handleDragOver(day.date, e)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(day.date, e)}
              >
                {/* Day Number */}
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm font-semibold ${day.isToday ? 'text-blue-600' : 'text-gray-700'}`}>
                    {day.dayOfMonth}
                  </span>
                  {day.dayData.deadlines.length > 0 && (
                    <span className="text-xs font-medium text-gray-500">
                      {day.dayData.deadlines.length}
                    </span>
                  )}
                </div>

                {/* Deadlines */}
                <div className="space-y-1">
                  {day.dayData.deadlines.slice(0, 3).map(deadline => (
                    <div
                      key={deadline.id}
                      draggable
                      onDragStart={(e) => handleDragStart(deadline, e)}
                      className={`
                        text-xs px-2 py-1 rounded cursor-move
                        ${getPriorityColor(deadline.priority)}
                        text-white truncate
                        hover:opacity-80 transition-opacity
                      `}
                      title={`${deadline.title} (${deadline.priority})`}
                    >
                      {deadline.title}
                    </div>
                  ))}

                  {day.dayData.deadlines.length > 3 && (
                    <div className="text-xs text-gray-500 px-2">
                      +{day.dayData.deadlines.length - 3} more
                    </div>
                  )}
                </div>

                {/* Risk Warning */}
                {day.dayData.intensity === 'extreme' && (
                  <div className="mt-2">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-600 rounded"></div>
          <span className="text-gray-600">FATAL</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-orange-500 rounded"></div>
          <span className="text-gray-600">CRITICAL</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-yellow-500 rounded"></div>
          <span className="text-gray-600">IMPORTANT</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 rounded"></div>
          <span className="text-gray-600">STANDARD</span>
        </div>
        <div className="ml-auto text-xs text-gray-500">
          Background color intensity = workload risk
        </div>
      </div>
    </div>
  );
}

// Simple toast notification helper
function showToast(message: string, type: 'success' | 'error') {
  // For now, use browser alert as fallback for errors
  if (type === 'error') {
    alert(message);
  }
}
