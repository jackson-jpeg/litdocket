'use client';

/**
 * Rules Database Browser
 *
 * Browse and search verified rules in the Authority Core database.
 * Features:
 * - Search by keyword, jurisdiction, trigger type
 * - Filter by authority tier
 * - View rule details with deadline specifications
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Database,
  Search,
  Filter,
  CheckCircle,
  Scale,
  FileText,
  ChevronRight,
  RefreshCw,
  ArrowLeft,
  Globe,
  Clock,
  Calendar,
  BookOpen,
  Info,
  AlertTriangle,
} from 'lucide-react';
import Link from 'next/link';
import apiClient from '@/lib/api-client';
import { AuthorityRule, DeadlineSpec } from '@/types';

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
}

const TRIGGER_TYPES = [
  { value: '', label: 'All Triggers' },
  { value: 'case_filed', label: 'Case Filed' },
  { value: 'complaint_served', label: 'Complaint Served' },
  { value: 'motion_filed', label: 'Motion Filed' },
  { value: 'discovery_deadline', label: 'Discovery Deadline' },
  { value: 'trial_date', label: 'Trial Date' },
  { value: 'pretrial_conference', label: 'Pretrial Conference' },
  { value: 'hearing_scheduled', label: 'Hearing Scheduled' },
  { value: 'appeal_filed', label: 'Appeal Filed' },
];

const AUTHORITY_TIERS = [
  { value: '', label: 'All Tiers' },
  { value: 'federal', label: 'Federal' },
  { value: 'state', label: 'State' },
  { value: 'local', label: 'Local' },
  { value: 'standing_order', label: 'Standing Order' },
  { value: 'firm', label: 'Firm' },
];

function RuleDetailModal({ rule, onClose }: { rule: AuthorityRule; onClose: () => void }) {
  const tierColors: Record<string, string> = {
    federal: 'bg-purple-100 text-purple-700',
    state: 'bg-blue-100 text-blue-700',
    local: 'bg-green-100 text-green-700',
    standing_order: 'bg-amber-100 text-amber-700',
    firm: 'bg-slate-100 text-slate-700',
  };

  const priorityColors: Record<string, string> = {
    fatal: 'bg-red-100 text-red-700 border-red-200',
    critical: 'bg-amber-100 text-amber-700 border-amber-200',
    important: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    standard: 'bg-slate-100 text-slate-600 border-slate-200',
    informational: 'bg-blue-50 text-blue-600 border-blue-200',
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-lg font-semibold text-slate-900">{rule.rule_name}</h2>
                <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${tierColors[rule.authority_tier]}`}>
                  {rule.authority_tier}
                </span>
              </div>
              <p className="text-sm text-blue-600">{rule.citation || rule.rule_code}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
            >
              <Scale className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Jurisdiction</p>
              <p className="font-medium text-slate-900">{rule.jurisdiction_name || 'Not specified'}</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Trigger Type</p>
              <p className="font-medium text-slate-900">{rule.trigger_type.replace(/_/g, ' ')}</p>
            </div>
          </div>

          {/* Deadlines */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-3">
              Deadline Specifications ({rule.deadlines.length})
            </h3>
            <div className="space-y-3">
              {rule.deadlines.map((deadline: DeadlineSpec, idx: number) => (
                <div
                  key={idx}
                  className={`rounded-lg p-4 border ${priorityColors[deadline.priority] || priorityColors.standard}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-slate-900">{deadline.title}</span>
                    <span className="text-xs font-medium uppercase">{deadline.priority}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1.5 text-slate-600">
                      <Clock className="w-4 h-4" />
                      {deadline.days_from_trigger > 0 ? '+' : ''}{deadline.days_from_trigger} days
                    </span>
                    <span className="flex items-center gap-1.5 text-slate-600">
                      <Calendar className="w-4 h-4" />
                      {deadline.calculation_method.replace(/_/g, ' ')}
                    </span>
                    {deadline.party_responsible && (
                      <span className="text-slate-500">
                        {deadline.party_responsible}
                      </span>
                    )}
                  </div>
                  {deadline.description && (
                    <p className="mt-2 text-sm text-slate-600">{deadline.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Service Extensions */}
          {rule.service_extensions && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-3">
                Service Extensions
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-slate-900">+{rule.service_extensions.mail}</p>
                  <p className="text-sm text-slate-500">Mail</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-slate-900">+{rule.service_extensions.electronic}</p>
                  <p className="text-sm text-slate-500">Electronic</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-slate-900">+{rule.service_extensions.personal}</p>
                  <p className="text-sm text-slate-500">Personal</p>
                </div>
              </div>
            </div>
          )}

          {/* Source */}
          {(rule.source_url || rule.source_text) && (
            <div>
              <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-3">
                Source
              </h3>
              {rule.source_url && (
                <a
                  href={rule.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline block mb-2"
                >
                  {rule.source_url}
                </a>
              )}
              {rule.source_text && (
                <div className="bg-slate-50 rounded-lg p-4 max-h-40 overflow-y-auto">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">{rule.source_text}</p>
                </div>
              )}
            </div>
          )}

          {/* Verification */}
          <div className="mt-6 pt-6 border-t border-slate-200">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                {rule.is_verified ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-green-600">Verified</span>
                    {rule.verified_at && (
                      <span className="text-slate-400">
                        on {new Date(rule.verified_at).toLocaleDateString()}
                      </span>
                    )}
                  </>
                ) : (
                  <span className="text-amber-600">Pending verification</span>
                )}
              </div>
              {rule.confidence_score !== undefined && (
                <span className="text-slate-500">
                  {Math.round(rule.confidence_score * 100)}% confidence
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function RuleCard({ rule, onSelect }: { rule: AuthorityRule; onSelect: () => void }) {
  const tierColors: Record<string, string> = {
    federal: 'bg-purple-100 text-purple-700',
    state: 'bg-blue-100 text-blue-700',
    local: 'bg-green-100 text-green-700',
    standing_order: 'bg-amber-100 text-amber-700',
    firm: 'bg-slate-100 text-slate-700',
  };

  return (
    <div
      onClick={onSelect}
      className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-slate-900 truncate">{rule.rule_name}</p>
          <p className="text-sm text-blue-600 truncate">{rule.citation || rule.rule_code}</p>
        </div>
        <span className={`flex-shrink-0 ml-2 px-2.5 py-1 text-xs font-medium rounded-full ${tierColors[rule.authority_tier]}`}>
          {rule.authority_tier}
        </span>
      </div>

      <div className="flex items-center gap-4 text-sm text-slate-500 mb-3">
        <span>{rule.jurisdiction_name || 'Unknown'}</span>
        <span>{rule.trigger_type.replace(/_/g, ' ')}</span>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1.5 text-slate-600">
            <FileText className="w-4 h-4" />
            {rule.deadlines.length} deadlines
          </span>
          {rule.is_verified && (
            <span className="flex items-center gap-1 text-green-600">
              <CheckCircle className="w-3.5 h-3.5" />
              Verified
            </span>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </div>
    </div>
  );
}

export default function RulesDatabasePage() {
  const router = useRouter();
  const [rules, setRules] = useState<AuthorityRule[]>([]);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRule, setSelectedRule] = useState<AuthorityRule | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedJurisdiction, setSelectedJurisdiction] = useState('');
  const [selectedTrigger, setSelectedTrigger] = useState('');
  const [selectedTier, setSelectedTier] = useState('');

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [rulesRes, jurisdictionsRes] = await Promise.all([
        apiClient.get('/api/v1/authority-core/rules?limit=200'),
        apiClient.get('/api/v1/jurisdictions'),
      ]);
      setRules(rulesRes.data);
      setJurisdictions(jurisdictionsRes.data);
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSearch = async () => {
    setIsLoading(true);
    try {
      let url = '/api/v1/authority-core/rules';
      const params: string[] = [];

      if (searchQuery.trim()) {
        url = '/api/v1/authority-core/rules/search';
        params.push(`q=${encodeURIComponent(searchQuery.trim())}`);
      }

      if (selectedJurisdiction) {
        params.push(`jurisdiction_id=${selectedJurisdiction}`);
      }

      if (selectedTrigger) {
        params.push(`trigger_type=${selectedTrigger}`);
      }

      if (params.length > 0) {
        url += '?' + params.join('&');
      }

      const response = await apiClient.get(url);
      let filteredRules = response.data;

      // Client-side filter by tier (API may not support this filter)
      if (selectedTier) {
        filteredRules = filteredRules.filter((r: AuthorityRule) => r.authority_tier === selectedTier);
      }

      setRules(filteredRules);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedJurisdiction('');
    setSelectedTrigger('');
    setSelectedTier('');
    fetchData();
  };

  const hasFilters = searchQuery || selectedJurisdiction || selectedTrigger || selectedTier;

  return (
    <div className="min-h-screen bg-slate-50 pb-12">
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/tools/authority-core')}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
                <Database className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Rules Database</h1>
                <p className="text-slate-500">{rules.length} verified rules</p>
              </div>
            </div>
            <Link
              href="/rules/conflicts"
              className="flex items-center gap-2 px-4 py-2 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors"
            >
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm font-medium">View Conflicts</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Search Input */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search rules..."
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Jurisdiction Filter */}
            <select
              value={selectedJurisdiction}
              onChange={(e) => setSelectedJurisdiction(e.target.value)}
              className="px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Jurisdictions</option>
              {jurisdictions.map((j) => (
                <option key={j.id} value={j.id}>{j.name}</option>
              ))}
            </select>

            {/* Trigger Type Filter */}
            <select
              value={selectedTrigger}
              onChange={(e) => setSelectedTrigger(e.target.value)}
              className="px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {TRIGGER_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>

            {/* Tier Filter */}
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {AUTHORITY_TIERS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>

            {/* Actions */}
            <button
              onClick={handleSearch}
              className="px-4 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Search className="w-4 h-4 inline mr-1.5" />
              Search
            </button>

            {hasFilters && (
              <button
                onClick={clearFilters}
                className="px-3 py-2.5 text-slate-600 font-medium rounded-lg hover:bg-slate-100 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="max-w-7xl mx-auto px-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        ) : rules.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
            <Database className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No Rules Found</h3>
            <p className="text-slate-500 mb-6">
              {hasFilters
                ? 'No rules match your search criteria. Try adjusting your filters.'
                : 'The rules database is empty. Import rules by extracting them from court websites.'}
            </p>
            {hasFilters ? (
              <button
                onClick={clearFilters}
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-700 font-medium rounded-lg hover:bg-slate-200 transition-colors"
              >
                Clear Filters
              </button>
            ) : (
              <button
                onClick={() => router.push('/tools/authority-core')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Globe className="w-4 h-4" />
                Go to Authority Core
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rules.map((rule) => (
              <RuleCard
                key={rule.id}
                rule={rule}
                onSelect={() => setSelectedRule(rule)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedRule && (
        <RuleDetailModal
          rule={selectedRule}
          onClose={() => setSelectedRule(null)}
        />
      )}
    </div>
  );
}
