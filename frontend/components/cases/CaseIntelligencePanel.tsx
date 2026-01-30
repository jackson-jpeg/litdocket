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
  ChevronDown,
  ChevronUp,
  Scale,
  Lightbulb,
  Target,
  Shield,
  Activity,
  FileText,
  Gavel,
  RefreshCw,
} from 'lucide-react';

interface HealthScore {
  overall_score: number;
  deadline_compliance_score: number | null;
  document_completeness_score: number | null;
  discovery_progress_score: number | null;
  timeline_health_score: number | null;
  risk_factors: Array<{
    type: string;
    severity: string;
    description: string;
    recommendation: string;
  }>;
  recommendations: Array<{
    priority: number;
    action: string;
    reasoning: string;
    category: string;
  }>;
}

interface Prediction {
  prediction_type: string;
  predicted_value: string;
  confidence: number;
  lower_bound: string | null;
  upper_bound: string | null;
  influencing_factors: Array<{
    factor: string;
    impact: string;
    weight: number;
  }>;
}

interface JudgeInsight {
  name: string;
  court: string;
  avg_ruling_time_days: number | null;
  motion_stats: {
    total_motions?: number;
    grant_rate?: number;
    common_types?: string[];
  };
  preferences: {
    page_limits?: number;
    hearing_style?: string;
    notable_preferences?: string[];
  };
}

interface CaseIntelligencePanelProps {
  caseId: string;
  judgeName?: string;
  className?: string;
}

function ScoreGauge({ score, label, size = 'md' }: { score: number | null; label: string; size?: 'sm' | 'md' }) {
  if (score === null) return null;

  const getColor = (s: number) => {
    if (s >= 80) return { bg: 'bg-green-100', text: 'text-green-600', ring: 'ring-green-400' };
    if (s >= 60) return { bg: 'bg-yellow-100', text: 'text-yellow-600', ring: 'ring-yellow-400' };
    if (s >= 40) return { bg: 'bg-orange-100', text: 'text-orange-600', ring: 'ring-orange-400' };
    return { bg: 'bg-red-100', text: 'text-red-600', ring: 'ring-red-400' };
  };

  const colors = getColor(score);
  const sizeClasses = size === 'sm' ? 'w-12 h-12 text-sm' : 'w-16 h-16 text-lg';

  return (
    <div className="flex flex-col items-center">
      <div className={`${sizeClasses} rounded-full ${colors.bg} ring-2 ${colors.ring} flex items-center justify-center`}>
        <span className={`font-bold ${colors.text}`}>{score}</span>
      </div>
      <span className="text-xs text-slate-500 mt-1 text-center">{label}</span>
    </div>
  );
}

function RiskBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-700 border-red-200',
    high: 'bg-orange-100 text-orange-700 border-orange-200',
    medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    low: 'bg-green-100 text-green-700 border-green-200',
  };

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${colors[severity] || colors.medium}`}>
      {severity}
    </span>
  );
}

export default function CaseIntelligencePanel({ caseId, judgeName, className = '' }: CaseIntelligencePanelProps) {
  const [healthScore, setHealthScore] = useState<HealthScore | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [judgeInsight, setJudgeInsight] = useState<JudgeInsight | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'health' | 'predict' | 'judge'>('health');

  const fetchData = async (forceRefresh = false) => {
    try {
      if (forceRefresh) setRefreshing(true);

      const healthResponse = await apiClient.get(
        `/api/v1/case-intelligence/cases/${caseId}/health${forceRefresh ? '?force_refresh=true' : ''}`
      );
      setHealthScore(healthResponse.data);

      // Try to fetch judge insights if a judge is assigned
      if (judgeName) {
        try {
          const judgesResponse = await apiClient.get(`/api/v1/case-intelligence/judges?name=${encodeURIComponent(judgeName)}`);
          if (judgesResponse.data && judgesResponse.data.length > 0) {
            setJudgeInsight(judgesResponse.data[0]);
          }
        } catch (err) {
          // Judge not found is okay
        }
      }
    } catch (error) {
      console.error('Failed to fetch intelligence data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchPrediction = async () => {
    try {
      const response = await apiClient.post(`/api/v1/case-intelligence/cases/${caseId}/predict`, {
        prediction_type: 'outcome',
      });
      setPrediction(response.data);
    } catch (error) {
      console.error('Failed to fetch prediction:', error);
    }
  };

  useEffect(() => {
    fetchData();
  }, [caseId, judgeName]);

  if (loading) {
    return (
      <div className={`card ${className}`}>
        <div className="flex items-center justify-center py-8">
          <Brain className="w-6 h-6 text-purple-500 animate-pulse" />
          <span className="ml-2 text-slate-500 text-sm">Analyzing case...</span>
        </div>
      </div>
    );
  }

  const overallScore = healthScore?.overall_score ?? 0;
  const scoreColor = overallScore >= 80 ? 'text-green-600' : overallScore >= 60 ? 'text-yellow-600' : overallScore >= 40 ? 'text-orange-600' : 'text-red-600';
  const hasRisks = healthScore?.risk_factors && healthScore.risk_factors.length > 0;

  return (
    <div className={`card overflow-hidden ${className}`}>
      {/* Header - Always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-slate-900">Case Intelligence</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-sm text-slate-500">Health Score:</span>
              <span className={`text-lg font-bold ${scoreColor}`}>{overallScore}</span>
              {hasRisks && (
                <AlertTriangle className="w-4 h-4 text-orange-500" />
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              fetchData(true);
            }}
            disabled={refreshing}
            className="p-1.5 rounded hover:bg-slate-200 transition-colors"
            title="Refresh analysis"
          >
            <RefreshCw className={`w-4 h-4 text-slate-500 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && healthScore && (
        <div className="border-t border-slate-200">
          {/* Tabs */}
          <div className="flex border-b border-slate-200">
            <button
              onClick={() => setActiveTab('health')}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'health'
                  ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Activity className="w-4 h-4 inline mr-1" />
              Health
            </button>
            <button
              onClick={() => {
                setActiveTab('predict');
                if (!prediction) fetchPrediction();
              }}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'predict'
                  ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <TrendingUp className="w-4 h-4 inline mr-1" />
              Predict
            </button>
            {judgeName && (
              <button
                onClick={() => setActiveTab('judge')}
                className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'judge'
                    ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Gavel className="w-4 h-4 inline mr-1" />
                Judge
              </button>
            )}
          </div>

          {/* Tab Content */}
          <div className="p-4">
            {activeTab === 'health' && (
              <div className="space-y-4">
                {/* Score Breakdown */}
                <div className="flex justify-around py-2">
                  <ScoreGauge score={healthScore.deadline_compliance_score} label="Deadlines" size="sm" />
                  <ScoreGauge score={healthScore.document_completeness_score} label="Documents" size="sm" />
                  <ScoreGauge score={healthScore.discovery_progress_score} label="Discovery" size="sm" />
                  <ScoreGauge score={healthScore.timeline_health_score} label="Timeline" size="sm" />
                </div>

                {/* Risk Factors */}
                {healthScore.risk_factors && healthScore.risk_factors.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1">
                      <Shield className="w-4 h-4 text-orange-500" />
                      Risk Factors
                    </h4>
                    <div className="space-y-2">
                      {healthScore.risk_factors.slice(0, 3).map((risk, idx) => (
                        <div key={idx} className="p-2 bg-orange-50 rounded-lg border border-orange-100">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-slate-800">{risk.type}</span>
                            <RiskBadge severity={risk.severity} />
                          </div>
                          <p className="text-xs text-slate-600">{risk.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommendations */}
                {healthScore.recommendations && healthScore.recommendations.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1">
                      <Lightbulb className="w-4 h-4 text-yellow-500" />
                      Recommendations
                    </h4>
                    <div className="space-y-2">
                      {healthScore.recommendations.slice(0, 3).map((rec, idx) => (
                        <div
                          key={idx}
                          className={`p-2 rounded-lg border-l-4 ${
                            rec.priority === 0
                              ? 'border-l-red-500 bg-red-50'
                              : rec.priority === 1
                              ? 'border-l-orange-500 bg-orange-50'
                              : 'border-l-blue-500 bg-blue-50'
                          }`}
                        >
                          <p className="text-sm font-medium text-slate-800">{rec.action}</p>
                          <p className="text-xs text-slate-600 mt-0.5">{rec.reasoning}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'predict' && (
              <div className="space-y-4">
                {!prediction ? (
                  <div className="text-center py-6">
                    <Brain className="w-8 h-8 text-purple-400 mx-auto mb-2 animate-pulse" />
                    <p className="text-sm text-slate-500">Generating prediction...</p>
                  </div>
                ) : (
                  <>
                    <div className="text-center py-4 bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg">
                      <Target className="w-8 h-8 text-purple-500 mx-auto mb-2" />
                      <p className="text-lg font-bold text-slate-900">{prediction.predicted_value}</p>
                      <p className="text-sm text-slate-500">
                        {Math.round(prediction.confidence * 100)}% confidence
                      </p>
                      {prediction.lower_bound && prediction.upper_bound && (
                        <p className="text-xs text-slate-400 mt-1">
                          Range: {prediction.lower_bound} - {prediction.upper_bound}
                        </p>
                      )}
                    </div>

                    {prediction.influencing_factors && prediction.influencing_factors.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 mb-2">Key Factors</h4>
                        <div className="space-y-1">
                          {prediction.influencing_factors.map((factor, idx) => (
                            <div key={idx} className="flex items-center justify-between text-sm">
                              <span className="text-slate-600">{factor.factor}</span>
                              <span className={`font-medium ${
                                factor.impact === 'positive' ? 'text-green-600' :
                                factor.impact === 'negative' ? 'text-red-600' : 'text-slate-600'
                              }`}>
                                {factor.impact === 'positive' ? '+' : factor.impact === 'negative' ? '-' : '~'}
                                {Math.round(factor.weight * 100)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {activeTab === 'judge' && (
              <div className="space-y-4">
                {!judgeInsight ? (
                  <div className="text-center py-6">
                    <Gavel className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">No judge analytics available</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Judge data will be populated as rulings are tracked
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                      <Scale className="w-8 h-8 text-slate-400" />
                      <div>
                        <p className="font-semibold text-slate-900">{judgeInsight.name}</p>
                        <p className="text-sm text-slate-500">{judgeInsight.court}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      {judgeInsight.avg_ruling_time_days && (
                        <div className="p-3 bg-blue-50 rounded-lg text-center">
                          <Clock className="w-5 h-5 text-blue-500 mx-auto mb-1" />
                          <p className="text-lg font-bold text-slate-900">{judgeInsight.avg_ruling_time_days}</p>
                          <p className="text-xs text-slate-500">Avg Days to Rule</p>
                        </div>
                      )}
                      {judgeInsight.motion_stats?.grant_rate !== undefined && (
                        <div className="p-3 bg-green-50 rounded-lg text-center">
                          <CheckCircle className="w-5 h-5 text-green-500 mx-auto mb-1" />
                          <p className="text-lg font-bold text-slate-900">
                            {Math.round(judgeInsight.motion_stats.grant_rate * 100)}%
                          </p>
                          <p className="text-xs text-slate-500">Motion Grant Rate</p>
                        </div>
                      )}
                    </div>

                    {judgeInsight.preferences?.notable_preferences && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 mb-2">Known Preferences</h4>
                        <ul className="text-sm text-slate-600 space-y-1">
                          {judgeInsight.preferences.notable_preferences.map((pref, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-purple-500 mt-0.5">•</span>
                              {pref}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Footer Link */}
          <div className="px-4 pb-4">
            <Link
              href="/intelligence"
              className="flex items-center justify-center gap-2 text-sm text-purple-600 hover:text-purple-700 font-medium"
            >
              <Brain className="w-4 h-4" />
              View Full Intelligence Dashboard
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
