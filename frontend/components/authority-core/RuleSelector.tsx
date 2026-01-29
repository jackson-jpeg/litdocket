'use client';

/**
 * RuleSelector Component
 *
 * A searchable dropdown for selecting Authority Core rules when creating deadlines.
 * Used in manual deadline creation to "Apply Rule" from the database.
 *
 * Features:
 * - Search by keyword
 * - Filter by jurisdiction
 * - Shows rule details on hover/select
 * - Returns selected rule for deadline calculation
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Scale,
  FileText,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Clock,
  X,
  Database,
  RefreshCw,
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import { AuthorityRule, DeadlineSpec } from '@/types';

interface RuleSelectorProps {
  jurisdictionId?: string;
  triggerType?: string;
  onSelect: (rule: AuthorityRule) => void;
  onCancel?: () => void;
  selectedRuleId?: string;
}

export default function RuleSelector({
  jurisdictionId,
  triggerType,
  onSelect,
  onCancel,
  selectedRuleId,
}: RuleSelectorProps) {
  const [rules, setRules] = useState<AuthorityRule[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedRuleId, setExpandedRuleId] = useState<string | null>(null);

  const fetchRules = useCallback(async () => {
    setIsLoading(true);
    try {
      let url = '/api/v1/authority-core/rules';
      const params: string[] = [];

      if (searchQuery.trim()) {
        url = '/api/v1/authority-core/rules/search';
        params.push(`q=${encodeURIComponent(searchQuery.trim())}`);
      }

      if (jurisdictionId) {
        params.push(`jurisdiction_id=${jurisdictionId}`);
      }

      if (triggerType) {
        params.push(`trigger_type=${triggerType}`);
      }

      params.push('limit=50');

      if (params.length > 0) {
        url += '?' + params.join('&');
      }

      const response = await apiClient.get(url);
      setRules(response.data);
    } catch (err) {
      console.error('Failed to fetch rules:', err);
      setRules([]);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, jurisdictionId, triggerType]);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchRules();
  };

  const handleSelect = (rule: AuthorityRule) => {
    onSelect(rule);
  };

  const toggleExpand = (ruleId: string) => {
    setExpandedRuleId(expandedRuleId === ruleId ? null : ruleId);
  };

  const tierColors: Record<string, string> = {
    federal: 'bg-purple-100 text-purple-700',
    state: 'bg-blue-100 text-blue-700',
    local: 'bg-green-100 text-green-700',
    standing_order: 'bg-amber-100 text-amber-700',
    firm: 'bg-slate-100 text-slate-700',
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="w-5 h-5 text-blue-600" />
          <span className="font-medium text-slate-900">Select a Rule</span>
        </div>
        {onCancel && (
          <button
            onClick={onCancel}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Search */}
      <div className="p-3 border-b border-slate-200">
        <form onSubmit={handleSearchSubmit}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearch}
              placeholder="Search rules..."
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </form>
      </div>

      {/* Rules List */}
      <div className="max-h-[400px] overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
          </div>
        ) : rules.length === 0 ? (
          <div className="py-8 text-center">
            <Database className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-slate-500 text-sm">No rules found</p>
            <p className="text-slate-400 text-xs mt-1">
              {searchQuery ? 'Try a different search term' : 'No rules available for this jurisdiction'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {rules.map((rule) => (
              <div key={rule.id} className="group">
                {/* Rule Summary */}
                <div
                  className={`px-4 py-3 hover:bg-slate-50 cursor-pointer transition-colors ${
                    selectedRuleId === rule.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div
                      className="flex-1 min-w-0"
                      onClick={() => handleSelect(rule)}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-slate-900 truncate">{rule.rule_name}</p>
                        <span className={`flex-shrink-0 px-2 py-0.5 text-xs font-medium rounded-full ${tierColors[rule.authority_tier]}`}>
                          {rule.authority_tier}
                        </span>
                      </div>
                      <p className="text-sm text-blue-600 truncate">{rule.citation || rule.rule_code}</p>
                      <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5" />
                          {rule.deadlines.length} deadlines
                        </span>
                        {rule.is_verified && (
                          <span className="flex items-center gap-1 text-green-600">
                            <CheckCircle className="w-3.5 h-3.5" />
                            Verified
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpand(rule.id);
                      }}
                      className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 ml-2"
                    >
                      {expandedRuleId === rule.id ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedRuleId === rule.id && (
                  <div className="px-4 py-3 bg-slate-50 border-t border-slate-100">
                    <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">
                      Deadlines
                    </h4>
                    <div className="space-y-2">
                      {rule.deadlines.map((deadline: DeadlineSpec, idx: number) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between bg-white rounded-lg p-2.5 border border-slate-200 text-sm"
                        >
                          <span className="text-slate-900">{deadline.title}</span>
                          <div className="flex items-center gap-3 text-slate-500">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5" />
                              {deadline.days_from_trigger > 0 ? '+' : ''}{deadline.days_from_trigger}d
                            </span>
                            <span className={`px-2 py-0.5 text-xs rounded-full ${
                              deadline.priority === 'fatal' ? 'bg-red-100 text-red-700' :
                              deadline.priority === 'critical' ? 'bg-amber-100 text-amber-700' :
                              'bg-slate-100 text-slate-600'
                            }`}>
                              {deadline.priority}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>

                    <button
                      onClick={() => handleSelect(rule)}
                      className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Apply This Rule
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      {rules.length > 0 && (
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 text-center">
          Click a rule to select it, or expand for details
        </div>
      )}
    </div>
  );
}
