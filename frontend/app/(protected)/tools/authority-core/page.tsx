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

interface HarvestResult {
  job_id: string;
  status: string;
  rules_found: number;
  proposals_created: number;
  errors: string[];
}

function ScrapePanel({ jurisdictions, onJobCreated }: {
  jurisdictions: Jurisdiction[];
  onJobCreated: (job: ScrapeJob) => void;
}) {
  const [selectedJurisdiction, setSelectedJurisdiction] = useState('');
  const [url, setUrl] = useState('');
  const [useExtendedThinking, setUseExtendedThinking] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<HarvestResult | null>(null);

  const handleHarvest = async () => {
    if (!selectedJurisdiction || !url.trim()) {
      setError('Please select a jurisdiction and enter a URL');
      return;
    }

    // Basic URL validation
    try {
      new URL(url.trim());
    } catch {
      setError('Please enter a valid URL (e.g., https://www.flsd.uscourts.gov/local-rules)');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.post('/api/v1/authority-core/harvest', {
        url: url.trim(),
        jurisdiction_id: selectedJurisdiction,
        use_extended_thinking: useExtendedThinking,
        auto_approve_high_confidence: false,
      });

      setResult(response.data);

      // Create a ScrapeJob-like object for the parent component
      const jobData: ScrapeJob = {
        id: response.data.job_id,
        user_id: '',
        jurisdiction_id: selectedJurisdiction,
        jurisdiction_name: response.data.jurisdiction_name,
        search_query: `Harvest from ${url.trim()}`,
        status: response.data.status,
        progress_pct: 100,
        rules_found: response.data.rules_found,
        proposals_created: response.data.proposals_created,
        urls_processed: [url.trim()],
        created_at: new Date().toISOString(),
      };
      onJobCreated(jobData);

      if (response.data.status === 'completed') {
        setUrl('');
      }
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        setError(axiosError.response?.data?.detail || 'Failed to harvest rules');
      } else {
        setError('Failed to harvest rules');
      }
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
          <p className="text-sm text-slate-500">Extract rules from official court websites</p>
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
            Court Rules URL
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.flsd.uscourts.gov/local-rules"
            className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="mt-1.5 text-xs text-slate-500">
            Enter the URL of an official court rules page
          </p>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="extendedThinking"
            checked={useExtendedThinking}
            onChange={(e) => setUseExtendedThinking(e.target.checked)}
            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="extendedThinking" className="text-sm text-slate-600">
            Use extended thinking (more accurate, slower)
          </label>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {result && (
          <div className={`p-3 rounded-lg flex items-start gap-2 ${
            result.errors.length > 0
              ? 'bg-amber-50 border border-amber-200'
              : 'bg-green-50 border border-green-200'
          }`}>
            <CheckCircle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
              result.errors.length > 0 ? 'text-amber-500' : 'text-green-500'
            }`} />
            <div className="text-sm">
              <p className={result.errors.length > 0 ? 'text-amber-700' : 'text-green-700'}>
                Found {result.rules_found} rules, created {result.proposals_created} proposals
              </p>
              {result.errors.length > 0 && (
                <p className="text-amber-600 text-xs mt-1">
                  {result.errors.length} warning(s) during extraction
                </p>
              )}
            </div>
          </div>
        )}

        <button
          onClick={handleHarvest}
          disabled={isLoading || !selectedJurisdiction || !url.trim()}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Extracting Rules...
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
      // Fetch each resource independently so one failure doesn't block others
      const [jurisdictionsRes, jobsRes, proposalsRes, rulesRes] = await Promise.allSettled([
        apiClient.get('/api/v1/jurisdictions'),
        apiClient.get('/api/v1/authority-core/jobs?limit=10'),
        apiClient.get('/api/v1/authority-core/proposals?status=pending&limit=20'),
        apiClient.get('/api/v1/authority-core/rules?limit=50'),
      ]);

      // Set data from successful responses
      if (jurisdictionsRes.status === 'fulfilled') {
        setJurisdictions(jurisdictionsRes.value.data);
      } else {
        console.error('Failed to fetch jurisdictions:', jurisdictionsRes.reason);
      }

      if (jobsRes.status === 'fulfilled') {
        setJobs(jobsRes.value.data);
      } else {
        console.error('Failed to fetch jobs:', jobsRes.reason);
      }

      if (proposalsRes.status === 'fulfilled') {
        setProposals(proposalsRes.value.data);
      } else {
        console.error('Failed to fetch proposals:', proposalsRes.reason);
      }

      if (rulesRes.status === 'fulfilled') {
        setRules(rulesRes.value.data);
      } else {
        console.error('Failed to fetch rules:', rulesRes.reason);
      }
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
        const response = await apiClient.get(`/api/v1/authority-core/scrape/${job.id}`);
        const updatedJob = response.data;

        setJobs((prev) =>
          prev.map((j) => (j.id === updatedJob.id ? updatedJob : j))
        );

        if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
          clearInterval(pollInterval);
          // Refresh proposals if job completed
          if (updatedJob.status === 'completed') {
            const proposalsRes = await apiClient.get('/api/v1/authority-core/proposals?status=pending&limit=20');
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
      const response = await apiClient.get(`/api/v1/authority-core/rules/search?q=${encodeURIComponent(searchQuery)}`);
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
