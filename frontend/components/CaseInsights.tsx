'use client';

import { useEffect, useState } from 'react';
import { TrendingUp, AlertTriangle, Lightbulb, Target, Activity, CheckCircle, Clock, AlertCircle } from 'lucide-react';

interface CaseInsightsProps {
  caseId: string;
}

interface Insights {
  case_health: {
    score: number;
    status: string;
    emoji: string;
    issues: string[];
  };
  urgent_alerts: Array<{
    severity: string;
    type: string;
    title: string;
    message: string;
    days_until?: number;
    days_overdue?: number;
  }>;
  smart_recommendations: string[];
  deadline_analytics: {
    total: number;
    pending: number;
    completed: number;
    overdue: number;
    completion_rate: number;
  };
  next_actions: Array<{
    priority: string;
    action: string;
    due_date?: string;
    days_until?: number;
  }>;
  risk_factors: Array<{
    severity: string;
    category: string;
    description: string;
  }>;
  efficiency_score: {
    score: number;
    rating: string;
  };
}

export default function CaseInsights({ caseId }: CaseInsightsProps) {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInsights();
  }, [caseId]);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/insights/case/${caseId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch insights');
      }

      const data = await response.json();
      setInsights(data);
    } catch (err) {
      setError('Failed to load case insights');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-48 bg-gray-200 rounded"></div>
          <div className="h-4 w-full bg-gray-200 rounded"></div>
          <div className="h-4 w-3/4 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !insights) {
    return null; // Silently fail - insights are nice-to-have
  }

  // Calculate combined health (average of case health and efficiency)
  const combinedHealth = Math.round((insights.case_health.score + insights.efficiency_score.score) / 2);

  // Determine overall status
  const getOverallStatus = () => {
    if (combinedHealth >= 90) return { text: 'Excellent', color: 'green', emoji: '💚' };
    if (combinedHealth >= 75) return { text: 'Good', color: 'blue', emoji: '💙' };
    if (combinedHealth >= 60) return { text: 'Fair', color: 'yellow', emoji: '💛' };
    if (combinedHealth >= 40) return { text: 'Needs Attention', color: 'orange', emoji: '🧡' };
    return { text: 'Critical', color: 'red', emoji: '❤️' };
  };

  const status = getOverallStatus();

  // Combine alerts and next actions into critical matters
  const criticalMatters = [
    ...insights.urgent_alerts.map(alert => ({ ...alert, type: 'alert' })),
    ...insights.next_actions.filter(action => action.priority === 'high').map(action => ({ ...action, type: 'action' }))
  ].slice(0, 5);

  return (
    <div className="space-y-4">
      {/* Section 1: Overall Health & Performance */}
      <div className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 rounded-xl border border-blue-200 p-6 shadow-sm">
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className={`p-3 bg-gradient-to-br from-${status.color}-500 to-${status.color}-600 rounded-xl shadow-md`}>
              <Activity className="w-7 h-7 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Overall Health</h3>
              <p className="text-sm text-gray-600 flex items-center gap-1.5">
                <span>{status.emoji}</span>
                <span>{status.text}</span>
              </p>
            </div>
          </div>
          <div className="text-center">
            <div className="text-5xl font-bold bg-gradient-to-br from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              {combinedHealth}
            </div>
            <div className="text-xs text-gray-500 font-medium">/ 100</div>
          </div>
        </div>

        {/* Dual Health Bars */}
        <div className="space-y-3 mb-4">
          {/* Case Health */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-700">Case Management</span>
              <span className="text-xs font-semibold text-gray-900">{insights.case_health.score}/100</span>
            </div>
            <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  insights.case_health.score >= 75
                    ? 'bg-gradient-to-r from-green-500 to-green-600'
                    : insights.case_health.score >= 50
                    ? 'bg-gradient-to-r from-yellow-500 to-yellow-600'
                    : 'bg-gradient-to-r from-red-500 to-red-600'
                }`}
                style={{ width: `${insights.case_health.score}%` }}
              />
            </div>
          </div>

          {/* Efficiency Rating */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-700">Deadline Efficiency</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-900">{insights.efficiency_score.score}%</span>
                <span className="text-xs px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full font-medium">
                  {insights.efficiency_score.rating}
                </span>
              </div>
            </div>
            <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 transition-all duration-500"
                style={{ width: `${insights.efficiency_score.score}%` }}
              />
            </div>
          </div>
        </div>

        {/* Top Issues */}
        {insights.case_health.issues.length > 0 && (
          <div className="pt-3 border-t border-blue-100">
            <p className="text-xs font-semibold text-gray-700 mb-2">Areas to Address:</p>
            <div className="space-y-1">
              {insights.case_health.issues.slice(0, 3).map((issue, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <AlertCircle className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-gray-700">{issue}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Critical Matters (Alerts + High Priority Actions) */}
      {criticalMatters.length > 0 && (
        <div className="bg-gradient-to-br from-red-50 to-orange-50 border border-red-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 bg-red-500 rounded-lg shadow-sm">
              <AlertTriangle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h4 className="font-bold text-red-900">Critical Matters</h4>
              <p className="text-xs text-red-700">Requires immediate attention</p>
            </div>
          </div>
          <div className="space-y-2">
            {criticalMatters.map((matter, idx) => (
              <div key={idx} className="bg-white p-3 rounded-lg border border-red-100 shadow-sm">
                {'message' in matter ? (
                  // Alert
                  <div className="flex items-start gap-2">
                    <Clock className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-red-900 font-medium">{matter.message}</p>
                  </div>
                ) : (
                  // Action
                  <div className="flex items-start gap-2">
                    <Target className="w-4 h-4 text-orange-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm text-gray-900 font-medium">{matter.action}</p>
                      {matter.days_until !== undefined && (
                        <p className="text-xs text-orange-700 mt-0.5">Due in {matter.days_until} days</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 3: Smart Insights & Analytics */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-purple-500 rounded-lg shadow-sm">
            <Lightbulb className="w-5 h-5 text-white" />
          </div>
          <div>
            <h4 className="font-bold text-gray-900">Smart Insights</h4>
            <p className="text-xs text-gray-600">AI-powered recommendations</p>
          </div>
        </div>

        {/* Deadline Stats Overview */}
        <div className="grid grid-cols-4 gap-2 mb-4 p-3 bg-gradient-to-br from-slate-50 to-gray-50 rounded-lg border border-gray-100">
          <div className="text-center">
            <div className="text-xl font-bold text-blue-600">{insights.deadline_analytics.pending}</div>
            <div className="text-[10px] text-gray-600 uppercase tracking-wide">Pending</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-green-600">{insights.deadline_analytics.completed}</div>
            <div className="text-[10px] text-gray-600 uppercase tracking-wide">Done</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-red-600">{insights.deadline_analytics.overdue}</div>
            <div className="text-[10px] text-gray-600 uppercase tracking-wide">Overdue</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-purple-600">{insights.deadline_analytics.completion_rate}%</div>
            <div className="text-[10px] text-gray-600 uppercase tracking-wide">On-Time</div>
          </div>
        </div>

        {/* Recommendations with context */}
        {insights.smart_recommendations.length > 0 ? (
          <div className="space-y-2">
            {insights.smart_recommendations.map((rec, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg border border-purple-100">
                <div className="mt-0.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-purple-500"></div>
                </div>
                <p className="text-sm text-purple-900 flex-1">{rec}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 py-6 text-green-700">
            <CheckCircle className="w-5 h-5" />
            <p className="text-sm font-medium">Everything looks great! Keep up the good work.</p>
          </div>
        )}

        {/* Additional Next Actions (non-high priority) */}
        {insights.next_actions.filter(action => action.priority !== 'high').length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5" />
              Suggested Actions
            </p>
            <div className="space-y-1.5">
              {insights.next_actions
                .filter(action => action.priority !== 'high')
                .slice(0, 3)
                .map((action, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-xs text-gray-700">
                    <div className={`mt-1 w-1.5 h-1.5 rounded-full ${
                      action.priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                    }`} />
                    <span>{action.action}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
