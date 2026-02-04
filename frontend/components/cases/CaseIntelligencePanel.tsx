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
    if (s >= 80) return { bg: 'bg-status-success/10', text: 'text-status-success', border: 'border-status-success' };
    if (s >= 60) return { bg: 'bg-important/10', text: 'text-important', border: 'border-important' };
    if (s >= 40) return { bg: 'bg-critical/10', text: 'text-critical', border: 'border-critical' };
    return { bg: 'bg-fatal/10', text: 'text-fatal', border: 'border-fatal' };
  };

  const colors = getColor(score);
  const sizeClasses = size === 'sm' ? 'w-12 h-12 text-sm' : 'w-16 h-16 text-lg';

  return (
    <div className="flex flex-col items-center">
      <div className={`${sizeClasses} ${colors.bg} border-2 ${colors.border} flex items-center justify-center`}>
        <span className={`font-mono font-bold ${colors.text}`}>{score}</span>
      </div>
      <span className="text-xs font-mono text-ink-muted mt-1 text-center uppercase tracking-wide">{label}</span>
    </div>
  );
}

function RiskBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-fatal/10 text-fatal border-fatal',
    high: 'bg-critical/10 text-critical border-critical',
    medium: 'bg-important/10 text-important border-important',
    low: 'bg-status-success/10 text-status-success border-status-success',
  };

  return (
    <span className={`px-2 py-0.5 text-xs font-mono font-medium uppercase border ${colors[severity] || colors.medium}`}>
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
          <Brain className="w-6 h-6 text-steel" />
          <span className="ml-2 text-ink-secondary text-sm font-mono">
            ANALYZING<span className="animate-pulse">_</span>
          </span>
        </div>
      </div>
    );
  }

  const overallScore = healthScore?.overall_score ?? 0;
  const scoreColor = overallScore >= 80 ? 'text-status-success' : overallScore >= 60 ? 'text-important' : overallScore >= 40 ? 'text-critical' : 'text-fatal';
  const hasRisks = healthScore?.risk_factors && healthScore.risk_factors.length > 0;

  return (
    <div className={`card overflow-hidden ${className}`}>
      {/* Header - Always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-surface transition-transform hover:translate-x-0.5"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-steel border border-ink">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <h3 className="font-heading font-semibold text-ink">Case Intelligence</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-sm font-mono text-ink-secondary">HEALTH:</span>
              <span className={`text-lg font-mono font-bold ${scoreColor}`}>{overallScore}</span>
              {hasRisks && (
                <AlertTriangle className="w-4 h-4 text-critical" />
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
            className="p-1.5 hover:bg-surface transition-transform hover:translate-x-0.5 hover:translate-y-0.5"
            title="Refresh analysis"
          >
            <RefreshCw className={`w-4 h-4 text-ink-muted ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-ink-muted" />
          ) : (
            <ChevronDown className="w-5 h-5 text-ink-muted" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && healthScore && (
        <div className="border-t border-ink">
          {/* Tabs */}
          <div className="flex border-b border-ink/20">
            <button
              onClick={() => setActiveTab('health')}
              className={`flex-1 px-4 py-2 text-sm font-mono font-medium uppercase tracking-wide transition-transform ${
                activeTab === 'health'
                  ? 'text-steel border-b-2 border-steel bg-surface'
                  : 'text-ink-secondary hover:text-ink hover:translate-x-0.5'
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
              className={`flex-1 px-4 py-2 text-sm font-mono font-medium uppercase tracking-wide transition-transform ${
                activeTab === 'predict'
                  ? 'text-steel border-b-2 border-steel bg-surface'
                  : 'text-ink-secondary hover:text-ink hover:translate-x-0.5'
              }`}
            >
              <TrendingUp className="w-4 h-4 inline mr-1" />
              Predict
            </button>
            {judgeName && (
              <button
                onClick={() => setActiveTab('judge')}
                className={`flex-1 px-4 py-2 text-sm font-mono font-medium uppercase tracking-wide transition-transform ${
                  activeTab === 'judge'
                    ? 'text-steel border-b-2 border-steel bg-surface'
                    : 'text-ink-secondary hover:text-ink hover:translate-x-0.5'
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
                    <h4 className="text-sm font-mono font-semibold text-ink uppercase tracking-wide mb-2 flex items-center gap-1">
                      <Shield className="w-4 h-4 text-critical" />
                      Risk Factors
                    </h4>
                    <div className="space-y-2">
                      {healthScore.risk_factors.slice(0, 3).map((risk, idx) => (
                        <div key={idx} className="p-2 bg-critical/5 border border-critical/30">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-ink">{risk.type}</span>
                            <RiskBadge severity={risk.severity} />
                          </div>
                          <p className="text-xs text-ink-secondary">{risk.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommendations */}
                {healthScore.recommendations && healthScore.recommendations.length > 0 && (
                  <div>
                    <h4 className="text-sm font-mono font-semibold text-ink uppercase tracking-wide mb-2 flex items-center gap-1">
                      <Lightbulb className="w-4 h-4 text-important" />
                      Recommendations
                    </h4>
                    <div className="space-y-2">
                      {healthScore.recommendations.slice(0, 3).map((rec, idx) => (
                        <div
                          key={idx}
                          className={`p-2 border-l-4 ${
                            rec.priority === 0
                              ? 'border-l-fatal bg-fatal/5'
                              : rec.priority === 1
                              ? 'border-l-critical bg-critical/5'
                              : 'border-l-steel bg-steel/5'
                          }`}
                        >
                          <p className="text-sm font-medium text-ink">{rec.action}</p>
                          <p className="text-xs text-ink-secondary mt-0.5">{rec.reasoning}</p>
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
                    <Brain className="w-8 h-8 text-steel mx-auto mb-2" />
                    <p className="text-sm font-mono text-ink-secondary">
                      GENERATING<span className="animate-pulse">_</span>
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="text-center py-4 bg-surface border border-ink/20">
                      <Target className="w-8 h-8 text-steel mx-auto mb-2" />
                      <p className="text-lg font-heading font-bold text-ink">{prediction.predicted_value}</p>
                      <p className="text-sm font-mono text-ink-secondary">
                        {Math.round(prediction.confidence * 100)}% confidence
                      </p>
                      {prediction.lower_bound && prediction.upper_bound && (
                        <p className="text-xs font-mono text-ink-muted mt-1">
                          Range: {prediction.lower_bound} - {prediction.upper_bound}
                        </p>
                      )}
                    </div>

                    {prediction.influencing_factors && prediction.influencing_factors.length > 0 && (
                      <div>
                        <h4 className="text-sm font-mono font-semibold text-ink uppercase tracking-wide mb-2">Key Factors</h4>
                        <div className="space-y-1">
                          {prediction.influencing_factors.map((factor, idx) => (
                            <div key={idx} className="flex items-center justify-between text-sm">
                              <span className="text-ink-secondary">{factor.factor}</span>
                              <span className={`font-mono font-medium ${
                                factor.impact === 'positive' ? 'text-status-success' :
                                factor.impact === 'negative' ? 'text-fatal' : 'text-ink-secondary'
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
                    <Gavel className="w-8 h-8 text-ink/30 mx-auto mb-2" />
                    <p className="text-sm text-ink-secondary">No judge analytics available</p>
                    <p className="text-xs font-mono text-ink-muted mt-1">
                      Judge data will be populated as rulings are tracked
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-3 p-3 bg-surface border border-ink/20">
                      <Scale className="w-8 h-8 text-ink-muted" />
                      <div>
                        <p className="font-heading font-semibold text-ink">{judgeInsight.name}</p>
                        <p className="text-sm font-mono text-ink-secondary">{judgeInsight.court}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      {judgeInsight.avg_ruling_time_days && (
                        <div className="p-3 bg-steel/10 border border-steel/30 text-center">
                          <Clock className="w-5 h-5 text-steel mx-auto mb-1" />
                          <p className="text-lg font-mono font-bold text-ink">{judgeInsight.avg_ruling_time_days}</p>
                          <p className="text-xs font-mono text-ink-secondary uppercase tracking-wide">Avg Days to Rule</p>
                        </div>
                      )}
                      {judgeInsight.motion_stats?.grant_rate !== undefined && (
                        <div className="p-3 bg-status-success/10 border border-status-success/30 text-center">
                          <CheckCircle className="w-5 h-5 text-status-success mx-auto mb-1" />
                          <p className="text-lg font-mono font-bold text-ink">
                            {Math.round(judgeInsight.motion_stats.grant_rate * 100)}%
                          </p>
                          <p className="text-xs font-mono text-ink-secondary uppercase tracking-wide">Motion Grant Rate</p>
                        </div>
                      )}
                    </div>

                    {judgeInsight.preferences?.notable_preferences && (
                      <div>
                        <h4 className="text-sm font-mono font-semibold text-ink uppercase tracking-wide mb-2">Known Preferences</h4>
                        <ul className="text-sm text-ink-secondary space-y-1">
                          {judgeInsight.preferences.notable_preferences.map((pref, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-steel mt-0.5">•</span>
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
          <div className="px-4 pb-4 pt-2 border-t border-ink/20">
            <Link
              href="/intelligence"
              className="flex items-center justify-center gap-2 text-sm text-steel hover:text-ink font-mono font-medium uppercase tracking-wide transition-transform hover:translate-x-0.5"
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
