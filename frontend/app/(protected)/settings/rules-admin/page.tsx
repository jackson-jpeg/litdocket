'use client';

/**
 * Rules Admin Dashboard - Manage the automated rules scraping pipeline
 *
 * Features:
 * 1. Coverage overview (50 states + federal courts)
 * 2. Rules queue management (approve/reject)
 * 3. Scraping job monitoring
 * 4. AI model status
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import apiClient from '@/lib/api-client';

// Icons
const CheckCircleIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const XCircleIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const RefreshIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const ChevronLeftIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
  </svg>
);

const GlobeIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const CpuChipIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
  </svg>
);

interface CoverageStats {
  summary: {
    total_jurisdictions: number;
    jurisdictions_covered: number;
    us_states: number;
    federal_courts: number;
  };
  pipeline: {
    total_scraped: number;
    total_validated: number;
    total_deployed: number;
    total_expected: number;
    coverage_percentage: number;
  };
  queue: {
    total_rules_in_queue: number;
    rules_by_status: Record<string, number>;
  };
}

interface ScrapedRule {
  id: string;
  jurisdiction_code: string;
  jurisdiction_name: string;
  court_type: string;
  rule_number: string;
  rule_title: string;
  rule_text: string;
  status: string;
  confidence_score: number;
  created_at: string;
}

interface AIModelInfo {
  name: string;
  model_id: string;
  use_case: string;
  cost_tier: string;
}

export default function RulesAdminPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'overview' | 'queue' | 'jobs'>('overview');
  const [loading, setLoading] = useState(true);
  const [coverageStats, setCoverageStats] = useState<CoverageStats | null>(null);
  const [rules, setRules] = useState<ScrapedRule[]>([]);
  const [selectedRule, setSelectedRule] = useState<ScrapedRule | null>(null);
  const [aiModels, setAiModels] = useState<Record<string, AIModelInfo> | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('pending_approval');

  const fetchCoverage = useCallback(async () => {
    try {
      const response = await apiClient.get('/rules-scraper/coverage');
      if (response.data.success) {
        setCoverageStats(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch coverage:', error);
    }
  }, []);

  const fetchRules = useCallback(async () => {
    try {
      const response = await apiClient.get('/rules-scraper/queue', {
        params: { status: statusFilter, limit: 50 }
      });
      if (response.data.success) {
        setRules(response.data.data.rules);
      }
    } catch (error) {
      console.error('Failed to fetch rules:', error);
    }
  }, [statusFilter]);

  const fetchAIModels = useCallback(async () => {
    try {
      const response = await apiClient.get('/rules-scraper/models');
      if (response.data.success) {
        setAiModels(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch AI models:', error);
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchCoverage(), fetchRules(), fetchAIModels()]);
      setLoading(false);
    };
    loadData();
  }, [fetchCoverage, fetchRules, fetchAIModels]);

  useEffect(() => {
    fetchRules();
  }, [statusFilter, fetchRules]);

  const handleApprove = async (ruleId: string) => {
    try {
      await apiClient.post(`/rules-scraper/queue/${ruleId}/approve`);
      fetchRules();
      fetchCoverage();
      setSelectedRule(null);
    } catch (error) {
      console.error('Failed to approve rule:', error);
    }
  };

  const handleReject = async (ruleId: string, reason: string) => {
    try {
      await apiClient.post(`/rules-scraper/queue/${ruleId}/reject`, null, {
        params: { reason }
      });
      fetchRules();
      fetchCoverage();
      setSelectedRule(null);
    } catch (error) {
      console.error('Failed to reject rule:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'validated':
      case 'approved':
      case 'deployed':
        return 'text-emerald-600 bg-emerald-50';
      case 'rejected':
        return 'text-red-600 bg-red-50';
      case 'pending_approval':
        return 'text-amber-600 bg-amber-50';
      default:
        return 'text-slate-600 bg-slate-50';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/settings')}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <ChevronLeftIcon />
              </button>
              <div>
                <h1 className="text-2xl font-semibold text-slate-900">Rules Administration</h1>
                <p className="text-sm text-slate-500 font-mono">
                  Automated rules gathering pipeline
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                fetchCoverage();
                fetchRules();
              }}
              className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <RefreshIcon />
              <span className="text-sm font-medium">Refresh</span>
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4">
            {(['overview', 'queue', 'jobs'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === tab
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* Coverage Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl border border-slate-200 p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <GlobeIcon />
                    </div>
                    <span className="text-sm font-medium text-slate-500">Total Jurisdictions</span>
                  </div>
                  <p className="text-3xl font-bold text-slate-900">
                    {coverageStats?.summary.total_jurisdictions || 0}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    {coverageStats?.summary.us_states} states + {coverageStats?.summary.federal_courts} federal
                  </p>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-emerald-100 rounded-lg text-emerald-600">
                      <CheckCircleIcon />
                    </div>
                    <span className="text-sm font-medium text-slate-500">Covered</span>
                  </div>
                  <p className="text-3xl font-bold text-emerald-600">
                    {coverageStats?.summary.jurisdictions_covered || 0}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    {((coverageStats?.summary.jurisdictions_covered || 0) / (coverageStats?.summary.total_jurisdictions || 1) * 100).toFixed(1)}% complete
                  </p>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-amber-100 rounded-lg text-amber-600">
                      <span className="text-lg font-bold">Q</span>
                    </div>
                    <span className="text-sm font-medium text-slate-500">In Queue</span>
                  </div>
                  <p className="text-3xl font-bold text-amber-600">
                    {coverageStats?.queue.total_rules_in_queue || 0}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    {coverageStats?.queue.rules_by_status?.pending_approval || 0} pending approval
                  </p>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-purple-100 rounded-lg text-purple-600">
                      <span className="text-lg font-bold">#</span>
                    </div>
                    <span className="text-sm font-medium text-slate-500">Deployed Rules</span>
                  </div>
                  <p className="text-3xl font-bold text-purple-600">
                    {coverageStats?.pipeline.total_deployed || 0}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    Live in production
                  </p>
                </div>
              </div>

              {/* AI Models */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <CpuChipIcon />
                  </div>
                  <h2 className="text-lg font-semibold text-slate-900">AI Model Configuration</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {aiModels && Object.entries(aiModels).map(([key, model]) => (
                    <div
                      key={key}
                      className="border border-slate-200 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold text-slate-900">{model.name}</h3>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          model.cost_tier === 'high' ? 'bg-red-100 text-red-600' :
                          model.cost_tier === 'medium' ? 'bg-amber-100 text-amber-600' :
                          'bg-emerald-100 text-emerald-600'
                        }`}>
                          {model.cost_tier}
                        </span>
                      </div>
                      <p className="text-sm text-slate-500 mb-2">{model.use_case}</p>
                      <code className="text-xs text-slate-400 font-mono">{model.model_id}</code>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pipeline Progress */}
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h2 className="text-lg font-semibold text-slate-900 mb-6">Pipeline Progress</h2>
                <div className="space-y-4">
                  {[
                    { label: 'Scraped', value: coverageStats?.pipeline.total_scraped || 0, color: 'bg-blue-500' },
                    { label: 'Validated', value: coverageStats?.pipeline.total_validated || 0, color: 'bg-amber-500' },
                    { label: 'Deployed', value: coverageStats?.pipeline.total_deployed || 0, color: 'bg-emerald-500' },
                  ].map((stage) => (
                    <div key={stage.label}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-600">{stage.label}</span>
                        <span className="font-medium text-slate-900">{stage.value}</span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${stage.color} rounded-full transition-all duration-500`}
                          style={{
                            width: `${Math.min(100, (stage.value / Math.max(1, coverageStats?.pipeline.total_expected || 1)) * 100)}%`
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'queue' && (
            <motion.div
              key="queue"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              {/* Filters */}
              <div className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-500">Status:</span>
                  {['pending_approval', 'validated', 'scraped', 'approved', 'rejected'].map((status) => (
                    <button
                      key={status}
                      onClick={() => setStatusFilter(status)}
                      className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                        statusFilter === status
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {status.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Rules List */}
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-500">Rule</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-500">Jurisdiction</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-500">Status</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-slate-500">Confidence</th>
                      <th className="text-right px-4 py-3 text-sm font-medium text-slate-500">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {rules.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                          No rules found with status &quot;{statusFilter}&quot;
                        </td>
                      </tr>
                    ) : (
                      rules.map((rule) => (
                        <tr
                          key={rule.id}
                          className="hover:bg-slate-50 cursor-pointer"
                          onClick={() => setSelectedRule(rule)}
                        >
                          <td className="px-4 py-3">
                            <div>
                              <p className="font-medium text-slate-900">{rule.rule_number}</p>
                              <p className="text-sm text-slate-500 truncate max-w-xs">{rule.rule_title}</p>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600">
                            {rule.jurisdiction_code}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(rule.status)}`}>
                              {rule.status}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    rule.confidence_score >= 0.8 ? 'bg-emerald-500' :
                                    rule.confidence_score >= 0.5 ? 'bg-amber-500' : 'bg-red-500'
                                  }`}
                                  style={{ width: `${rule.confidence_score * 100}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-500">
                                {(rule.confidence_score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            {(rule.status === 'validated' || rule.status === 'pending_approval') && (
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleApprove(rule.id);
                                  }}
                                  className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                                  title="Approve"
                                >
                                  <CheckCircleIcon />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    const reason = prompt('Enter rejection reason:');
                                    if (reason) handleReject(rule.id, reason);
                                  }}
                                  className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                  title="Reject"
                                >
                                  <XCircleIcon />
                                </button>
                              </div>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}

          {activeTab === 'jobs' && (
            <motion.div
              key="jobs"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-white rounded-xl border border-slate-200 p-8 text-center"
            >
              <div className="max-w-md mx-auto">
                <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CpuChipIcon />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">Scraping Jobs</h3>
                <p className="text-slate-500 mb-6">
                  Background scraping jobs for automated rules gathering.
                  Jobs can be started from the coverage view.
                </p>
                <button
                  onClick={() => setActiveTab('overview')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  View Coverage
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Rule Detail Modal */}
      <AnimatePresence>
        {selectedRule && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedRule(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-slate-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-slate-900">
                      {selectedRule.rule_number}
                    </h2>
                    <p className="text-sm text-slate-500">{selectedRule.jurisdiction_code}</p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm ${getStatusColor(selectedRule.status)}`}>
                    {selectedRule.status}
                  </span>
                </div>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <h3 className="text-sm font-medium text-slate-500 mb-1">Title</h3>
                  <p className="text-slate-900">{selectedRule.rule_title}</p>
                </div>

                <div>
                  <h3 className="text-sm font-medium text-slate-500 mb-1">Rule Text</h3>
                  <div className="bg-slate-50 rounded-lg p-4 text-sm text-slate-700 font-mono whitespace-pre-wrap max-h-60 overflow-y-auto">
                    {selectedRule.rule_text}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-sm font-medium text-slate-500 mb-1">Court Type</h3>
                    <p className="text-slate-900">{selectedRule.court_type || 'N/A'}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-slate-500 mb-1">Confidence</h3>
                    <p className="text-slate-900">{(selectedRule.confidence_score * 100).toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              {(selectedRule.status === 'validated' || selectedRule.status === 'pending_approval') && (
                <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
                  <button
                    onClick={() => {
                      const reason = prompt('Enter rejection reason:');
                      if (reason) handleReject(selectedRule.id, reason);
                    }}
                    className="px-4 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => handleApprove(selectedRule.id)}
                    className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
                  >
                    Approve Rule
                  </button>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
