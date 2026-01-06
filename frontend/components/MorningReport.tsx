'use client';

import { useState, useEffect } from 'react';
import { Sun, AlertTriangle, FileText, Calendar, TrendingUp, ChevronRight, Loader2 } from 'lucide-react';
import apiClient from '@/lib/api-client';

interface MorningReportData {
  greeting: string;
  summary: string;
  high_risk_alerts: Array<{
    type: string;
    alert_level: string;
    deadline_id: string;
    case_id: string;
    case_title: string;
    deadline_title: string;
    deadline_date: string;
    days_until?: number;
    message: string;
  }>;
  new_filings: Array<{
    document_id: string;
    case_id: string;
    case_title: string;
    document_title: string;
    uploaded_at: string;
    message: string;
  }>;
  upcoming_deadlines: Array<{
    deadline_id: string;
    case_id: string;
    case_title: string;
    deadline_title: string;
    deadline_date: string;
    days_until: number;
    urgency: string;
  }>;
  actionable_insights: Array<{
    priority: string;
    icon: string;
    title: string;
    message: string;
    action: string;
  }>;
  case_overview: {
    total_cases: number;
    cases_needing_attention: number;
    total_pending_deadlines: number;
  };
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
      setError(err.response?.data?.detail || 'Failed to load morning report');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-red-50 border-red-200 text-red-900';
      case 'high': return 'bg-orange-50 border-orange-200 text-orange-900';
      case 'medium': return 'bg-yellow-50 border-yellow-200 text-yellow-900';
      default: return 'bg-blue-50 border-blue-200 text-blue-900';
    }
  };

  const getAlertColor = (alertLevel: string) => {
    switch (alertLevel) {
      case 'OVERDUE': return 'bg-red-50 border-red-300';
      case 'CRITICAL': return 'bg-red-50 border-red-200';
      case 'URGENT': return 'bg-orange-50 border-orange-200';
      default: return 'bg-yellow-50 border-yellow-200';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
        <div className="flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
          <span className="ml-3 text-slate-600">Loading intelligence briefing...</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <p className="text-slate-600 text-center">Unable to load morning report</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Greeting & Summary */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-blue-50 rounded-lg">
            <Sun className="w-6 h-6 text-blue-600" />
          </div>
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-slate-800 mb-2">{report.greeting}</h2>
            <p className="text-slate-600 leading-relaxed">{report.summary}</p>
            <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-200">
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-800">{report.case_overview.total_cases}</p>
                <p className="text-xs text-slate-600 mt-1">Active Cases</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-orange-600">{report.case_overview.cases_needing_attention}</p>
                <p className="text-xs text-slate-600 mt-1">Need Attention</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-800">{report.case_overview.total_pending_deadlines}</p>
                <p className="text-xs text-slate-600 mt-1">Pending Deadlines</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Actionable Insights */}
      {report.actionable_insights && report.actionable_insights.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="p-6 border-b border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              Actionable Insights
            </h3>
          </div>
          <div className="p-6 space-y-3">
            {report.actionable_insights.map((insight, idx) => (
              <div
                key={idx}
                className={`p-4 border-2 rounded-lg ${getPriorityColor(insight.priority)}`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{insight.icon}</span>
                  <div className="flex-1">
                    <h4 className="font-semibold mb-1">{insight.title}</h4>
                    <p className="text-sm mb-2">{insight.message}</p>
                    <button className="text-xs font-medium underline hover:no-underline">
                      {insight.action} →
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* High-Risk Alerts */}
      {report.high_risk_alerts && report.high_risk_alerts.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="p-6 border-b border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              High-Risk Alerts
            </h3>
          </div>
          <div className="p-6 space-y-3 max-h-96 overflow-y-auto">
            {report.high_risk_alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`p-4 border-2 rounded-lg cursor-pointer hover:opacity-80 transition-opacity ${getAlertColor(alert.alert_level)}`}
                onClick={() => onCaseClick?.(alert.case_id)}
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-800">{alert.case_title}</p>
                    <p className="text-sm font-medium text-slate-700 mt-1">{alert.deadline_title}</p>
                    <p className="text-sm text-slate-600 mt-2">{alert.message}</p>
                    {alert.deadline_date && (
                      <p className="text-xs text-slate-500 mt-2">Deadline: {alert.deadline_date}</p>
                    )}
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* New Filings */}
      {report.new_filings && report.new_filings.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="p-6 border-b border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-500" />
              New Filings Since Last Login
            </h3>
          </div>
          <div className="p-6 space-y-3">
            {report.new_filings.map((filing, idx) => (
              <div
                key={idx}
                className="p-4 bg-blue-50 border border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors"
                onClick={() => onCaseClick?.(filing.case_id)}
              >
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800">{filing.document_title}</p>
                    <p className="text-sm text-slate-600 mt-1">{filing.case_title}</p>
                    <p className="text-xs text-slate-500 mt-2">
                      {new Date(filing.uploaded_at).toLocaleString()}
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming Deadlines This Week */}
      {report.upcoming_deadlines && report.upcoming_deadlines.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="p-6 border-b border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-500" />
              This Week's Deadlines
            </h3>
          </div>
          <div className="p-6 space-y-2">
            {report.upcoming_deadlines.slice(0, 10).map((deadline, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors"
                onClick={() => onCaseClick?.(deadline.case_id)}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-800 text-sm truncate">{deadline.deadline_title}</p>
                  <p className="text-xs text-slate-600 truncate">{deadline.case_title}</p>
                </div>
                <div className="text-right ml-4">
                  <p className="text-sm font-semibold text-slate-800">{deadline.deadline_date}</p>
                  <p className={`text-xs ${deadline.days_until <= 1 ? 'text-red-600 font-semibold' : deadline.days_until <= 3 ? 'text-orange-600' : 'text-slate-600'}`}>
                    {deadline.days_until} day{deadline.days_until !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
