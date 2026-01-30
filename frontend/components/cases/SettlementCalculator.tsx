'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import {
  Calculator,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Scale,
  Target,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  RefreshCw,
  Info,
} from 'lucide-react';

interface SettlementAnalysis {
  recommended_range: {
    low: number;
    mid: number;
    high: number;
  };
  confidence: number;
  factors: Array<{
    name: string;
    impact: 'positive' | 'negative' | 'neutral';
    weight: number;
    description: string;
  }>;
  comparable_settlements: Array<{
    amount: number;
    case_type: string;
    jurisdiction: string;
    outcome: string;
  }>;
  negotiation_strategy: {
    initial_demand: number;
    walkaway_point: number;
    key_leverage_points: string[];
    potential_concessions: string[];
  };
  risk_assessment: {
    trial_win_probability: number;
    expected_trial_verdict: number;
    litigation_costs_estimate: number;
    time_to_trial_months: number;
  };
  recommendation: string;
}

interface SettlementCalculatorProps {
  caseId: string;
  caseType?: string;
  jurisdiction?: string;
  className?: string;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function ImpactBadge({ impact }: { impact: string }) {
  const config: Record<string, { bg: string; text: string; icon: typeof TrendingUp }> = {
    positive: { bg: 'bg-green-100', text: 'text-green-700', icon: TrendingUp },
    negative: { bg: 'bg-red-100', text: 'text-red-700', icon: TrendingDown },
    neutral: { bg: 'bg-slate-100', text: 'text-slate-700', icon: Scale },
  };

  const { bg, text, icon: Icon } = config[impact] || config.neutral;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${bg} ${text}`}>
      <Icon className="w-3 h-3" />
      {impact}
    </span>
  );
}

export default function SettlementCalculator({
  caseId,
  caseType,
  jurisdiction,
  className = '',
}: SettlementCalculatorProps) {
  const [analysis, setAnalysis] = useState<SettlementAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'range' | 'factors' | 'strategy' | 'risk'>('range');
  const [error, setError] = useState<string | null>(null);

  // Custom inputs for recalculation
  const [customInputs, setCustomInputs] = useState({
    claimed_damages: 0,
    liability_strength: 50,
    documentation_quality: 50,
    opposing_resources: 50,
  });

  const calculateSettlement = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post(`/api/v1/case-intelligence/cases/${caseId}/settlement/calculate`, {
        claimed_damages: customInputs.claimed_damages || undefined,
        liability_strength: customInputs.liability_strength,
        documentation_quality: customInputs.documentation_quality,
        opposing_resources: customInputs.opposing_resources,
        case_type: caseType,
        jurisdiction: jurisdiction,
      });

      setAnalysis(response.data);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Failed to calculate settlement. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`card overflow-hidden ${className}`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg">
            <Calculator className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-slate-900">Settlement Calculator</h3>
            <p className="text-sm text-slate-500">AI-powered settlement analysis</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-green-500" />
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-slate-200">
          {!analysis ? (
            <div className="p-4">
              {/* Input Form */}
              <div className="space-y-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Claimed Damages (optional)
                  </label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="number"
                      value={customInputs.claimed_damages || ''}
                      onChange={(e) =>
                        setCustomInputs({ ...customInputs, claimed_damages: Number(e.target.value) })
                      }
                      placeholder="Enter amount"
                      className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">
                      Liability Strength
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={customInputs.liability_strength}
                      onChange={(e) =>
                        setCustomInputs({ ...customInputs, liability_strength: Number(e.target.value) })
                      }
                      className="w-full"
                    />
                    <p className="text-xs text-center text-slate-600">{customInputs.liability_strength}%</p>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">
                      Documentation Quality
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={customInputs.documentation_quality}
                      onChange={(e) =>
                        setCustomInputs({ ...customInputs, documentation_quality: Number(e.target.value) })
                      }
                      className="w-full"
                    />
                    <p className="text-xs text-center text-slate-600">{customInputs.documentation_quality}%</p>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">
                      Opposing Resources
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={customInputs.opposing_resources}
                      onChange={(e) =>
                        setCustomInputs({ ...customInputs, opposing_resources: Number(e.target.value) })
                      }
                      className="w-full"
                    />
                    <p className="text-xs text-center text-slate-600">{customInputs.opposing_resources}%</p>
                  </div>
                </div>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              <button
                onClick={calculateSettlement}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-medium hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 transition-all"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Calculating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Calculate Settlement Range
                  </>
                )}
              </button>
            </div>
          ) : (
            <div>
              {/* Tabs */}
              <div className="flex border-b border-slate-200 text-xs">
                {(['range', 'factors', 'strategy', 'risk'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`flex-1 px-3 py-2 font-medium capitalize transition-colors ${
                      activeTab === tab
                        ? 'text-green-600 border-b-2 border-green-600 bg-green-50'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="p-4 max-h-96 overflow-y-auto">
                {activeTab === 'range' && (
                  <div className="space-y-4">
                    {/* Settlement Range */}
                    <div className="text-center py-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg">
                      <Target className="w-8 h-8 text-green-500 mx-auto mb-2" />
                      <p className="text-sm text-slate-500 mb-1">Recommended Settlement Range</p>
                      <div className="flex items-center justify-center gap-4">
                        <div>
                          <p className="text-xs text-slate-400">Low</p>
                          <p className="text-lg font-bold text-slate-700">
                            {formatCurrency(analysis.recommended_range.low)}
                          </p>
                        </div>
                        <div className="text-2xl text-slate-300">-</div>
                        <div>
                          <p className="text-xs text-green-600">Target</p>
                          <p className="text-2xl font-bold text-green-600">
                            {formatCurrency(analysis.recommended_range.mid)}
                          </p>
                        </div>
                        <div className="text-2xl text-slate-300">-</div>
                        <div>
                          <p className="text-xs text-slate-400">High</p>
                          <p className="text-lg font-bold text-slate-700">
                            {formatCurrency(analysis.recommended_range.high)}
                          </p>
                        </div>
                      </div>
                      <p className="text-xs text-slate-500 mt-2">
                        {Math.round(analysis.confidence * 100)}% confidence
                      </p>
                    </div>

                    {/* Recommendation */}
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start gap-2">
                        <Info className="w-4 h-4 text-blue-500 mt-0.5" />
                        <p className="text-sm text-blue-800">{analysis.recommendation}</p>
                      </div>
                    </div>

                    {/* Comparable Settlements */}
                    {analysis.comparable_settlements && analysis.comparable_settlements.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 mb-2">
                          Comparable Settlements
                        </h4>
                        <div className="space-y-2">
                          {analysis.comparable_settlements.map((comp, idx) => (
                            <div
                              key={idx}
                              className="flex items-center justify-between p-2 bg-slate-50 rounded"
                            >
                              <div>
                                <p className="text-sm text-slate-700">{comp.case_type}</p>
                                <p className="text-xs text-slate-500">{comp.jurisdiction}</p>
                              </div>
                              <p className="font-medium text-slate-900">
                                {formatCurrency(comp.amount)}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'factors' && (
                  <div className="space-y-3">
                    {analysis.factors.map((factor, idx) => (
                      <div key={idx} className="p-3 bg-slate-50 rounded-lg">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-slate-800">{factor.name}</span>
                          <ImpactBadge impact={factor.impact} />
                        </div>
                        <p className="text-xs text-slate-600 mb-2">{factor.description}</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                factor.impact === 'positive'
                                  ? 'bg-green-500'
                                  : factor.impact === 'negative'
                                  ? 'bg-red-500'
                                  : 'bg-slate-400'
                              }`}
                              style={{ width: `${factor.weight * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500">
                            {Math.round(factor.weight * 100)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'strategy' && analysis.negotiation_strategy && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-green-50 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Initial Demand</p>
                        <p className="text-lg font-bold text-green-600">
                          {formatCurrency(analysis.negotiation_strategy.initial_demand)}
                        </p>
                      </div>
                      <div className="p-3 bg-red-50 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Walk-Away Point</p>
                        <p className="text-lg font-bold text-red-600">
                          {formatCurrency(analysis.negotiation_strategy.walkaway_point)}
                        </p>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-sm font-semibold text-slate-700 mb-2">
                        Key Leverage Points
                      </h4>
                      <ul className="space-y-1">
                        {analysis.negotiation_strategy.key_leverage_points.map((point, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm">
                            <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
                            <span className="text-slate-700">{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h4 className="text-sm font-semibold text-slate-700 mb-2">
                        Potential Concessions
                      </h4>
                      <ul className="space-y-1">
                        {analysis.negotiation_strategy.potential_concessions.map((concession, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm">
                            <AlertCircle className="w-4 h-4 text-yellow-500 mt-0.5" />
                            <span className="text-slate-700">{concession}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {activeTab === 'risk' && analysis.risk_assessment && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-slate-50 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Trial Win Probability</p>
                        <p className="text-2xl font-bold text-slate-800">
                          {Math.round(analysis.risk_assessment.trial_win_probability * 100)}%
                        </p>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Expected Verdict</p>
                        <p className="text-2xl font-bold text-slate-800">
                          {formatCurrency(analysis.risk_assessment.expected_trial_verdict)}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-orange-50 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Est. Litigation Costs</p>
                        <p className="text-lg font-bold text-orange-600">
                          {formatCurrency(analysis.risk_assessment.litigation_costs_estimate)}
                        </p>
                      </div>
                      <div className="p-3 bg-blue-50 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Time to Trial</p>
                        <p className="text-lg font-bold text-blue-600">
                          {analysis.risk_assessment.time_to_trial_months} months
                        </p>
                      </div>
                    </div>

                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-xs text-yellow-800">
                        <strong>Note:</strong> These estimates are based on similar cases and should
                        be used as guidelines only. Actual outcomes may vary based on case-specific
                        factors.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Recalculate Button */}
              <div className="p-3 border-t border-slate-200 bg-slate-50">
                <button
                  onClick={() => setAnalysis(null)}
                  className="w-full flex items-center justify-center gap-2 text-sm text-green-600 hover:text-green-700 font-medium"
                >
                  <RefreshCw className="w-4 h-4" />
                  Recalculate with Different Parameters
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
