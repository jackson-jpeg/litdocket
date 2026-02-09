/**
 * Inbox Analytics Dashboard
 *
 * Phase 5: Multi-Jurisdiction Scaling - Attorney Performance Tracking
 *
 * Features:
 * - Throughput metrics (items reviewed per day/week)
 * - Attorney leaderboard (gamification)
 * - Review time analytics
 * - Confidence score distribution
 * - Approval/rejection ratios
 * - Bottleneck identification
 */

'use client';

import React, { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';

interface InboxStats {
  total_items: number;
  pending: number;
  reviewed: number;
  deferred: number;
  average_review_time_minutes: number;
  approval_rate: number;
  rejection_rate: number;
  deferral_rate: number;
}

interface AttorneyStats {
  attorney_id: string;
  attorney_name: string;
  items_reviewed: number;
  approval_count: number;
  rejection_count: number;
  average_review_time_minutes: number;
  confidence_threshold: number;
  last_review_at: string;
}

interface ConfidenceDistribution {
  confidence_range: string;
  count: number;
  approval_rate: number;
}

export default function InboxAnalyticsDashboard() {
  const [stats, setStats] = useState<InboxStats | null>(null);
  const [attorneys, setAttorneys] = useState<AttorneyStats[]>([]);
  const [distribution, setDistribution] = useState<ConfidenceDistribution[]>([]);
  const [timeRange, setTimeRange] = useState<'today' | 'week' | 'month' | 'all'>('week');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [timeRange]);

  const loadAnalytics = async () => {
    try {
      // Mock data - would come from backend
      const mockStats: InboxStats = {
        total_items: 450,
        pending: 125,
        reviewed: 300,
        deferred: 25,
        average_review_time_minutes: 4.2,
        approval_rate: 0.78,
        rejection_rate: 0.15,
        deferral_rate: 0.07
      };

      const mockAttorneys: AttorneyStats[] = [
        {
          attorney_id: '1',
          attorney_name: 'Sarah Johnson',
          items_reviewed: 85,
          approval_count: 72,
          rejection_count: 10,
          average_review_time_minutes: 3.8,
          confidence_threshold: 0.85,
          last_review_at: new Date().toISOString()
        },
        {
          attorney_id: '2',
          attorney_name: 'Michael Chen',
          items_reviewed: 67,
          approval_count: 58,
          rejection_count: 7,
          average_review_time_minutes: 4.5,
          confidence_threshold: 0.88,
          last_review_at: new Date().toISOString()
        },
        {
          attorney_id: '3',
          attorney_name: 'Emily Rodriguez',
          items_reviewed: 52,
          approval_count: 45,
          rejection_count: 5,
          average_review_time_minutes: 5.2,
          confidence_threshold: 0.82,
          last_review_at: new Date().toISOString()
        }
      ];

      const mockDistribution: ConfidenceDistribution[] = [
        { confidence_range: '≥95% (High)', count: 125, approval_rate: 0.96 },
        { confidence_range: '85-95% (Medium-High)', count: 180, approval_rate: 0.85 },
        { confidence_range: '70-85% (Medium)', count: 95, approval_rate: 0.62 },
        { confidence_range: '<70% (Low)', count: 50, approval_rate: 0.38 }
      ];

      setStats(mockStats);
      setAttorneys(mockAttorneys);
      setDistribution(mockDistribution);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load inbox analytics:', error);
      setLoading(false);
    }
  };

  if (loading || !stats) {
    return <div className="p-8 text-center">Loading analytics...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-ink">Inbox Analytics</h1>
            <p className="text-gray-600 mt-1">Attorney performance and review metrics</p>
          </div>
          <div className="flex gap-2">
            {(['today', 'week', 'month', 'all'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-4 py-2 border-2 font-medium ${
                  timeRange === range
                    ? 'border-ink bg-ink text-white'
                    : 'border-gray-300 bg-white hover:bg-gray-50'
                }`}
              >
                {range.charAt(0).toUpperCase() + range.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-4 gap-px bg-ink mb-6">
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">TOTAL ITEMS</p>
            <p className="text-3xl font-bold text-ink">{stats.total_items}</p>
            <p className="text-xs text-gray-600 mt-1">{stats.pending} pending</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">REVIEWED</p>
            <p className="text-3xl font-bold text-ink">{stats.reviewed}</p>
            <p className="text-xs text-gray-600 mt-1">{((stats.reviewed / stats.total_items) * 100).toFixed(0)}% completion</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">AVG REVIEW TIME</p>
            <p className="text-3xl font-bold text-ink">{stats.average_review_time_minutes.toFixed(1)}m</p>
            <p className="text-xs text-gray-600 mt-1">Per item</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">APPROVAL RATE</p>
            <p className="text-3xl font-bold text-ink">{(stats.approval_rate * 100).toFixed(0)}%</p>
            <p className="text-xs text-gray-600 mt-1">{(stats.rejection_rate * 100).toFixed(0)}% rejected</p>
          </div>
        </div>

        {/* Attorney Leaderboard */}
        <div className="bg-white border-2 border-ink mb-6">
          <div className="border-b-2 border-ink bg-gray-50 px-4 py-3">
            <h2 className="font-semibold text-ink">Attorney Leaderboard 🏆</h2>
            <p className="text-sm text-gray-600 mt-0.5">Top performers this {timeRange}</p>
          </div>
          <div className="divide-y-2 divide-ink">
            {attorneys.map((attorney, index) => {
              const approvalRate = attorney.items_reviewed > 0
                ? (attorney.approval_count / attorney.items_reviewed * 100)
                : 0;

              return (
                <div key={attorney.attorney_id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {/* Rank Badge */}
                      <div className={`w-12 h-12 flex items-center justify-center text-xl font-bold ${
                        index === 0 ? 'bg-yellow-100 text-yellow-700 border-2 border-yellow-400' :
                        index === 1 ? 'bg-gray-100 text-gray-700 border-2 border-gray-400' :
                        index === 2 ? 'bg-orange-100 text-orange-700 border-2 border-orange-400' :
                        'bg-gray-50 text-gray-600 border-2 border-gray-300'
                      }`}>
                        #{index + 1}
                      </div>

                      {/* Attorney Info */}
                      <div>
                        <h3 className="font-medium text-ink">{attorney.attorney_name}</h3>
                        <p className="text-sm text-gray-600 mt-0.5">
                          {attorney.items_reviewed} items reviewed · Avg {attorney.average_review_time_minutes.toFixed(1)}m per item
                        </p>
                      </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="flex gap-8 text-sm">
                      <div className="text-right">
                        <p className="text-xs text-gray-500">APPROVALS</p>
                        <p className="font-semibold text-green-600">{attorney.approval_count}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-500">REJECTIONS</p>
                        <p className="font-semibold text-red-600">{attorney.rejection_count}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-500">APPROVAL RATE</p>
                        <p className="font-semibold text-ink">{approvalRate.toFixed(0)}%</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-500">THRESHOLD</p>
                        <p className="font-semibold text-ink">{(attorney.confidence_threshold * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Confidence Distribution */}
        <div className="bg-white border-2 border-ink mb-6">
          <div className="border-b-2 border-ink bg-gray-50 px-4 py-3">
            <h2 className="font-semibold text-ink">Confidence Score Distribution</h2>
            <p className="text-sm text-gray-600 mt-0.5">Rule extraction quality by confidence range</p>
          </div>
          <div className="p-4">
            {/* Bar Chart */}
            <div className="space-y-4">
              {distribution.map((range) => {
                const maxCount = Math.max(...distribution.map(d => d.count));
                const width = (range.count / maxCount) * 100;

                return (
                  <div key={range.confidence_range}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-ink">{range.confidence_range}</span>
                      <span className="text-sm text-gray-600">{range.count} items</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-8 bg-gray-100 border-2 border-gray-300 relative">
                        <div
                          className={`h-full transition-all duration-300 ${
                            range.confidence_range.includes('High') ? 'bg-green-500' :
                            range.confidence_range.includes('Medium-High') ? 'bg-yellow-500' :
                            range.confidence_range.includes('Medium') ? 'bg-orange-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${width}%` }}
                        />
                      </div>
                      <div className="w-24 text-right">
                        <span className="text-sm font-semibold text-ink">
                          {(range.approval_rate * 100).toFixed(0)}% approved
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Insights */}
            <div className="mt-6 p-4 bg-blue-50 border-l-4 border-blue-500">
              <p className="text-sm font-semibold text-blue-900 mb-1">💡 Insights</p>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• High-confidence rules (≥95%) have a {(distribution[0].approval_rate * 100).toFixed(0)}% approval rate</li>
                <li>• {distribution[distribution.length - 1].count} low-confidence rules require careful review</li>
                <li>• Consider auto-approving rules above {Math.round(stats.approval_rate * 100)}% threshold</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Processing Speed Chart */}
        <div className="grid grid-cols-2 gap-px bg-ink">
          <div className="bg-white p-6">
            <h3 className="font-semibold text-ink mb-4">Review Time Distribution</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">0-3 minutes (Fast)</span>
                <span className="font-semibold text-green-600">45%</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">3-5 minutes (Normal)</span>
                <span className="font-semibold text-blue-600">35%</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">5-10 minutes (Slow)</span>
                <span className="font-semibold text-yellow-600">15%</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">&gt;10 minutes (Very Slow)</span>
                <span className="font-semibold text-red-600">5%</span>
              </div>
            </div>
          </div>

          <div className="bg-white p-6">
            <h3 className="font-semibold text-ink mb-4">Resolution Breakdown</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Approved</span>
                <span className="font-semibold text-green-600">{(stats.approval_rate * 100).toFixed(0)}%</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Rejected</span>
                <span className="font-semibold text-red-600">{(stats.rejection_rate * 100).toFixed(0)}%</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Deferred</span>
                <span className="font-semibold text-yellow-600">{(stats.deferral_rate * 100).toFixed(0)}%</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Pending</span>
                <span className="font-semibold text-gray-600">{((stats.pending / stats.total_items) * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
