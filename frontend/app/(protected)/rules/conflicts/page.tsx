'use client';

/**
 * Rule Conflicts Page
 *
 * Displays and allows resolution of conflicts between Authority Core rules.
 * Conflicts occur when multiple rules have overlapping triggers with different deadlines.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  Filter,
  RefreshCw,
  Scale,
  ArrowLeft,
  Search,
} from 'lucide-react';
import Link from 'next/link';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';
import ConflictCard from '@/components/authority-core/ConflictCard';
import type { RuleConflict, AuthorityRule } from '@/types';

type FilterStatus = 'all' | 'pending' | 'resolved';

export default function RuleConflictsPage() {
  const [conflicts, setConflicts] = useState<RuleConflict[]>([]);
  const [rules, setRules] = useState<Record<string, AuthorityRule>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('pending');
  const [searchQuery, setSearchQuery] = useState('');

  const { showSuccess, showError } = useToast();

  const fetchConflicts = useCallback(async () => {
    setIsLoading(true);
    try {
      const statusParam = filterStatus === 'all' ? '' : `?status=${filterStatus}`;
      const response = await apiClient.get(`/authority-core/conflicts${statusParam}`);
      setConflicts(response.data);

      // Fetch rules for all conflicts
      const ruleIds = new Set<string>();
      response.data.forEach((c: RuleConflict) => {
        if (c.rule_a_id) ruleIds.add(c.rule_a_id);
        if (c.rule_b_id) ruleIds.add(c.rule_b_id);
      });

      const rulesMap: Record<string, AuthorityRule> = {};
      await Promise.all(
        Array.from(ruleIds).map(async (id) => {
          try {
            const ruleResponse = await apiClient.get(`/authority-core/rules/${id}`);
            rulesMap[id] = ruleResponse.data;
          } catch (err) {
            console.error(`Failed to fetch rule ${id}:`, err);
          }
        })
      );
      setRules(rulesMap);
    } catch (err) {
      console.error('Failed to fetch conflicts:', err);
      showError('Failed to load conflicts');
    } finally {
      setIsLoading(false);
    }
  }, [filterStatus, showError]);

  useEffect(() => {
    fetchConflicts();
  }, [fetchConflicts]);

  const handleResolve = async (conflictId: string, resolution: string, winningRuleId?: string) => {
    try {
      await apiClient.post(`/authority-core/conflicts/${conflictId}/resolve`, {
        resolution,
        winning_rule_id: winningRuleId,
      });
      showSuccess('Conflict resolved');
      fetchConflicts();
    } catch (err) {
      console.error('Failed to resolve conflict:', err);
      showError('Failed to resolve conflict');
      throw err;
    }
  };

  // Filter conflicts by search query
  const filteredConflicts = conflicts.filter((conflict) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const ruleA = rules[conflict.rule_a_id];
    const ruleB = rules[conflict.rule_b_id];
    return (
      conflict.description?.toLowerCase().includes(query) ||
      conflict.conflict_type?.toLowerCase().includes(query) ||
      ruleA?.rule_name?.toLowerCase().includes(query) ||
      ruleB?.rule_name?.toLowerCase().includes(query) ||
      ruleA?.citation?.toLowerCase().includes(query) ||
      ruleB?.citation?.toLowerCase().includes(query)
    );
  });

  const pendingCount = conflicts.filter((c) => !c.resolution || c.resolution === 'pending').length;
  const resolvedCount = conflicts.filter((c) => c.resolution && c.resolution !== 'pending').length;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4">
            <div className="flex items-center gap-4 mb-4">
              <Link
                href="/rules/database"
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Rule Conflicts</h1>
                <p className="text-sm text-slate-500">
                  Review and resolve conflicts between Authority Core rules
                </p>
              </div>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-6 mb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <span className="text-sm">
                  <span className="font-semibold text-slate-900">{pendingCount}</span>
                  <span className="text-slate-500"> pending</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-500" />
                <span className="text-sm">
                  <span className="font-semibold text-slate-900">{resolvedCount}</span>
                  <span className="text-slate-500"> resolved</span>
                </span>
              </div>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4">
              {/* Search */}
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search conflicts..."
                  className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
                {(['pending', 'resolved', 'all'] as FilterStatus[]).map((status) => (
                  <button
                    key={status}
                    onClick={() => setFilterStatus(status)}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                      filterStatus === status
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </button>
                ))}
              </div>

              {/* Refresh */}
              <button
                onClick={fetchConflicts}
                disabled={isLoading}
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        ) : filteredConflicts.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
            <Scale className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">
              {filterStatus === 'pending' ? 'No Pending Conflicts' : 'No Conflicts Found'}
            </h3>
            <p className="text-slate-500 max-w-md mx-auto">
              {filterStatus === 'pending'
                ? 'All rule conflicts have been resolved. Great job!'
                : searchQuery
                ? 'Try adjusting your search query.'
                : 'No conflicts detected between your Authority Core rules.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredConflicts.map((conflict) => (
              <ConflictCard
                key={conflict.id}
                conflict={conflict}
                ruleA={rules[conflict.rule_a_id]}
                ruleB={rules[conflict.rule_b_id]}
                onResolve={handleResolve}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
