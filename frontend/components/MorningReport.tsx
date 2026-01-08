'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, Clock, ChevronRight, Loader2 } from 'lucide-react';
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
    priority?: string;
    message: string;
  }>;
  new_filings: Array<{
    document_id: string;
    case_id: string;
    case_title: string;
    document_title: string;
    document_type?: string;
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

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric'
    });
  };

  const formatShortDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getPriorityDisplay = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'fatal': return { label: 'FATAL', class: 'bg-red-700 text-white' };
      case 'critical': return { label: 'CRITICAL', class: 'bg-red-600 text-white' };
      case 'high': return { label: 'HIGH', class: 'bg-orange-600 text-white' };
      case 'medium': return { label: 'MEDIUM', class: 'bg-yellow-500 text-black' };
      default: return { label: 'STANDARD', class: 'bg-gray-500 text-white' };
    }
  };

  const getAlertStatus = (alert: any) => {
    if (alert.alert_level === 'OVERDUE') {
      return { label: `${alert.days_overdue || Math.abs(alert.days_until)}d OVERDUE`, class: 'text-red-700 font-bold' };
    }
    if (alert.days_until === 0) return { label: 'DUE TODAY', class: 'text-red-600 font-bold' };
    if (alert.days_until === 1) return { label: 'DUE TOMORROW', class: 'text-orange-600 font-semibold' };
    if (alert.days_until <= 3) return { label: `${alert.days_until}d`, class: 'text-orange-600' };
    return { label: `${alert.days_until}d`, class: 'text-gray-600' };
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-300 p-8">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 text-[#0f62fe] animate-spin" />
          <span className="text-gray-600 text-sm">Loading intelligence briefing...</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="bg-white border border-gray-300 p-6">
        <p className="text-gray-600 text-sm text-center">Unable to load briefing data</p>
      </div>
    );
  }

  const today = new Date();
  const dateStr = today.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div className="space-y-4">
      {/* Header Bar */}
      <div className="bg-[#001d6c] text-white px-5 py-4">
        <div className="flex items-baseline justify-between">
          <div>
            <h1 className="font-serif text-2xl font-normal tracking-tight">
              Daily Intelligence Briefing
            </h1>
            <p className="text-blue-200 text-sm mt-1">{dateStr}</p>
          </div>
          <div className="text-right text-sm">
            <p className="text-blue-200">Report Generated</p>
            <p className="font-mono text-xs">{new Date(report.generated_at).toLocaleTimeString()}</p>
          </div>
        </div>
      </div>

      {/* Summary Panel */}
      <div className="bg-white border border-gray-300">
        <div className="bg-gray-100 px-4 py-2 border-b border-gray-300">
          <h2 className="font-serif text-sm font-semibold text-gray-800 uppercase tracking-wide">
            Executive Summary
          </h2>
        </div>
        <div className="p-4">
          <p className="text-gray-800 leading-relaxed">{report.summary}</p>

          {/* Stats Row */}
          <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-200">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Active Cases</p>
              <p className="font-mono text-2xl font-semibold text-gray-900">{report.case_overview.total_cases}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Pending Deadlines</p>
              <p className="font-mono text-2xl font-semibold text-gray-900">{report.case_overview.total_pending_deadlines}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Requiring Attention</p>
              <p className={`font-mono text-2xl font-semibold ${report.case_overview.cases_needing_attention > 0 ? 'text-red-700' : 'text-green-700'}`}>
                {report.case_overview.cases_needing_attention}
              </p>
            </div>
            {report.week_stats && (
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">Completed This Week</p>
                <p className="font-mono text-2xl font-semibold text-green-700">{report.week_stats.completed_this_week}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Critical Alerts Table */}
      {report.high_risk_alerts && report.high_risk_alerts.length > 0 && (
        <div className="bg-white border border-gray-300">
          <div className="bg-red-50 px-4 py-2 border-b border-gray-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-700" />
            <h2 className="font-serif text-sm font-semibold text-red-900 uppercase tracking-wide">
              Critical Alerts ({report.high_risk_alerts.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100 border-b border-gray-300">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider w-20">Status</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider w-20">Priority</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider">Deadline</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider">Case</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider w-28">Due Date</th>
                  <th className="w-8"></th>
                </tr>
              </thead>
              <tbody>
                {report.high_risk_alerts.map((alert, idx) => {
                  const status = getAlertStatus(alert);
                  const priority = getPriorityDisplay(alert.priority || 'fatal');
                  return (
                    <tr
                      key={idx}
                      className="border-b border-gray-200 hover:bg-blue-50 cursor-pointer transition-colors"
                      onClick={() => onCaseClick?.(alert.case_id)}
                    >
                      <td className="px-3 py-2">
                        <span className={`text-xs font-mono ${status.class}`}>{status.label}</span>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`text-xs px-1.5 py-0.5 ${priority.class}`}>{priority.label}</span>
                      </td>
                      <td className="px-3 py-2 text-gray-900 font-medium">{alert.deadline_title}</td>
                      <td className="px-3 py-2 text-gray-600">{alert.case_title}</td>
                      <td className="px-3 py-2 font-mono text-xs text-gray-700">
                        {alert.deadline_date ? formatDate(alert.deadline_date) : '—'}
                      </td>
                      <td className="px-2">
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Upcoming Deadlines */}
        {report.upcoming_deadlines && report.upcoming_deadlines.length > 0 && (
          <div className="bg-white border border-gray-300">
            <div className="bg-gray-100 px-4 py-2 border-b border-gray-300 flex items-center gap-2">
              <Clock className="w-4 h-4 text-[#0f62fe]" />
              <h2 className="font-serif text-sm font-semibold text-gray-800 uppercase tracking-wide">
                7-Day Outlook ({report.upcoming_deadlines.length})
              </h2>
            </div>
            <div className="divide-y divide-gray-200 max-h-80 overflow-y-auto">
              {report.upcoming_deadlines.map((deadline, idx) => {
                const priority = getPriorityDisplay(deadline.priority);
                return (
                  <div
                    key={idx}
                    className="px-3 py-2 hover:bg-blue-50 cursor-pointer transition-colors flex items-center gap-3"
                    onClick={() => onCaseClick?.(deadline.case_id)}
                  >
                    <div className="flex-shrink-0 w-16 text-center">
                      <p className="font-mono text-sm font-bold text-gray-900">
                        {formatShortDate(deadline.deadline_date)}
                      </p>
                      <p className={`text-xs ${deadline.days_until <= 1 ? 'text-red-600 font-semibold' : 'text-gray-500'}`}>
                        {deadline.days_until === 0 ? 'Today' : deadline.days_until === 1 ? 'Tomorrow' : `${deadline.days_until}d`}
                      </p>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 truncate">{deadline.deadline_title}</p>
                      <p className="text-xs text-gray-500 truncate">{deadline.case_title}</p>
                    </div>
                    <span className={`text-xs px-1.5 py-0.5 flex-shrink-0 ${priority.class}`}>
                      {priority.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Milestones */}
        {report.milestones && report.milestones.length > 0 && (
          <div className="bg-white border border-gray-300">
            <div className="bg-gray-100 px-4 py-2 border-b border-gray-300">
              <h2 className="font-serif text-sm font-semibold text-gray-800 uppercase tracking-wide">
                Upcoming Proceedings
              </h2>
            </div>
            <div className="divide-y divide-gray-200">
              {report.milestones.map((milestone, idx) => (
                <div
                  key={idx}
                  className="px-3 py-2 hover:bg-blue-50 cursor-pointer transition-colors flex items-center gap-3"
                  onClick={() => onCaseClick?.(milestone.case_id)}
                >
                  <div className="flex-shrink-0 w-16 text-center border-r border-gray-200 pr-3">
                    <p className="text-xs text-gray-500 uppercase">
                      {new Date(milestone.date).toLocaleDateString('en-US', { month: 'short' })}
                    </p>
                    <p className="font-mono text-xl font-bold text-gray-900">
                      {new Date(milestone.date).getDate()}
                    </p>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                      {milestone.type}
                    </p>
                    <p className="text-xs text-gray-600 truncate">{milestone.case_title}</p>
                  </div>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {milestone.days_until}d
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* New Documents */}
      {report.new_filings && report.new_filings.length > 0 && (
        <div className="bg-white border border-gray-300">
          <div className="bg-gray-100 px-4 py-2 border-b border-gray-300">
            <h2 className="font-serif text-sm font-semibold text-gray-800 uppercase tracking-wide">
              Recent Document Activity ({report.new_filings.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider">Document</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider">Type</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider">Case</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider w-36">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {report.new_filings.slice(0, 5).map((filing, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-gray-200 hover:bg-blue-50 cursor-pointer transition-colors"
                    onClick={() => onCaseClick?.(filing.case_id)}
                  >
                    <td className="px-3 py-2 text-gray-900">{filing.document_title}</td>
                    <td className="px-3 py-2 text-gray-600 text-xs uppercase">{filing.document_type || '—'}</td>
                    <td className="px-3 py-2 text-gray-600">{filing.case_title}</td>
                    <td className="px-3 py-2 font-mono text-xs text-gray-500">
                      {new Date(filing.uploaded_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Actionable Items */}
      {report.actionable_insights && report.actionable_insights.length > 0 && (
        <div className="bg-white border border-gray-300">
          <div className="bg-[#e8f1ff] px-4 py-2 border-b border-gray-300">
            <h2 className="font-serif text-sm font-semibold text-[#001d6c] uppercase tracking-wide">
              Recommended Actions
            </h2>
          </div>
          <div className="p-3 space-y-2">
            {report.actionable_insights.map((insight, idx) => (
              <div
                key={idx}
                className={`
                  p-3 border-l-4 bg-gray-50
                  ${insight.priority === 'critical' ? 'border-l-red-600' : ''}
                  ${insight.priority === 'high' ? 'border-l-orange-500' : ''}
                  ${insight.priority === 'medium' ? 'border-l-[#0f62fe]' : ''}
                  ${insight.priority === 'low' ? 'border-l-gray-400' : ''}
                `}
              >
                <div className="flex items-start gap-3">
                  <span className="text-lg flex-shrink-0">{insight.icon}</span>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900 text-sm">{insight.title}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{insight.message}</p>
                  </div>
                  {insight.action && insight.action_type !== 'info' && (
                    <button className="text-xs text-[#0f62fe] hover:underline flex-shrink-0 font-medium">
                      {insight.action} &rarr;
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {report.case_overview.total_cases === 0 && (
        <div className="bg-white border border-gray-300 p-8 text-center">
          <p className="text-gray-600">No active cases. Add a case to begin tracking deadlines.</p>
        </div>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-gray-500 py-2">
        LitDocket Intelligence System &bull; Data as of {new Date(report.generated_at).toLocaleString()}
      </div>
    </div>
  );
}
