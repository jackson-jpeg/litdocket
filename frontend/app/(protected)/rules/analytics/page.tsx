'use client';

/**
 * Rules Analytics Dashboard
 *
 * Provides comprehensive analytics for Authority Core:
 * - Most used rules with usage counts
 * - Rules by jurisdiction with verification status
 * - Rules by authority tier
 * - Proposal approval/rejection rates
 * - Conflict resolution metrics
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  RefreshCw,
  TrendingUp,
  Building2,
  Layers,
  FileCheck,
  AlertTriangle,
  BarChart3,
  PieChart,
  Scale,
  CheckCircle,
  XCircle,
  Clock,
  ChevronRight,
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface RuleUsageStats {
  rule_id: string;
  rule_name: string;
  rule_code: string;
  jurisdiction_name: string | null;
  usage_count: number;
  deadlines_generated: number;
}

interface JurisdictionStats {
  jurisdiction_id: string;
  jurisdiction_name: string;
  rule_count: number;
  verified_count: number;
  pending_proposals: number;
}

interface TierStats {
  tier: string;
  rule_count: number;
  usage_count: number;
}

interface ProposalStats {
  total_proposals: number;
  pending: number;
  approved: number;
  rejected: number;
  needs_revision: number;
  approval_rate: number;
}

interface ConflictStats {
  total_conflicts: number;
  pending: number;
  auto_resolved: number;
  manually_resolved: number;
  ignored: number;
}

interface AnalyticsData {
  most_used_rules: RuleUsageStats[];
  rules_by_jurisdiction: JurisdictionStats[];
  rules_by_tier: TierStats[];
  proposal_stats: ProposalStats;
  conflict_stats: ConflictStats;
  total_rules: number;
  total_verified_rules: number;
}

function StatCard({ title, value, subtitle, icon, color }: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'amber' | 'red' | 'purple' | 'slate';
}) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    slate: 'bg-slate-50 text-slate-600',
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
          {subtitle && (
            <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colors[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function TierBadge({ tier }: { tier: string }) {
  const styles: Record<string, string> = {
    federal: 'bg-blue-100 text-blue-700',
    state: 'bg-green-100 text-green-700',
    local: 'bg-amber-100 text-amber-700',
    standing_order: 'bg-purple-100 text-purple-700',
    firm: 'bg-slate-100 text-slate-700',
  };

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${styles[tier] || styles.firm}`}>
      {tier.replace('_', ' ')}
    </span>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const percentage = max > 0 ? (value / max) * 100 : 0;

  return (
    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
      <div
        className={`h-full ${color} transition-all duration-500`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

export default function AnalyticsPage() {
  const router = useRouter();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<AnalyticsData>('/authority-core/analytics');
      setData(response.data);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setError('Failed to load analytics data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <p className="text-lg font-medium text-slate-900">{error || 'Failed to load data'}</p>
          <button
            onClick={fetchAnalytics}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const maxRuleCount = Math.max(...data.rules_by_jurisdiction.map(j => j.rule_count), 1);
  const maxUsage = Math.max(...data.most_used_rules.map(r => r.usage_count), 1);

  return (
    <div className="min-h-screen bg-slate-50 pb-12">
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/rules')}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Rules Analytics</h1>
                <p className="text-slate-500">Authority Core usage and performance metrics</p>
              </div>
            </div>
            <button
              onClick={fetchAnalytics}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Top Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Total Rules"
            value={data.total_rules}
            subtitle={`${data.total_verified_rules} verified`}
            icon={<Scale className="w-6 h-6" />}
            color="blue"
          />
          <StatCard
            title="Pending Proposals"
            value={data.proposal_stats.pending}
            subtitle="awaiting review"
            icon={<Clock className="w-6 h-6" />}
            color="amber"
          />
          <StatCard
            title="Approval Rate"
            value={`${data.proposal_stats.approval_rate}%`}
            subtitle={`${data.proposal_stats.approved} approved`}
            icon={<CheckCircle className="w-6 h-6" />}
            color="green"
          />
          <StatCard
            title="Active Conflicts"
            value={data.conflict_stats.pending}
            subtitle="need resolution"
            icon={<AlertTriangle className="w-6 h-6" />}
            color="red"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Most Used Rules */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                <h2 className="text-lg font-semibold text-slate-900">Most Used Rules</h2>
              </div>
            </div>
            <div className="divide-y divide-slate-100">
              {data.most_used_rules.length === 0 ? (
                <div className="px-6 py-8 text-center text-slate-500">
                  No usage data yet
                </div>
              ) : (
                data.most_used_rules.slice(0, 5).map((rule, idx) => (
                  <div key={rule.rule_id} className="px-6 py-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-start gap-3">
                        <span className="w-6 h-6 flex items-center justify-center bg-blue-100 text-blue-700 text-xs font-bold rounded">
                          {idx + 1}
                        </span>
                        <div>
                          <p className="font-medium text-slate-900">{rule.rule_name}</p>
                          <p className="text-sm text-slate-500">{rule.jurisdiction_name || rule.rule_code}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-slate-900">{rule.usage_count}</p>
                        <p className="text-xs text-slate-500">uses</p>
                      </div>
                    </div>
                    <ProgressBar value={rule.usage_count} max={maxUsage} color="bg-blue-500" />
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Rules by Tier */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-purple-600" />
                <h2 className="text-lg font-semibold text-slate-900">Rules by Authority Tier</h2>
              </div>
            </div>
            <div className="p-6">
              {data.rules_by_tier.length === 0 ? (
                <div className="py-8 text-center text-slate-500">
                  No rules yet
                </div>
              ) : (
                <div className="space-y-4">
                  {data.rules_by_tier.map((tier) => (
                    <div key={tier.tier} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <TierBadge tier={tier.tier} />
                        <span className="text-sm text-slate-600">
                          {tier.rule_count} rules
                        </span>
                      </div>
                      <span className="text-sm font-medium text-slate-900">
                        {tier.usage_count} uses
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Rules by Jurisdiction */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-green-600" />
                <h2 className="text-lg font-semibold text-slate-900">Rules by Jurisdiction</h2>
              </div>
            </div>
            <div className="divide-y divide-slate-100 max-h-[400px] overflow-y-auto">
              {data.rules_by_jurisdiction.length === 0 ? (
                <div className="px-6 py-8 text-center text-slate-500">
                  No jurisdictions with rules
                </div>
              ) : (
                data.rules_by_jurisdiction.map((jur) => (
                  <div key={jur.jurisdiction_id} className="px-6 py-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-medium text-slate-900">{jur.jurisdiction_name}</p>
                      <div className="flex items-center gap-2">
                        {jur.pending_proposals > 0 && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700 rounded-full">
                            {jur.pending_proposals} pending
                          </span>
                        )}
                        <span className="text-sm font-semibold text-slate-900">
                          {jur.rule_count}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <ProgressBar value={jur.rule_count} max={maxRuleCount} color="bg-green-500" />
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {jur.verified_count}/{jur.rule_count} verified
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Proposal & Conflict Stats */}
          <div className="space-y-8">
            {/* Proposal Stats */}
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-5 h-5 text-amber-600" />
                  <h2 className="text-lg font-semibold text-slate-900">Proposal Statistics</h2>
                </div>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className="text-2xl font-bold text-slate-900">{data.proposal_stats.total_proposals}</p>
                    <p className="text-sm text-slate-500">Total</p>
                  </div>
                  <div className="text-center p-3 bg-green-50 rounded-lg">
                    <p className="text-2xl font-bold text-green-700">{data.proposal_stats.approval_rate}%</p>
                    <p className="text-sm text-green-600">Approval Rate</p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm text-slate-600">
                      <Clock className="w-4 h-4 text-amber-500" /> Pending
                    </span>
                    <span className="font-medium">{data.proposal_stats.pending}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm text-slate-600">
                      <CheckCircle className="w-4 h-4 text-green-500" /> Approved
                    </span>
                    <span className="font-medium">{data.proposal_stats.approved}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm text-slate-600">
                      <XCircle className="w-4 h-4 text-red-500" /> Rejected
                    </span>
                    <span className="font-medium">{data.proposal_stats.rejected}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm text-slate-600">
                      <AlertTriangle className="w-4 h-4 text-blue-500" /> Needs Revision
                    </span>
                    <span className="font-medium">{data.proposal_stats.needs_revision}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Conflict Stats */}
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                    <h2 className="text-lg font-semibold text-slate-900">Conflict Resolution</h2>
                  </div>
                  {data.conflict_stats.pending > 0 && (
                    <button
                      onClick={() => router.push('/rules/conflicts')}
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                    >
                      View <ChevronRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className="text-2xl font-bold text-slate-900">{data.conflict_stats.total_conflicts}</p>
                    <p className="text-sm text-slate-500">Total</p>
                  </div>
                  <div className="text-center p-3 bg-red-50 rounded-lg">
                    <p className="text-2xl font-bold text-red-700">{data.conflict_stats.pending}</p>
                    <p className="text-sm text-red-600">Pending</p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Auto-resolved (tier precedence)</span>
                    <span className="font-medium">{data.conflict_stats.auto_resolved}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Manually resolved</span>
                    <span className="font-medium">{data.conflict_stats.manually_resolved}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Ignored</span>
                    <span className="font-medium">{data.conflict_stats.ignored}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
