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
    } catch (err: unknown) {
      console.error('Failed to load morning report:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load briefing';
      setError(errorMessage);
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
      case 'fatal': return { label: 'FATAL', class: 'badge-critical' };
      case 'critical': return { label: 'CRITICAL', class: 'badge-critical' };
      case 'high': return { label: 'HIGH', class: 'badge-warning' };
      case 'medium': return { label: 'MEDIUM', class: 'badge-warning' };
      default: return { label: 'STANDARD', class: 'badge-neutral' };
    }
  };

  const getAlertStatus = (alert: MorningReportData['high_risk_alerts'][0]) => {
    if (alert.alert_level === 'OVERDUE') {
      return { label: `${alert.days_overdue || Math.abs(alert.days_until || 0)}d OVERDUE`, class: 'text-overdue font-bold' };
    }
    if (alert.days_until === 0) return { label: 'DUE TODAY', class: 'text-overdue font-bold' };
    if (alert.days_until === 1) return { label: 'DUE TOMORROW', class: 'text-status-warning font-semibold' };
    if (alert.days_until && alert.days_until <= 3) return { label: `${alert.days_until}d`, class: 'text-status-warning' };
    return { label: `${alert.days_until}d`, class: 'text-enterprise-grey-600' };
  };

  if (loading) {
    return (
      <div className="panel-beveled p-8">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 text-navy animate-spin" />
          <span className="text-enterprise-grey-600 text-sm">Loading intelligence briefing...</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="panel-beveled p-6">
        <p className="text-enterprise-grey-600 text-sm text-center">Unable to load briefing data</p>
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
      {/* Header Bar - Window Titlebar Style */}
      <div className="window-frame">
        <div className="window-titlebar flex items-baseline justify-between">
          <div>
            <h1 className="window-titlebar-text text-lg tracking-tight">
              Daily Intelligence Briefing
            </h1>
          </div>
          <div className="text-right text-xs">
            <span className="opacity-75">{dateStr}</span>
          </div>
        </div>

        {/* Summary Panel */}
        <div className="window-content p-4">
          <p className="text-enterprise-grey-800 leading-relaxed text-sm">{report.summary}</p>

          {/* Stats Row - Dense Data Grid */}
          <div className="grid grid-cols-4 gap-3 mt-4 pt-3 border-t border-enterprise-grey-300">
            <div className="panel-inset p-2 text-center">
              <p className="text-xxs text-enterprise-grey-500 uppercase tracking-wide">Active Cases</p>
              <p className="font-mono text-xl font-semibold text-enterprise-grey-900">{report.case_overview.total_cases}</p>
            </div>
            <div className="panel-inset p-2 text-center">
              <p className="text-xxs text-enterprise-grey-500 uppercase tracking-wide">Pending</p>
              <p className="font-mono text-xl font-semibold text-enterprise-grey-900">{report.case_overview.total_pending_deadlines}</p>
            </div>
            <div className="panel-inset p-2 text-center">
              <p className="text-xxs text-enterprise-grey-500 uppercase tracking-wide">Attention</p>
              <p className={`font-mono text-xl font-semibold ${report.case_overview.cases_needing_attention > 0 ? 'text-overdue' : 'text-filed'}`}>
                {report.case_overview.cases_needing_attention}
              </p>
            </div>
            {report.week_stats && (
              <div className="panel-inset p-2 text-center">
                <p className="text-xxs text-enterprise-grey-500 uppercase tracking-wide">Completed</p>
                <p className="font-mono text-xl font-semibold text-filed">{report.week_stats.completed_this_week}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Critical Alerts Table */}
      {report.high_risk_alerts && report.high_risk_alerts.length > 0 && (
        <div className="enterprise-card">
          <div className="enterprise-card-header flex items-center gap-2" style={{ backgroundColor: '#FFEBEE', borderColor: '#8B0000' }}>
            <AlertTriangle className="w-4 h-4 text-overdue" />
            <h2 className="text-sm font-semibold text-overdue uppercase tracking-wide">
              Critical Alerts ({report.high_risk_alerts.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="w-20">Status</th>
                  <th className="w-20">Priority</th>
                  <th>Deadline</th>
                  <th>Case</th>
                  <th className="w-28">Due Date</th>
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
                      className="cursor-pointer"
                      onClick={() => onCaseClick?.(alert.case_id)}
                    >
                      <td>
                        <span className={`font-mono text-xs ${status.class}`}>{status.label}</span>
                      </td>
                      <td>
                        <span className={priority.class}>{priority.label}</span>
                      </td>
                      <td className="font-medium">{alert.deadline_title}</td>
                      <td className="text-enterprise-grey-600">{alert.case_title}</td>
                      <td className="font-mono text-xs">
                        {alert.deadline_date ? formatDate(alert.deadline_date) : '—'}
                      </td>
                      <td>
                        <ChevronRight className="w-4 h-4 text-enterprise-grey-400" />
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
          <div className="enterprise-card">
            <div className="enterprise-card-header flex items-center gap-2">
              <Clock className="w-4 h-4 text-navy" />
              <h2 className="text-sm uppercase tracking-wide">
                7-Day Outlook ({report.upcoming_deadlines.length})
              </h2>
            </div>
            <div className="divide-y divide-enterprise-grey-200 max-h-80 overflow-y-auto classic-scrollbar">
              {report.upcoming_deadlines.map((deadline, idx) => {
                const priority = getPriorityDisplay(deadline.priority);
                return (
                  <div
                    key={idx}
                    className="px-3 py-2 hover:bg-surface cursor-pointer flex items-center gap-3"
                    onClick={() => onCaseClick?.(deadline.case_id)}
                  >
                    <div className="flex-shrink-0 w-16 text-center">
                      <p className="font-mono text-sm font-bold text-enterprise-grey-900">
                        {formatShortDate(deadline.deadline_date)}
                      </p>
                      <p className={`text-xs ${deadline.days_until <= 1 ? 'text-overdue font-semibold' : 'text-enterprise-grey-500'}`}>
                        {deadline.days_until === 0 ? 'Today' : deadline.days_until === 1 ? 'Tomorrow' : `${deadline.days_until}d`}
                      </p>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-enterprise-grey-900 truncate">{deadline.deadline_title}</p>
                      <p className="text-xs text-enterprise-grey-500 truncate">{deadline.case_title}</p>
                    </div>
                    <span className={`flex-shrink-0 ${priority.class}`}>
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
          <div className="enterprise-card">
            <div className="enterprise-card-header">
              <h2 className="text-sm uppercase tracking-wide">
                Upcoming Proceedings
              </h2>
            </div>
            <div className="divide-y divide-enterprise-grey-200">
              {report.milestones.map((milestone, idx) => (
                <div
                  key={idx}
                  className="px-3 py-2 hover:bg-surface cursor-pointer flex items-center gap-3"
                  onClick={() => onCaseClick?.(milestone.case_id)}
                >
                  <div className="flex-shrink-0 w-16 text-center border-r border-enterprise-grey-200 pr-3">
                    <p className="text-xs text-enterprise-grey-500 uppercase">
                      {new Date(milestone.date).toLocaleDateString('en-US', { month: 'short' })}
                    </p>
                    <p className="font-mono text-xl font-bold text-enterprise-grey-900">
                      {new Date(milestone.date).getDate()}
                    </p>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-enterprise-grey-900 uppercase tracking-wide">
                      {milestone.type}
                    </p>
                    <p className="text-xs text-enterprise-grey-600 truncate">{milestone.case_title}</p>
                  </div>
                  <span className="text-xs text-enterprise-grey-500 flex-shrink-0 font-mono">
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
        <div className="enterprise-card">
          <div className="enterprise-card-header">
            <h2 className="text-sm uppercase tracking-wide">
              Recent Document Activity ({report.new_filings.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Type</th>
                  <th>Case</th>
                  <th className="w-36">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {report.new_filings.slice(0, 5).map((filing, idx) => (
                  <tr
                    key={idx}
                    className="cursor-pointer"
                    onClick={() => onCaseClick?.(filing.case_id)}
                  >
                    <td>{filing.document_title}</td>
                    <td className="text-xs uppercase">{filing.document_type || '—'}</td>
                    <td className="text-enterprise-grey-600">{filing.case_title}</td>
                    <td className="font-mono text-xs text-enterprise-grey-500">
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
        <div className="enterprise-card">
          <div className="enterprise-card-header" style={{ backgroundColor: '#E3F2FD' }}>
            <h2 className="text-sm text-navy uppercase tracking-wide">
              Recommended Actions
            </h2>
          </div>
          <div className="enterprise-card-body space-y-2">
            {report.actionable_insights.map((insight, idx) => (
              <div
                key={idx}
                className={`
                  p-3 bg-surface-light
                  ${insight.priority === 'critical' ? 'priority-fatal' : ''}
                  ${insight.priority === 'high' ? 'priority-critical' : ''}
                  ${insight.priority === 'medium' ? 'priority-important' : ''}
                  ${insight.priority === 'low' ? 'priority-standard' : ''}
                `}
              >
                <div className="flex items-start gap-3">
                  <span className="text-lg flex-shrink-0">{insight.icon}</span>
                  <div className="flex-1">
                    <p className="font-semibold text-enterprise-grey-900 text-sm">{insight.title}</p>
                    <p className="text-xs text-enterprise-grey-600 mt-0.5">{insight.message}</p>
                  </div>
                  {insight.action && insight.action_type !== 'info' && (
                    <button className="btn-beveled text-xs flex-shrink-0">
                      {insight.action}
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
        <div className="panel-beveled p-8 text-center">
          <p className="text-enterprise-grey-600">No active cases. Add a case to begin tracking deadlines.</p>
        </div>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-enterprise-grey-500 py-2 font-mono">
        LitDocket Intelligence System &bull; Data as of {new Date(report.generated_at).toLocaleString()}
      </div>
    </div>
  );
}
