'use client';

import React, { useEffect, useState } from 'react';
import { Calendar, AlertTriangle, TrendingUp, Lightbulb } from 'lucide-react';
import apiClient from '@/lib/api-client';

interface HeatmapDay {
  risk_score: number;
  deadline_count: number;
  intensity: 'low' | 'medium' | 'high' | 'very_high' | 'extreme';
}

interface WorkloadStats {
  average_deadlines_per_day: number;
  peak_workload_day: {
    date: string;
    deadline_count: number;
  } | null;
  saturated_days_count: number;
  total_deadlines: number;
  analysis_period_days: number;
}

interface BurnoutAlert {
  type: string;
  start_date: string;
  end_date: string;
  consecutive_days: number;
  message: string;
  severity: string;
}

interface AISuggestion {
  date: string;
  risk_score: number;
  ai_recommendations: Array<{
    deadline_title: string;
    move_to_date: string;
    reason: string;
  }>;
  summary: string;
}

interface WorkloadHeatmapProps {
  userId?: string;
  daysAhead?: number;
}

export default function WorkloadHeatmap({ userId, daysAhead = 60 }: WorkloadHeatmapProps) {
  const [heatmap, setHeatmap] = useState<Record<string, HeatmapDay>>({});
  const [stats, setStats] = useState<WorkloadStats | null>(null);
  const [burnoutAlerts, setBurnoutAlerts] = useState<BurnoutAlert[]>([]);
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    fetchWorkloadAnalysis();
  }, [daysAhead]);

  const fetchWorkloadAnalysis = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/workload/analysis?days_ahead=${daysAhead}`);
      if (response.data.success) {
        setHeatmap(response.data.data.workload_heatmap);
        setStats(response.data.data.statistics);
        setBurnoutAlerts(response.data.data.burnout_alerts);
        setAiSuggestions(response.data.data.ai_suggestions);
      }
    } catch (error) {
      console.error('Failed to fetch workload analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const getIntensityColor = (intensity: string) => {
    switch (intensity) {
      case 'extreme':
        return 'bg-red-600';
      case 'very_high':
        return 'bg-red-400';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-yellow-400';
      case 'low':
        return 'bg-green-200';
      default:
        return 'bg-gray-100';
    }
  };

  const generateCalendarGrid = () => {
    const today = new Date();
    const days = [];

    for (let i = 0; i < daysAhead; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      const dateString = date.toISOString().split('T')[0];

      const dayData = heatmap[dateString] || {
        risk_score: 0,
        deadline_count: 0,
        intensity: 'low' as const
      };

      days.push({
        date: dateString,
        dayOfWeek: date.getDay(),
        dayOfMonth: date.getDate(),
        ...dayData
      });
    }

    return days;
  };

  const calendarDays = generateCalendarGrid();

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
          <div className="p-2 bg-purple-100 rounded-lg">
            <TrendingUp className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Workload Analysis</h2>
            <p className="text-sm text-gray-600">
              Visual intensity map for the next {daysAhead} days
            </p>
          </div>
        </div>

        {aiSuggestions.length > 0 && (
          <button
            onClick={() => setShowSuggestions(!showSuggestions)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <Lightbulb className="w-4 h-4" />
            {showSuggestions ? 'Hide' : 'View'} AI Suggestions ({aiSuggestions.length})
          </button>
        )}
      </div>

      {/* Burnout Alerts */}
      {burnoutAlerts.length > 0 && (
        <div className="space-y-2">
          {burnoutAlerts.map((alert, i) => (
            <div key={i} className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium text-red-900">Burnout Risk Detected</p>
                <p className="text-sm text-red-700">{alert.message}</p>
                <p className="text-xs text-red-600 mt-1">
                  {new Date(alert.start_date).toLocaleDateString()} - {new Date(alert.end_date).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-600">Total Deadlines</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total_deadlines}</p>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-600">Avg Per Day</p>
            <p className="text-2xl font-bold text-gray-900">{stats.average_deadlines_per_day.toFixed(1)}</p>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-600">High-Risk Days</p>
            <p className="text-2xl font-bold text-orange-600">{stats.saturated_days_count}</p>
          </div>

          {stats.peak_workload_day && (
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-600">Peak Day</p>
              <p className="text-lg font-bold text-red-600">{stats.peak_workload_day.deadline_count} deadlines</p>
              <p className="text-xs text-gray-500">{new Date(stats.peak_workload_day.date).toLocaleDateString()}</p>
            </div>
          )}
        </div>
      )}

      {/* Heatmap Grid */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="mb-4">
          <h3 className="font-semibold text-gray-900 mb-2">Workload Intensity Calendar</h3>
          <div className="flex items-center gap-4 text-xs text-gray-600">
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-200 rounded"></div>
              Low
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 bg-yellow-400 rounded"></div>
              Medium
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 bg-orange-500 rounded"></div>
              High
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-400 rounded"></div>
              Very High
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-600 rounded"></div>
              Extreme
            </span>
          </div>
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-2">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="text-xs font-medium text-gray-500 text-center py-1">
              {day}
            </div>
          ))}

          {/* Add empty cells for first week alignment */}
          {Array.from({ length: calendarDays[0]?.dayOfWeek || 0 }).map((_, i) => (
            <div key={`empty-${i}`} className="aspect-square"></div>
          ))}

          {/* Calendar days */}
          {calendarDays.map((day) => (
            <div
              key={day.date}
              className={`
                aspect-square rounded-lg p-2 cursor-pointer transition-all hover:scale-110
                ${getIntensityColor(day.intensity)}
                ${day.deadline_count === 0 ? 'opacity-20' : ''}
              `}
              title={`${new Date(day.date).toLocaleDateString()}: ${day.deadline_count} deadline(s), Risk: ${day.risk_score.toFixed(1)}`}
            >
              <div className="flex flex-col items-center justify-center h-full text-white">
                <div className="text-xs font-semibold">{day.dayOfMonth}</div>
                {day.deadline_count > 0 && (
                  <div className="text-[10px] font-bold">{day.deadline_count}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AI Suggestions Panel */}
      {showSuggestions && aiSuggestions.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 space-y-4">
          <h3 className="font-semibold text-purple-900 flex items-center gap-2">
            <Lightbulb className="w-5 h-5" />
            AI Rebalancing Suggestions
          </h3>

          {aiSuggestions.map((suggestion, i) => (
            <div key={i} className="bg-white p-4 rounded-lg border border-purple-200">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">
                  {new Date(suggestion.date).toLocaleDateString()}
                </h4>
                <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                  Risk: {suggestion.risk_score.toFixed(1)}
                </span>
              </div>

              <p className="text-sm text-gray-700 mb-3">{suggestion.summary}</p>

              {suggestion.ai_recommendations && suggestion.ai_recommendations.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-gray-600">Recommendations:</p>
                  {suggestion.ai_recommendations.map((rec, j) => (
                    <div key={j} className="bg-purple-50 p-3 rounded text-sm">
                      <p className="font-medium text-purple-900">
                        Move: {rec.deadline_title}
                      </p>
                      <p className="text-purple-700">
                        To: {new Date(rec.move_to_date).toLocaleDateString()}
                      </p>
                      <p className="text-xs text-purple-600 mt-1">{rec.reason}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
