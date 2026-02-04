'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/api-client';
import {
  Brain,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  Scale,
  Activity,
  ChevronRight,
  RefreshCw,
  Zap,
} from 'lucide-react';

interface DashboardSummary {
  total_cases: number;
  cases_with_scores: number;
  average_health_score: number;
  at_risk_count: number;
  healthy_count: number;
}

interface AtRiskCase {
  case_id: string;
  case_title: string;
  health_score: number;
  top_risk: {
    type: string;
    severity: string;
    description: string;
  } | null;
}

interface Recommendation {
  priority: number;
  action: string;
  reasoning: string;
  category: string;
}

interface ScoreDistribution {
  critical: number;
  warning: number;
  fair: number;
  good: number;
}

interface DashboardData {
  summary: DashboardSummary;
  at_risk_cases: AtRiskCase[];
  top_recommendations: Recommendation[];
  score_distribution: ScoreDistribution;
}

function HealthGauge({ score, size = 'large' }: { score: number; size?: 'small' | 'large' }) {
  const getColor = (s: number) => {
    if (s >= 80) return 'text-green-500';
    if (s >= 60) return 'text-yellow-500';
    if (s >= 40) return 'text-orange-500';
    return 'text-red-500';
  };

  const getBgColor = (s: number) => {
    if (s >= 80) return 'bg-green-100';
    if (s >= 60) return 'bg-yellow-100';
    if (s >= 40) return 'bg-orange-100';
    return 'bg-red-100';
  };

  const sizeClasses = size === 'large' ? 'w-32 h-32 text-4xl' : 'w-16 h-16 text-lg';

  return (
    <div className={`${sizeClasses} rounded-full ${getBgColor(score)} flex items-center justify-center`}>
      <span className={`font-bold ${getColor(score)}`}>{score}</span>
    </div>
  );
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const getColor = (s: number) => {
    if (s >= 80) return 'bg-green-500';
    if (s >= 60) return 'bg-yellow-500';
    if (s >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600 w-32">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor(score)} transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-sm font-medium text-gray-900 w-10">{score}</span>
    </div>
  );
}

export default function IntelligenceDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEmptyState, setIsEmptyState] = useState(false);

  const fetchDashboard = async () => {
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/case-intelligence/dashboard');
      const dashboardData = response.data;

      // Check for empty state (no cases)
      if (dashboardData.summary.total_cases === 0) {
        setIsEmptyState(true);
      } else {
        setIsEmptyState(false);
      }

      setData(dashboardData);
    } catch (err: unknown) {
      console.error('Failed to fetch dashboard:', err);
      // Check if it's a 404 or specific error indicating no data
      const errorResponse = err as { response?: { status?: number; data?: { detail?: string } } };
      if (errorResponse?.response?.status === 404) {
        setIsEmptyState(true);
        // Set empty data structure for new users
        setData({
          summary: { total_cases: 0, cases_with_scores: 0, average_health_score: 0, at_risk_count: 0, healthy_count: 0 },
          at_risk_cases: [],
          top_recommendations: [],
          score_distribution: { critical: 0, warning: 0, fair: 0, good: 0 },
        });
      } else {
        setError(errorResponse?.response?.data?.detail || 'Failed to load dashboard data. Please try again.');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboard();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <Brain className="w-16 h-16 text-blue-400 animate-pulse mx-auto mb-4" />
          <p className="text-white text-lg">Analyzing your cases...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Unable to Load Dashboard</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 mx-auto"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (isEmptyState || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
        {/* Header */}
        <div className="border-b border-slate-700">
          <div className="max-w-7xl mx-auto px-6 py-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-lg">
                <Brain className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Case Intelligence</h1>
                <p className="text-slate-400">AI-Powered Litigation Analytics</p>
              </div>
            </div>
          </div>
        </div>

        {/* Empty State */}
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <div className="p-4 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-2xl inline-block mb-6">
            <Brain className="w-16 h-16 text-blue-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-4">Get Started with Case Intelligence</h2>
          <p className="text-slate-400 mb-8 leading-relaxed">
            Once you add your first case, our AI will analyze risk factors, track health scores,
            and surface actionable recommendations to keep you ahead of deadlines.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/cases"
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Scale className="w-5 h-5" />
              Add Your First Case
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-lg">
                <Brain className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Case Intelligence</h1>
                <p className="text-slate-400">AI-Powered Litigation Analytics</p>
              </div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Top Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-2">
              <Scale className="w-5 h-5 text-blue-400" />
              <span className="text-slate-400 text-sm">Active Cases</span>
            </div>
            <p className="text-3xl font-bold text-white">{data.summary.total_cases}</p>
          </div>

          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-2">
              <Activity className="w-5 h-5 text-green-400" />
              <span className="text-slate-400 text-sm">Average Health</span>
            </div>
            <p className="text-3xl font-bold text-white">{data.summary.average_health_score}%</p>
          </div>

          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <span className="text-slate-400 text-sm">At Risk</span>
            </div>
            <p className="text-3xl font-bold text-red-400">{data.summary.at_risk_count}</p>
          </div>

          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <span className="text-slate-400 text-sm">Healthy</span>
            </div>
            <p className="text-3xl font-bold text-green-400">{data.summary.healthy_count}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Health Distribution */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-6">Case Health Distribution</h2>

            <div className="flex items-center justify-center mb-6">
              <HealthGauge score={Math.round(data.summary.average_health_score)} />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span className="text-slate-300">Good (80+)</span>
                </div>
                <span className="text-white font-medium">{data.score_distribution.good}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <span className="text-slate-300">Fair (60-79)</span>
                </div>
                <span className="text-white font-medium">{data.score_distribution.fair}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                  <span className="text-slate-300">Warning (40-59)</span>
                </div>
                <span className="text-white font-medium">{data.score_distribution.warning}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <span className="text-slate-300">Critical (&lt;40)</span>
                </div>
                <span className="text-white font-medium">{data.score_distribution.critical}</span>
              </div>
            </div>
          </div>

          {/* At-Risk Cases */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">At-Risk Cases</h2>
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>

            {data.at_risk_cases.length === 0 ? (
              <div className="text-center py-8">
                <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
                <p className="text-slate-400">All cases are in good health!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {data.at_risk_cases.slice(0, 5).map((caseItem) => (
                  <Link
                    key={caseItem.case_id}
                    href={`/cases/${caseItem.case_id}`}
                    className="block p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white font-medium truncate flex-1">
                        {caseItem.case_title || 'Untitled Case'}
                      </span>
                      <HealthGauge score={caseItem.health_score} size="small" />
                    </div>
                    {caseItem.top_risk && (
                      <p className="text-sm text-red-400 truncate">
                        {caseItem.top_risk.description}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* AI Recommendations */}
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">AI Recommendations</h2>
              <Zap className="w-5 h-5 text-yellow-400" />
            </div>

            {data.top_recommendations.length === 0 ? (
              <div className="text-center py-8">
                <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
                <p className="text-slate-400">No urgent actions needed</p>
              </div>
            ) : (
              <div className="space-y-3">
                {data.top_recommendations.slice(0, 5).map((rec, index) => (
                  <div
                    key={index}
                    className="p-3 bg-slate-700/50 rounded-lg border-l-4"
                    style={{
                      borderLeftColor:
                        rec.priority === 0
                          ? '#ef4444'
                          : rec.priority === 1
                          ? '#f59e0b'
                          : '#3b82f6',
                    }}
                  >
                    <p className="text-white text-sm font-medium">{rec.action}</p>
                    <p className="text-slate-400 text-xs mt-1">{rec.reasoning}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
          <Link
            href="/cases"
            className="flex items-center gap-3 p-4 bg-slate-800 rounded-xl border border-slate-700 hover:border-blue-500 transition-colors"
          >
            <Scale className="w-6 h-6 text-blue-400" />
            <div>
              <p className="text-white font-medium">View Cases</p>
              <p className="text-slate-400 text-sm">Manage all cases</p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-500 ml-auto" />
          </Link>

          <Link
            href="/calendar"
            className="flex items-center gap-3 p-4 bg-slate-800 rounded-xl border border-slate-700 hover:border-blue-500 transition-colors"
          >
            <Clock className="w-6 h-6 text-green-400" />
            <div>
              <p className="text-white font-medium">Deadlines</p>
              <p className="text-slate-400 text-sm">View calendar</p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-500 ml-auto" />
          </Link>

          <Link
            href="/tools/authority-core"
            className="flex items-center gap-3 p-4 bg-slate-800 rounded-xl border border-slate-700 hover:border-blue-500 transition-colors"
          >
            <FileText className="w-6 h-6 text-purple-400" />
            <div>
              <p className="text-white font-medium">Authority Core</p>
              <p className="text-slate-400 text-sm">Rules database</p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-500 ml-auto" />
          </Link>

          <Link
            href="/ai-assistant"
            className="flex items-center gap-3 p-4 bg-slate-800 rounded-xl border border-slate-700 hover:border-blue-500 transition-colors"
          >
            <Brain className="w-6 h-6 text-yellow-400" />
            <div>
              <p className="text-white font-medium">AI Assistant</p>
              <p className="text-slate-400 text-sm">Ask questions</p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-500 ml-auto" />
          </Link>
        </div>
      </div>
    </div>
  );
}
