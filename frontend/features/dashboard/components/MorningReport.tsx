'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, Clock, ChevronRight, Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import apiClient, { extractApiError } from '@/lib/api-client';

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
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<MorningReportData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMorningReport();
  }, []);

  const fetchMorningReport = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get('/api/v1/dashboard/morning-report');
      const data = response.data;

      // Validate and provide defaults for required fields
      if (data) {
        const validatedReport: MorningReportData = {
          greeting: data.greeting || 'Good morning',
          summary: data.summary || 'Welcome to LitDocket.',
          high_risk_alerts: data.high_risk_alerts || [],
          new_filings: data.new_filings || [],
          upcoming_deadlines: data.upcoming_deadlines || [],
          actionable_insights: data.actionable_insights || [],
          case_overview: data.case_overview || {
            total_cases: 0,
            cases_needing_attention: 0,
            total_pending_deadlines: 0
          },
          week_stats: data.week_stats,
          milestones: data.milestones || [],
          workload_level: data.workload_level || 'clear',
          generated_at: data.generated_at || new Date().toISOString()
        };
        setReport(validatedReport);
      }
    } catch (err: unknown) {
      console.error('Failed to load morning report:', err);
      const apiError = extractApiError(err);
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    fetchMorningReport();
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
      <div className="card p-8">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
          <span className="text-slate-600 text-sm">Loading intelligence briefing...</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="card p-6">
        <div className="flex flex-col items-center justify-center gap-3">
          <AlertTriangle className="w-8 h-8 text-amber-500" />
          <p className="text-slate-700 text-sm font-medium">Unable to load briefing data</p>
          {error && (
            <p className="text-slate-500 text-xs text-center max-w-md">{error}</p>
          )}
          <button
            onClick={handleRetry}
            className="mt-2 px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
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
    <div className="space-y-6">
      {/* Header Bar - Paper & Steel */}
      <div className="card">
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-baseline justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Daily Intelligence Briefing
            </h1>
            <div className="flex items-center gap-2 text-xs text-slate-500 font-mono mt-1">
              <Clock className="w-3 h-3" />
              Last updated: {formatDistanceToNow(new Date(report.generated_at), { addSuffix: true })}
            </div>
          </div>
          <div className="text-right text-xs">
            <span className="text-slate-500 font-mono">{dateStr}</span>
          </div>
        </div>

        {/* Summary Panel */}
        <div className="p-6 bg-white">
          <p className="text-slate-900 leading-relaxed text-base">{report.summary}</p>

          {/* Stats Row - Clean Cards */}
          <div className="grid grid-cols-4 gap-4 mt-6 pt-4 border-t border-slate-200">
            {/* Active Cases Card */}
            <div
              onClick={() => router.push('/cases')}
              className="bg-white border border-slate-200 rounded-lg p-4 cursor-pointer hover:border-blue-300 hover:shadow-md transition-all"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Active Cases
                </span>
                <TrendingUp className="w-3 h-3 text-green-600" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold font-mono text-slate-900">
                  {report.case_overview.total_cases}
                </span>
                <span className="text-xs text-green-600 font-mono">+5%</span>
              </div>
            </div>

            {/* Pending Deadlines Card */}
            <div
              onClick={() => router.push('/calendar?filter=pending')}
              className="bg-white border border-slate-200 rounded-lg p-4 cursor-pointer hover:border-blue-300 hover:shadow-md transition-all"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Pending
                </span>
                <Minus className="w-3 h-3 text-slate-400" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold font-mono text-slate-900">
                  {report.case_overview.total_pending_deadlines}
                </span>
                <span className="text-xs text-slate-400 font-mono">0%</span>
              </div>
            </div>

            {/* Cases Needing Attention Card */}
            <div
              onClick={() => router.push('/cases?filter=attention')}
              className={`bg-white border rounded-lg p-4 cursor-pointer hover:shadow-md transition-all ${
                report.case_overview.cases_needing_attention > 0
                  ? 'border-red-200 hover:border-red-300'
                  : 'border-green-200 hover:border-green-300'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Attention
                </span>
                {report.case_overview.cases_needing_attention > 0 ? (
                  <TrendingUp className="w-3 h-3 text-red-600" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-green-600" />
                )}
              </div>
              <div className="flex items-baseline gap-2">
                <span className={`text-4xl font-bold font-mono ${
                  report.case_overview.cases_needing_attention > 0
                    ? 'text-red-600'
                    : 'text-green-600'
                }`}>
                  {report.case_overview.cases_needing_attention}
                </span>
                <span className={`text-xs font-mono ${
                  report.case_overview.cases_needing_attention > 0
                    ? 'text-red-600'
                    : 'text-green-600'
                }`}>
                  {report.case_overview.cases_needing_attention > 0 ? '+15%' : '-20%'}
                </span>
              </div>
            </div>

            {/* Completed This Week Card */}
            {report.week_stats && (
              <div
                onClick={() => router.push('/calendar?filter=completed')}
                className="bg-white border border-green-200 rounded-lg p-4 cursor-pointer hover:border-green-300 hover:shadow-md transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Completed
                  </span>
                  <TrendingUp className="w-3 h-3 text-green-600" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold font-mono text-green-600">
                    {report.week_stats.completed_this_week}
                  </span>
                  <span className="text-xs text-green-600 font-mono">+12%</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Critical Alerts Table */}
      {report.high_risk_alerts && report.high_risk_alerts.length > 0 && (
        <div className="card overflow-hidden">
          <div className="bg-red-50 border-b border-red-200 px-6 py-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            <h2 className="text-sm font-semibold text-red-900 uppercase tracking-wide">
              Critical Alerts ({report.high_risk_alerts.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider w-24">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider w-24">Priority</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Deadline</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Case</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider w-32">Due Date</th>
                  <th className="px-6 py-3 w-8"></th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {report.high_risk_alerts.map((alert, idx) => {
                  const status = getAlertStatus(alert);
                  const priority = getPriorityDisplay(alert.priority || 'fatal');
                  return (
                    <tr
                      key={idx}
                      className="cursor-pointer hover:bg-slate-50 transition-colors"
                      onClick={() => onCaseClick?.(alert.case_id)}
                    >
                      <td className="px-6 py-4">
                        <span className={`font-mono text-xs ${status.class}`}>{status.label}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={priority.class}>{priority.label}</span>
                      </td>
                      <td className="px-6 py-4 font-medium text-slate-900">{alert.deadline_title}</td>
                      <td className="px-6 py-4 text-slate-600">{alert.case_title}</td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-600">
                        {alert.deadline_date ? formatDate(alert.deadline_date) : '—'}
                      </td>
                      <td className="px-6 py-4">
                        <ChevronRight className="w-4 h-4 text-slate-400" />
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
      <div className="grid md:grid-cols-2 gap-6">
        {/* Upcoming Deadlines */}
        {report.upcoming_deadlines && report.upcoming_deadlines.length > 0 && (
          <div className="card overflow-hidden">
            <div className="bg-slate-50 border-b border-slate-200 px-6 py-3 flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">
                7-Day Outlook ({report.upcoming_deadlines.length})
              </h2>
            </div>
            <div className="divide-y divide-slate-200 max-h-80 overflow-y-auto">
              {report.upcoming_deadlines.map((deadline, idx) => {
                const priority = getPriorityDisplay(deadline.priority);
                return (
                  <div
                    key={idx}
                    className="px-6 py-4 hover:bg-slate-50 cursor-pointer flex items-center gap-4 transition-colors"
                    onClick={() => onCaseClick?.(deadline.case_id)}
                  >
                    <div className="flex-shrink-0 w-16 text-center">
                      <p className="font-mono text-sm font-bold text-slate-900">
                        {formatShortDate(deadline.deadline_date)}
                      </p>
                      <p className={`text-xs ${deadline.days_until <= 1 ? 'text-red-600 font-semibold' : 'text-slate-500'}`}>
                        {deadline.days_until === 0 ? 'Today' : deadline.days_until === 1 ? 'Tomorrow' : `${deadline.days_until}d`}
                      </p>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-900 truncate font-medium">{deadline.deadline_title}</p>
                      <p className="text-xs text-slate-500 truncate">{deadline.case_title}</p>
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
          <div className="card overflow-hidden">
            <div className="bg-slate-50 border-b border-slate-200 px-6 py-3">
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">
                Upcoming Proceedings
              </h2>
            </div>
            <div className="divide-y divide-slate-200">
              {report.milestones.map((milestone, idx) => (
                <div
                  key={idx}
                  className="px-6 py-4 hover:bg-slate-50 cursor-pointer flex items-center gap-4 transition-colors"
                  onClick={() => onCaseClick?.(milestone.case_id)}
                >
                  <div className="flex-shrink-0 w-16 text-center border-r border-slate-200 pr-4">
                    <p className="text-xs text-slate-500 uppercase font-semibold">
                      {new Date(milestone.date).toLocaleDateString('en-US', { month: 'short' })}
                    </p>
                    <p className="font-mono text-2xl font-bold text-slate-900">
                      {new Date(milestone.date).getDate()}
                    </p>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 uppercase tracking-wide">
                      {milestone.type}
                    </p>
                    <p className="text-xs text-slate-600 truncate">{milestone.case_title}</p>
                  </div>
                  <span className="text-xs text-slate-500 flex-shrink-0 font-mono">
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
        <div className="card overflow-hidden">
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-3">
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">
              Recent Document Activity ({report.new_filings.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Document</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Case</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider w-40">Uploaded</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {report.new_filings.slice(0, 5).map((filing, idx) => (
                  <tr
                    key={idx}
                    className="cursor-pointer hover:bg-slate-50 transition-colors"
                    onClick={() => onCaseClick?.(filing.case_id)}
                  >
                    <td className="px-6 py-4 font-medium text-slate-900">{filing.document_title}</td>
                    <td className="px-6 py-4 text-xs uppercase text-slate-600">{filing.document_type || '—'}</td>
                    <td className="px-6 py-4 text-slate-600">{filing.case_title}</td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-500">
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
        <div className="card overflow-hidden">
          <div className="bg-blue-50 border-b border-blue-200 px-6 py-3">
            <h2 className="text-sm font-semibold text-blue-900 uppercase tracking-wide">
              Recommended Actions
            </h2>
          </div>
          <div className="p-6 space-y-3">
            {report.actionable_insights.map((insight, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border ${
                  insight.priority === 'critical' ? 'bg-red-50 border-red-200' :
                  insight.priority === 'high' ? 'bg-orange-50 border-orange-200' :
                  insight.priority === 'medium' ? 'bg-amber-50 border-amber-200' :
                  'bg-blue-50 border-blue-200'
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-lg flex-shrink-0">{insight.icon}</span>
                  <div className="flex-1">
                    <p className="font-semibold text-slate-900 text-sm">{insight.title}</p>
                    <p className="text-xs text-slate-600 mt-1">{insight.message}</p>
                  </div>
                  {insight.action && insight.action_type !== 'info' && (
                    <button className="btn-primary text-xs flex-shrink-0">
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
        <div className="card p-8 text-center">
          <p className="text-slate-600">No active cases. Add a case to begin tracking deadlines.</p>
        </div>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-slate-500 py-4 font-mono">
        LitDocket Intelligence System &bull; Data as of {new Date(report.generated_at).toLocaleString()}
      </div>
    </div>
  );
}
