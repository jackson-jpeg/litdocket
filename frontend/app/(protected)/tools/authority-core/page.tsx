'use client';

/**
 * Authority Core - AI-Powered Rules Database
 *
 * Main interface for:
 * - Searching and extracting court rules via web scraping
 * - Managing rule proposals (review, approve, reject)
 * - Browsing the verified rules database
 *
 * Design matches the Tools Hub aesthetic with light slate backgrounds,
 * white cards, and the enterprise legal styling.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Database,
  Search,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ChevronRight,
  RefreshCw,
  Globe,
  Scale,
  Zap,
  BookOpen,
  ArrowRight,
  Info,
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import { ScrapeJob, RuleProposal, AuthorityRule } from '@/types';

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
  jurisdiction_type: string;
  state?: string;
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  count?: number;
}

function TabButton({ active, onClick, icon, label, count }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-all ${
        active
          ? 'bg-blue-600 text-white shadow-sm'
          : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
      }`}
    >
      {icon}
      <span>{label}</span>
      {count !== undefined && count > 0 && (
        <span className={`ml-1 px-2 py-0.5 text-xs rounded-full ${
          active ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-600'
        }`}>
          {count}
        </span>
      )}
    </button>
  );
}

function ScrapePanel({ jurisdictions, onJobCreated }: {
  jurisdictions: Jurisdiction[];
  onJobCreated: (job: ScrapeJob) => void;
}) {
  const [selectedJurisdiction, setSelectedJurisdiction] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleScrape = async () => {
    if (!selectedJurisdiction || !searchQuery.trim()) {
      setError('Please select a jurisdiction and enter a search query');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.post('/authority-core/scrape', {
        jurisdiction_id: selectedJurisdiction,
        search_query: searchQuery.trim(),
      });

      onJobCreated(response.data);
      setSearchQuery('');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start scrape job';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-blue-50 rounded-lg">
          <Globe className="w-5 h-5 text-blue-600" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-900">Extract Court Rules</h3>
          <p className="text-sm text-slate-500">Search and extract rules from court websites</p>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Jurisdiction
          </label>
          <select
            value={selectedJurisdiction}
            onChange={(e) => setSelectedJurisdiction(e.target.value)}
            className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select a jurisdiction...</option>
            {jurisdictions.map((j) => (
              <option key={j.id} value={j.id}>
                {j.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Search Query
          </label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="e.g., motion response deadline, discovery rules"
            className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="mt-1.5 text-xs text-slate-500">
            Be specific about what rules you&apos;re looking for
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <button
          onClick={handleScrape}
          disabled={isLoading || !selectedJurisdiction || !searchQuery.trim()}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Starting Extraction...
            </>
          ) : (
            <>
              <Zap className="w-4 h-4" />
              Extract Rules
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function JobCard({ job }: { job: ScrapeJob }) {
  const statusColors: Record<string, string> = {
    queued: 'bg-slate-100 text-slate-700',
    searching: 'bg-blue-100 text-blue-700',
    extracting: 'bg-amber-100 text-amber-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
  };

  const statusIcons: Record<string, React.ReactNode> = {
    queued: <Clock className="w-4 h-4" />,
    searching: <Search className="w-4 h-4 animate-pulse" />,
    extracting: <Zap className="w-4 h-4 animate-pulse" />,
    completed: <CheckCircle className="w-4 h-4" />,
    failed: <XCircle className="w-4 h-4" />,
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <p className="font-medium text-slate-900 line-clamp-1">{job.search_query}</p>
          <p className="text-sm text-slate-500">{job.jurisdiction_name || 'Unknown jurisdiction'}</p>
        </div>
        <span className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full ${statusColors[job.status]}`}>
          {statusIcons[job.status]}
          {job.status}
        </span>
      </div>

      {job.status !== 'failed' && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>Progress</span>
            <span>{job.progress_pct}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5">
            <div
              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${job.progress_pct}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-500">
          {job.rules_found} rules found
        </span>
        {job.proposals_created > 0 && (
          <span className="text-blue-600 font-medium">
            {job.proposals_created} proposals
          </span>
        )}
      </div>
    </div>
  );
}

function ProposalCard({ proposal, onAction }: {
  proposal: RuleProposal;
  onAction: () => void;
}) {
  const router = useRouter();

  const getConfidenceBadge = (score: number) => {
    if (score >= 0.8) return { label: 'High', color: 'bg-green-100 text-green-700' };
    if (score >= 0.5) return { label: 'Medium', color: 'bg-amber-100 text-amber-700' };
    return { label: 'Low', color: 'bg-red-100 text-red-700' };
  };

  const confidence = getConfidenceBadge(proposal.confidence_score);
  const ruleData = proposal.proposed_rule_data;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <p className="font-medium text-slate-900">{ruleData.rule_name}</p>
          <p className="text-sm text-slate-500">{ruleData.citation || ruleData.rule_code}</p>
        </div>
        <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${confidence.color}`}>
          {confidence.label} confidence
        </span>
      </div>

      <div className="flex items-center gap-4 text-sm text-slate-600 mb-4">
        <span className="flex items-center gap-1.5">
          <Scale className="w-4 h-4" />
          {ruleData.authority_tier}
        </span>
        <span className="flex items-center gap-1.5">
          <FileText className="w-4 h-4" />
          {ruleData.deadlines.length} deadlines
        </span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => router.push(`/rules/proposals/${proposal.id}`)}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
        >
          Review
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function RuleCard({ rule }: { rule: AuthorityRule }) {
  const router = useRouter();

  const tierColors: Record<string, string> = {
    federal: 'bg-purple-100 text-purple-700',
    state: 'bg-blue-100 text-blue-700',
    local: 'bg-green-100 text-green-700',
    standing_order: 'bg-amber-100 text-amber-700',
    firm: 'bg-slate-100 text-slate-700',
  };

  return (
    <div
      onClick={() => router.push(`/rules/database/${rule.id}`)}
      className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-sm hover:border-blue-300 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <p className="font-medium text-slate-900">{rule.rule_name}</p>
          <p className="text-sm text-blue-600">{rule.citation || rule.rule_code}</p>
        </div>
        <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${tierColors[rule.authority_tier]}`}>
          {rule.authority_tier}
        </span>
      </div>

      <div className="flex items-center gap-4 text-sm text-slate-500">
        <span>{rule.jurisdiction_name || 'Unknown'}</span>
        <span>{rule.deadlines.length} deadlines</span>
        {rule.is_verified && (
          <span className="flex items-center gap-1 text-green-600">
            <CheckCircle className="w-3.5 h-3.5" />
            Verified
          </span>
        )}
      </div>
    </div>
  );
}

export default function AuthorityCorePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'extract' | 'proposals' | 'database'>('extract');
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [jobs, setJobs] = useState<ScrapeJob[]>([]);
  const [proposals, setProposals] = useState<RuleProposal[]>([]);
  const [rules, setRules] = useState<AuthorityRule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [jurisdictionsRes, jobsRes, proposalsRes, rulesRes] = await Promise.all([
        apiClient.get('/jurisdictions'),
        apiClient.get('/authority-core/jobs?limit=10'),
        apiClient.get('/authority-core/proposals?status=pending&limit=20'),
        apiClient.get('/authority-core/rules?limit=50'),
      ]);

      setJurisdictions(jurisdictionsRes.data);
      setJobs(jobsRes.data);
      setProposals(proposalsRes.data);
      setRules(rulesRes.data);
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleJobCreated = (job: ScrapeJob) => {
    setJobs((prev) => [job, ...prev]);
    // Poll for updates
    const pollInterval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/authority-core/scrape/${job.id}`);
        const updatedJob = response.data;

        setJobs((prev) =>
          prev.map((j) => (j.id === updatedJob.id ? updatedJob : j))
        );

        if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
          clearInterval(pollInterval);
          // Refresh proposals if job completed
          if (updatedJob.status === 'completed') {
            const proposalsRes = await apiClient.get('/authority-core/proposals?status=pending&limit=20');
            setProposals(proposalsRes.data);
          }
        }
      } catch (err) {
        console.error('Failed to poll job status:', err);
        clearInterval(pollInterval);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    try {
      const response = await apiClient.get(`/authority-core/rules/search?q=${encodeURIComponent(searchQuery)}`);
      setRules(response.data);
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const pendingProposalsCount = proposals.filter((p) => p.status === 'pending').length;

  return (
    <div className="min-h-screen bg-slate-50 pb-12">
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg">
                <Database className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Authority Core</h1>
                <p className="text-slate-500">AI-Powered Rules Database</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => router.push('/rules/database')}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
              >
                <BookOpen className="w-4 h-4" />
                Browse All Rules
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center gap-2">
          <TabButton
            active={activeTab === 'extract'}
            onClick={() => setActiveTab('extract')}
            icon={<Globe className="w-4 h-4" />}
            label="Extract Rules"
          />
          <TabButton
            active={activeTab === 'proposals'}
            onClick={() => setActiveTab('proposals')}
            icon={<FileText className="w-4 h-4" />}
            label="Proposals"
            count={pendingProposalsCount}
          />
          <TabButton
            active={activeTab === 'database'}
            onClick={() => setActiveTab('database')}
            icon={<Database className="w-4 h-4" />}
            label="Rules Database"
          />
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        ) : (
          <>
            {/* Extract Tab */}
            {activeTab === 'extract' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ScrapePanel jurisdictions={jurisdictions} onJobCreated={handleJobCreated} />

                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-slate-900">Recent Jobs</h3>
                    <button
                      onClick={fetchData}
                      className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>

                  {jobs.length === 0 ? (
                    <div className="text-center py-8">
                      <Globe className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                      <p className="text-slate-500">No extraction jobs yet</p>
                      <p className="text-sm text-slate-400">Start by extracting rules from a jurisdiction</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {jobs.map((job) => (
                        <JobCard key={job.id} job={job} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Proposals Tab */}
            {activeTab === 'proposals' && (
              <div>
                {proposals.length === 0 ? (
                  <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
                    <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">No Pending Proposals</h3>
                    <p className="text-slate-500 mb-6">
                      Extract rules from court websites to generate proposals for review.
                    </p>
                    <button
                      onClick={() => setActiveTab('extract')}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <Zap className="w-4 h-4" />
                      Start Extraction
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {proposals.map((proposal) => (
                      <ProposalCard
                        key={proposal.id}
                        proposal={proposal}
                        onAction={fetchData}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Database Tab */}
            {activeTab === 'database' && (
              <div>
                {/* Search */}
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
                  <div className="flex items-center gap-3">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        placeholder="Search rules by name, citation, or keywords..."
                        className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <button
                      onClick={handleSearch}
                      className="px-4 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Search
                    </button>
                  </div>
                </div>

                {rules.length === 0 ? (
                  <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
                    <Database className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">No Rules in Database</h3>
                    <p className="text-slate-500 mb-6">
                      Import rules by extracting them from court websites and approving proposals.
                    </p>
                    <button
                      onClick={() => setActiveTab('extract')}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <Zap className="w-4 h-4" />
                      Start Extraction
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {rules.map((rule) => (
                      <RuleCard key={rule.id} rule={rule} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Info Banner */}
      <div className="max-w-7xl mx-auto px-6 mt-8">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-blue-900">How Authority Core Works</h4>
              <p className="text-sm text-blue-700 mt-1">
                Authority Core uses AI to extract procedural rules from court websites. Each extracted rule
                becomes a proposal that you review and approve before it enters the verified rules database.
                Once approved, rules are used automatically when calculating deadlines.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
