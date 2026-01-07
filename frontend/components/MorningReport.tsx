'use client';

import { useState, useEffect } from 'react';
import {
  AlertTriangle,
  FileText,
  Calendar,
  ChevronRight,
  Loader2,
  Clock,
  CheckCircle2,
  Briefcase,
  Gavel,
  ArrowRight,
  Zap
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface MorningReportData {
  greeting: string;
  summary: string;
  high_risk_alerts: Array<{
    type: string;
    alert_level: string;
    deadline_id: string;
    case_id: string;
    case_number?: string;
    case_title: string;
    deadline_title: string;
    deadline_date: string;
    days_until?: number;
    days_overdue?: number;
    message: string;
  }>;
  new_filings: Array<{
    document_id: string;
    case_id: string;
    case_title: string;
    document_title: string;
    uploaded_at: string;
  }>;
  upcoming_deadlines: Array<{
    deadline_id: string;
    case_id: string;
    case_number?: string;
    case_title: string;
    deadline_title: string;
    deadline_date: string;
    deadline_date_formatted?: string;
    days_until: number;
    urgency: string;
    priority: string;
  }>;
  actionable_insights: Array<{
    priority: string;
    icon: string;
    title: string;
    message: string;
    action?: string;
    action_type?: string;
    case_id?: string;
    related_items?: string[];
  }>;
  case_overview: {
    total_cases: number;
    cases_needing_attention: number;
    total_pending_deadlines: number;
  };
  week_stats?: {
    completed_this_week: number;
    due_this_week: number;
    day_of_week: string;
  };
  milestones?: Array<{
    type: string;
    case_title: string;
    case_id: string;
    date: string;
    days_until: number;
    title: string;
  }>;
  workload_level?: string;
  generated_at: string;
}

interface MorningReportProps {
  onCaseClick?: (caseId: string) => void;
}

export default function MorningReport({ onCaseClick }: MorningReportProps) {
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<MorningReportData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMorningReport();
  }, []);

  const fetchMorningReport = async () => {
    try {
      const response = await apiClient.get('/api/v1/dashboard/morning-report');
      setReport(response.data);
    } catch (err: any) {
      console.error('Failed to load morning report:', err);
      setError(err.response?.data?.detail || 'Failed to load briefing');
    } finally {
      setLoading(false);
    }
  };

  const getUrgencyStyle = (urgency: string, priority: string) => {
    if (priority === 'fatal') return 'border-l-red-600 bg-red-50';
    switch (urgency) {
      case 'today': return 'border-l-red-500 bg-red-50';
      case 'tomorrow': return 'border-l-orange-500 bg-orange-50';
      case 'soon': return 'border-l-amber-500 bg-amber-50';
      default: return 'border-l-slate-300 bg-slate-50';
    }
  };

  const formatDaysUntil = (days: number) => {
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    return `${days} days`;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-12">
        <div className="flex flex-col items-center justify-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="text-slate-500">Loading your briefing...</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
        <p className="text-slate-500 text-center">Unable to load morning briefing</p>
      </div>
    );
  }

  const hasAlerts = report.high_risk_alerts && report.high_risk_alerts.length > 0;
  const hasUpcoming = report.upcoming_deadlines && report.upcoming_deadlines.length > 0;
  const hasInsights = report.actionable_insights && report.actionable_insights.length > 0;

  return (
    <div className="space-y-6">
      {/* Main Briefing Card */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl shadow-lg overflow-hidden">
        <div className="p-6 md:p-8">
          {/* Greeting */}
          <h1 className="text-2xl md:text-3xl font-semibold text-white mb-3">
            {report.greeting}
          </h1>

          {/* Summary */}
          <p className="text-slate-300 text-lg leading-relaxed max-w-3xl">
            {report.summary}
          </p>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-4 mt-8">
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
              <div className="flex items-center gap-2 mb-1">
                <Briefcase className="w-4 h-4 text-slate-400" />
                <span className="text-xs text-slate-400 uppercase tracking-wide">Cases</span>
              </div>
              <p className="text-2xl font-bold text-white">{report.case_overview.total_cases}</p>
            </div>
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
              <div className="flex items-center gap-2 mb-1">
                <Calendar className="w-4 h-4 text-slate-400" />
                <span className="text-xs text-slate-400 uppercase tracking-wide">Pending</span>
              </div>
              <p className="text-2xl font-bold text-white">{report.case_overview.total_pending_deadlines}</p>
            </div>
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="w-4 h-4 text-slate-400" />
                <span className="text-xs text-slate-400 uppercase tracking-wide">Attention</span>
              </div>
              <p className={`text-2xl font-bold ${report.case_overview.cases_needing_attention > 0 ? 'text-amber-400' : 'text-green-400'}`}>
                {report.case_overview.cases_needing_attention}
              </p>
            </div>
          </div>

          {/* Week Stats (if available) */}
          {report.week_stats && report.week_stats.completed_this_week > 0 && (
            <div className="mt-6 flex items-center gap-2 text-slate-400">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-sm">
                {report.week_stats.completed_this_week} completed this week
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Actionable Insights */}
      {hasInsights && (
        <div className="grid gap-3">
          {report.actionable_insights.map((insight, idx) => (
            <div
              key={idx}
              className={`
                p-4 rounded-lg border-2 flex items-start gap-4 cursor-pointer
                transition-all hover:shadow-md
                ${insight.priority === 'critical' ? 'bg-red-50 border-red-200 hover:border-red-300' : ''}
                ${insight.priority === 'high' ? 'bg-orange-50 border-orange-200 hover:border-orange-300' : ''}
                ${insight.priority === 'medium' ? 'bg-blue-50 border-blue-200 hover:border-blue-300' : ''}
                ${insight.priority === 'low' ? 'bg-slate-50 border-slate-200 hover:border-slate-300' : ''}
              `}
              onClick={() => {
                if (insight.case_id) {
                  onCaseClick?.(insight.case_id);
                }
              }}
            >
              <span className="text-2xl flex-shrink-0">{insight.icon}</span>
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold text-slate-900">{insight.title}</h4>
                <p className="text-sm text-slate-600 mt-0.5">{insight.message}</p>
              </div>
              {insight.action && insight.action_type !== 'info' && (
                <button className="flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900 flex-shrink-0">
                  {insight.action}
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* High-Risk Alerts */}
        {hasAlerts && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              <h3 className="font-semibold text-slate-900">Requires Attention</h3>
              <span className="ml-auto bg-red-100 text-red-700 text-xs font-medium px-2 py-0.5 rounded-full">
                {report.high_risk_alerts.length}
              </span>
            </div>
            <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
              {report.high_risk_alerts.map((alert, idx) => (
                <div
                  key={idx}
                  className="px-5 py-4 hover:bg-slate-50 cursor-pointer transition-colors"
                  onClick={() => onCaseClick?.(alert.case_id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-slate-900 truncate">{alert.deadline_title}</p>
                      <p className="text-sm text-slate-500 truncate mt-0.5">{alert.case_title}</p>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <span className={`
                        inline-block px-2 py-0.5 rounded text-xs font-semibold
                        ${alert.alert_level === 'OVERDUE' ? 'bg-red-100 text-red-700' : ''}
                        ${alert.alert_level === 'URGENT' ? 'bg-orange-100 text-orange-700' : ''}
                        ${alert.alert_level === 'CRITICAL' ? 'bg-red-100 text-red-700' : ''}
                      `}>
                        {alert.message}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upcoming Deadlines */}
        {hasUpcoming && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-slate-900">This Week</h3>
              <span className="ml-auto bg-blue-100 text-blue-700 text-xs font-medium px-2 py-0.5 rounded-full">
                {report.upcoming_deadlines.length}
              </span>
            </div>
            <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
              {report.upcoming_deadlines.map((deadline, idx) => (
                <div
                  key={idx}
                  className={`
                    px-5 py-3 hover:bg-slate-50 cursor-pointer transition-colors
                    border-l-4 ${getUrgencyStyle(deadline.urgency, deadline.priority)}
                  `}
                  onClick={() => onCaseClick?.(deadline.case_id)}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-slate-900 truncate text-sm">{deadline.deadline_title}</p>
                      <p className="text-xs text-slate-500 truncate">{deadline.case_title}</p>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="text-sm font-semibold text-slate-700">
                        {deadline.deadline_date_formatted || new Date(deadline.deadline_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </p>
                      <p className={`text-xs ${deadline.days_until <= 1 ? 'text-red-600 font-medium' : 'text-slate-500'}`}>
                        {formatDaysUntil(deadline.days_until)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Milestones */}
      {report.milestones && report.milestones.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
            <Gavel className="w-5 h-5 text-purple-500" />
            <h3 className="font-semibold text-slate-900">Upcoming Milestones</h3>
          </div>
          <div className="p-4 grid gap-3">
            {report.milestones.map((milestone, idx) => (
              <div
                key={idx}
                className="flex items-center gap-4 p-3 bg-purple-50 border border-purple-100 rounded-lg cursor-pointer hover:bg-purple-100 transition-colors"
                onClick={() => onCaseClick?.(milestone.case_id)}
              >
                <div className="flex-shrink-0 w-12 h-12 bg-purple-100 rounded-lg flex flex-col items-center justify-center">
                  <span className="text-xs text-purple-600 font-medium uppercase">
                    {new Date(milestone.date).toLocaleDateString('en-US', { month: 'short' })}
                  </span>
                  <span className="text-lg font-bold text-purple-700">
                    {new Date(milestone.date).getDate()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900">{milestone.type.charAt(0).toUpperCase() + milestone.type.slice(1)}</p>
                  <p className="text-sm text-slate-600 truncate">{milestone.case_title}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <span className="text-sm font-medium text-purple-700">{milestone.days_until} days</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* New Filings */}
      {report.new_filings && report.new_filings.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
            <FileText className="w-5 h-5 text-emerald-500" />
            <h3 className="font-semibold text-slate-900">New Documents</h3>
            <span className="ml-auto bg-emerald-100 text-emerald-700 text-xs font-medium px-2 py-0.5 rounded-full">
              {report.new_filings.length}
            </span>
          </div>
          <div className="divide-y divide-slate-100 max-h-60 overflow-y-auto">
            {report.new_filings.map((filing, idx) => (
              <div
                key={idx}
                className="px-5 py-3 hover:bg-slate-50 cursor-pointer transition-colors flex items-center gap-3"
                onClick={() => onCaseClick?.(filing.case_id)}
              >
                <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{filing.document_title}</p>
                  <p className="text-xs text-slate-500 truncate">{filing.case_title}</p>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!hasAlerts && !hasUpcoming && report.case_overview.total_cases === 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-12 text-center">
          <Briefcase className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No Active Cases</h3>
          <p className="text-slate-500">Get started by adding your first case.</p>
        </div>
      )}
    </div>
  );
}
