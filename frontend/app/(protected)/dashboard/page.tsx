'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import {
  Upload, FileText, AlertTriangle, Clock, CheckCircle,
  Calendar, Folder, Scale, Loader2, AlertCircle, ChevronRight, RefreshCw, Settings, Calculator
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import MorningReport from '@/components/MorningReport';
import DeadlineHeatMap from '@/components/DeadlineHeatMap';
import MatterHealthCards from '@/components/MatterHealthCards';
import GlobalSearch from '@/components/GlobalSearch';
import { HeatMapSkeleton, MatterHealthSkeleton } from '@/components/Skeleton';
import { QuickToolsGrid, ToolSuggestionBanner } from '@/components/ContextualToolCard';
import { useAuth } from '@/lib/auth/auth-context';
import QuickCalculatorModal from '@/components/tools/QuickCalculatorModal';
import { OnboardingWizard } from '@/components/onboarding/OnboardingWizard';

// Import progressive loading hooks
import {
  useDashboardAlerts,
  useDashboardStats,
  useDashboardUpcoming,
  useHeatMap,
  useActivityFeed,
  useMatterHealth,
} from '@/hooks/dashboard';

// Helper to format time ago
function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}

// Skeleton components for progressive loading
function StatsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="card animate-pulse">
          <div className="h-4 bg-slate-200 rounded w-20 mb-3" />
          <div className="h-10 bg-slate-200 rounded w-16 mb-2" />
          <div className="h-4 bg-slate-200 rounded w-32" />
        </div>
      ))}
    </div>
  );
}

function UpcomingSkeleton() {
  return (
    <div className="card">
      <div className="h-6 bg-slate-200 rounded w-48 mb-6" />
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-4 animate-pulse">
            <div className="w-3 h-3 bg-slate-200 rounded-full mt-2" />
            <div className="flex-1 p-4 bg-slate-50 rounded-lg">
              <div className="h-5 bg-slate-200 rounded w-3/4 mb-2" />
              <div className="h-4 bg-slate-200 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActivitySkeleton() {
  return (
    <div className="card">
      <div className="h-5 bg-slate-200 rounded w-32 mb-4" />
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex gap-3 animate-pulse">
            <div className="w-8 h-8 bg-slate-200 rounded-lg" />
            <div className="flex-1">
              <div className="h-4 bg-slate-200 rounded w-3/4 mb-2" />
              <div className="h-3 bg-slate-200 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Stats Section Component
function StatsSection() {
  const router = useRouter();
  const { data: alerts } = useDashboardAlerts();
  const { data: stats, isLoading } = useDashboardStats();

  if (isLoading) {
    return <StatsSkeleton />;
  }

  if (!stats) return null;

  const overdueCount = alerts?.overdue.count || 0;
  const urgentCount = alerts?.urgent.count || 0;
  const upcomingWeekCount = alerts?.upcoming_week.count || 0;
  const upcomingMonthCount = alerts?.upcoming_month.count || 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {/* Critical/Overdue Card */}
      <div
        onClick={() => router.push('/calendar?filter=overdue')}
        className="card-hover cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-mono font-semibold text-ink-secondary uppercase tracking-wide">Critical</div>
          {overdueCount > 0 ? (
            <div className="w-2 h-2 bg-fatal" />
          ) : (
            <CheckCircle className="w-4 h-4 text-status-success" />
          )}
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className={`text-4xl font-mono font-bold ${
            overdueCount > 0 ? 'text-fatal' : 'text-status-success'
          }`}>
            {overdueCount + urgentCount}
          </span>
        </div>
        <p className="text-sm text-ink-secondary">
          {overdueCount} overdue, {urgentCount} urgent
        </p>
      </div>

      {/* Pending Deadlines */}
      <div
        onClick={() => router.push('/calendar?filter=pending')}
        className="card-hover cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-mono font-semibold text-ink-secondary uppercase tracking-wide">Pending</div>
          <Clock className="w-4 h-4 text-important" />
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-4xl font-mono font-bold text-important">
            {stats.total_pending_deadlines}
          </span>
        </div>
        <p className="text-sm text-ink-secondary">
          {upcomingWeekCount} this week · {upcomingMonthCount} this month
        </p>
      </div>

      {/* Active Cases */}
      <div
        onClick={() => router.push('/cases')}
        className="card-hover cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-mono font-semibold text-ink-secondary uppercase tracking-wide">Cases</div>
          <Folder className="w-4 h-4 text-steel" />
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-4xl font-mono font-bold text-steel">
            {stats.total_cases}
          </span>
        </div>
        <p className="text-sm text-ink-secondary">
          {stats.by_jurisdiction.state} State · {stats.by_jurisdiction.federal} Federal
        </p>
      </div>

      {/* Documents */}
      <div
        onClick={() => router.push('/cases')}
        className="card-hover cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-mono font-semibold text-ink-secondary uppercase tracking-wide">Documents</div>
          <FileText className="w-4 h-4 text-steel-light" />
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-4xl font-mono font-bold text-steel-light">
            {stats.total_documents}
          </span>
        </div>
        {stats.total_cases > 0 && (
          <p className="text-sm text-ink-secondary">
            ~{Math.round(stats.total_documents / stats.total_cases)} per case
          </p>
        )}
      </div>
    </div>
  );
}

// Upcoming Deadlines Section
function UpcomingDeadlinesSection() {
  const router = useRouter();
  const { data, isLoading } = useDashboardUpcoming(30, 10);

  if (isLoading) {
    return <UpcomingSkeleton />;
  }

  return (
    <div className="card">
      <div className="mb-6">
        <h3 className="text-xl font-heading font-semibold text-ink flex items-center gap-2">
          <Calendar className="w-5 h-5 text-steel" />
          Upcoming Deadlines
        </h3>
      </div>

      {data?.deadlines && data.deadlines.length > 0 ? (
        <div className="timeline">
          {data.deadlines.map((deadline) => (
            <div
              key={deadline.id}
              className="timeline-item cursor-pointer group"
              onClick={() => router.push(`/cases/${deadline.case_id}`)}
            >
              <div className={`timeline-dot ${
                deadline.urgency_level === 'overdue' ? 'bg-fatal' :
                deadline.urgency_level === 'urgent' ? 'bg-critical' :
                deadline.urgency_level === 'upcoming-week' ? 'bg-important' : 'bg-steel'
              }`} />
              <div className="bg-paper border border-ink/20 p-4 hover:border-ink hover:translate-x-0.5 hover:translate-y-0.5 transition-transform">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-ink truncate group-hover:text-steel">{deadline.title}</p>
                    <p className="text-sm font-mono text-ink-secondary mt-1">
                      {deadline.deadline_date} • {Math.abs(deadline.days_until || 0)} day{Math.abs(deadline.days_until || 0) !== 1 ? 's' : ''} {(deadline.days_until || 0) < 0 ? 'overdue' : 'remaining'}
                    </p>
                    {deadline.action_required && (
                      <p className="text-sm text-ink-muted mt-2">{deadline.action_required}</p>
                    )}
                    {deadline.party_role && (
                      <span className="inline-block mt-2 text-xs font-mono bg-surface text-ink-secondary px-2 py-1 border border-ink/20">
                        {deadline.party_role}
                      </span>
                    )}
                  </div>
                  <span className={`badge ${
                    deadline.urgency_level === 'overdue' ? 'badge-fatal' :
                    deadline.urgency_level === 'urgent' ? 'badge-critical' :
                    deadline.urgency_level === 'upcoming-week' ? 'badge-important' : 'badge-standard'
                  }`}>
                    {deadline.urgency_level === 'overdue' ? 'OVERDUE' :
                     deadline.urgency_level === 'urgent' ? 'URGENT' :
                     deadline.urgency_level === 'upcoming-week' ? 'THIS WEEK' : 'UPCOMING'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-ink-secondary">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 text-status-success" />
          <p className="font-medium">All clear!</p>
          <p className="text-sm mt-1">No upcoming deadlines</p>
        </div>
      )}
    </div>
  );
}

// Critical Cases Section (sidebar)
function CriticalCasesSection() {
  const router = useRouter();
  const { data } = useMatterHealth(true);

  if (!data?.critical_cases || data.critical_cases.length === 0) {
    return null;
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Critical Cases</h3>
      <div className="space-y-3">
        {data.critical_cases.slice(0, 5).map((caseItem) => (
          <div
            key={caseItem.case_id}
            className="p-4 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:border-blue-300 hover:bg-blue-50 transition-all group"
            onClick={() => router.push(`/cases/${caseItem.case_id}`)}
          >
            <p className="font-medium text-slate-900 group-hover:text-blue-600">{caseItem.case_number}</p>
            <p className="text-sm text-slate-600 mt-1 truncate">{caseItem.title}</p>
            <div className="mt-3 flex items-center justify-between">
              <span className={`badge ${
                caseItem.urgency_level === 'critical' ? 'badge-fatal' : 'badge-critical'
              }`}>
                {caseItem.days_until_deadline} days
              </span>
              <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Activity Feed Section
function ActivityFeedSection() {
  const { data, isLoading } = useActivityFeed(8);

  if (isLoading) {
    return <ActivitySkeleton />;
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Recent Activity</h3>
      <div className="space-y-4">
        {data?.activities.slice(0, 8).map((activity, idx) => (
          <div key={idx} className="flex items-start gap-3 pb-4 border-b border-slate-100 last:border-0 last:pb-0">
            <div className="p-2 bg-blue-50 rounded-lg">
              <FileText className="w-4 h-4 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">
                {activity.case_number}
              </p>
              <p className="text-xs text-slate-600 truncate mt-0.5">
                {activity.description}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {new Date(activity.timestamp).toLocaleDateString()}
              </p>
            </div>
          </div>
        ))}

        {(!data?.activities || data.activities.length === 0) && (
          <p className="text-center text-slate-500 py-4 text-sm">No recent activity</p>
        )}
      </div>
    </div>
  );
}

// Heat Map Section (lazy loaded)
function HeatMapSection() {
  const router = useRouter();
  const { data, isLoading } = useHeatMap(true);

  if (isLoading) {
    return <HeatMapSkeleton />;
  }

  if (!data?.matrix || data.matrix.every(cell => cell.count === 0)) {
    return (
      <div className="card text-center py-16">
        <Calendar className="w-16 h-16 text-slate-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-slate-900 mb-2">
          No Heat Map Data
        </h3>
        <p className="text-sm text-slate-600">
          Add deadlines to cases to see the deadline heat map visualization
        </p>
      </div>
    );
  }

  // Transform flat matrix to the format DeadlineHeatMap expects
  type UrgencyKey = 'today' | '3_day' | '7_day' | '30_day';
  type SeverityKey = 'fatal' | 'critical' | 'important' | 'standard' | 'informational';

  interface HeatMapDeadline {
    id: string;
    case_id: string;
    title: string;
    deadline_date: string;
    days_until: number;
    action_required: string;
    case_title: string;
  }

  // Initialize empty matrix
  const emptyUrgency: Record<UrgencyKey, HeatMapDeadline[]> = {
    today: [],
    '3_day': [],
    '7_day': [],
    '30_day': [],
  };

  const matrix: Record<SeverityKey, Record<UrgencyKey, HeatMapDeadline[]>> = {
    fatal: { ...emptyUrgency },
    critical: { ...emptyUrgency },
    important: { ...emptyUrgency },
    standard: { ...emptyUrgency },
    informational: { ...emptyUrgency },
  };

  // Populate matrix from flat data
  const byFatality: Record<string, number> = { fatal: 0, critical: 0, important: 0, standard: 0, informational: 0 };
  const byUrgency: Record<string, number> = { today: 0, '3_day': 0, '7_day': 0, '30_day': 0 };

  data.matrix.forEach((cell) => {
    const severity = cell.severity as SeverityKey;
    const urgency = cell.urgency as UrgencyKey;

    if (matrix[severity] && matrix[severity][urgency] !== undefined) {
      matrix[severity][urgency] = cell.deadlines.map((d) => ({
        id: d.id,
        case_id: d.case_id,
        title: d.title,
        deadline_date: d.deadline_date,
        days_until: d.days_until,
        action_required: '',
        case_title: '',
      }));
      byFatality[severity] = (byFatality[severity] || 0) + cell.count;
      byUrgency[urgency] = (byUrgency[urgency] || 0) + cell.count;
    }
  });

  const heatMapData = {
    matrix,
    summary: {
      total_deadlines: data.summary.total,
      by_fatality: {
        fatal: byFatality.fatal,
        critical: byFatality.critical,
        important: byFatality.important,
        standard: byFatality.standard,
        informational: byFatality.informational,
      },
      by_urgency: {
        today: byUrgency.today,
        '3_day': byUrgency['3_day'],
        '7_day': byUrgency['7_day'],
        '30_day': byUrgency['30_day'],
      },
    },
  };

  return (
    <DeadlineHeatMap
      heatMapData={heatMapData}
      onCaseClick={(caseId) => router.push(`/cases/${caseId}`)}
    />
  );
}

// Matter Health Section (lazy loaded)
function MatterHealthSection() {
  const router = useRouter();
  const { data, isLoading } = useMatterHealth(true);

  if (isLoading) {
    return <MatterHealthSkeleton />;
  }

  if (!data?.health_cards || data.health_cards.length === 0) {
    return (
      <div className="card text-center py-16">
        <Folder className="w-16 h-16 text-slate-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-slate-900 mb-2">
          No Cases with Pending Deadlines
        </h3>
        <p className="text-sm text-slate-600 mb-6">
          All cases are up to date or have no active deadlines
        </p>
        <button
          onClick={() => router.push('/cases')}
          className="btn-primary"
        >
          View All Cases
        </button>
      </div>
    );
  }

  return (
    <MatterHealthCards
      healthCards={data.health_cards}
      onCaseClick={(caseId) => router.push(`/cases/${caseId}`)}
    />
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { signOut, user } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeView, setActiveView] = useState<'overview' | 'heatmap' | 'cases'>('overview');
  const [calculatorOpen, setCalculatorOpen] = useState(false);

  // Use hooks for progressive loading
  const { data: alerts, isLoading: alertsLoading, lastUpdated, mutate: refreshAlerts } = useDashboardAlerts();
  const { data: stats, isLoading: statsLoading, mutate: refreshStats } = useDashboardStats();
  const { mutate: refreshUpcoming } = useDashboardUpcoming();
  const { mutate: refreshActivity } = useActivityFeed();
  const { mutate: refreshHealth } = useMatterHealth(activeView === 'cases');
  const { mutate: refreshHeatMap } = useHeatMap(activeView === 'heatmap');

  // Combined loading state - only true during initial load
  const isInitialLoading = alertsLoading && statsLoading && !alerts && !stats;

  // Combined refresh function
  const handleManualRefresh = useCallback(async () => {
    await Promise.all([
      refreshAlerts(),
      refreshStats(),
      refreshUpcoming(),
      refreshActivity(),
      refreshHealth(),
      refreshHeatMap(),
    ]);
  }, [refreshAlerts, refreshStats, refreshUpcoming, refreshActivity, refreshHealth, refreshHeatMap]);

  // Keyboard shortcut for search (Cmd/Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];

    if (file.type !== 'application/pdf') {
      setError('Please upload a PDF file');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post('/api/v1/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const { redirect_url } = response.data;
      router.push(redirect_url);

    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Upload failed. Please try again.');
      setUploading(false);
    }
  }, [router]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: uploading,
  });

  // Show loading only on initial page load
  if (isInitialLoading) {
    return (
      <div className="h-full flex items-center justify-center" aria-busy="true">
        <div role="status" aria-label="Loading dashboard">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      </div>
    );
  }

  // Check if user has no cases (new user flow)
  const hasCases = stats && stats.total_cases > 0;

  return (
    <div className="h-full">
      {/* Onboarding Wizard - shows for new users */}
      <OnboardingWizard />

      {/* Global Search Modal */}
      <GlobalSearch isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Quick Calculator Modal */}
      <QuickCalculatorModal
        isOpen={calculatorOpen}
        onClose={() => setCalculatorOpen(false)}
      />

      {/* Header Actions Bar */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-heading font-bold text-ink mb-2">Dashboard</h1>
          <p className="text-sm text-ink-secondary">
            Overview of all cases and deadlines
            {lastUpdated && (
              <span className="ml-2 text-slate-400">
                · Updated {formatTimeAgo(lastUpdated)}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCalculatorOpen(true)}
            className="btn-ghost"
            title="Quick Calculator"
          >
            <Calculator className="w-4 h-4" />
          </button>
          <button
            onClick={handleManualRefresh}
            className="btn-ghost"
            title="Refresh dashboard"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => router.push('/settings')}
            className="btn-ghost"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="space-y-6">
        {/* Critical Alert Banner - Show if Fatal/Critical deadlines exist */}
        {alerts && (alerts.overdue.count > 0 || alerts.urgent.count > 0) && (
          <div className="bg-fatal/10 border-l-4 border-fatal p-6 mb-6">
            <div className="flex items-start gap-4">
              <AlertTriangle className="w-6 h-6 text-fatal flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-lg font-heading font-semibold text-fatal mb-2">Critical Attention Required</h3>
                <p className="text-sm text-ink-secondary mb-3">
                  You have {alerts.overdue.count} overdue deadline{alerts.overdue.count !== 1 ? 's' : ''}
                  {alerts.urgent.count > 0 && ` and ${alerts.urgent.count} urgent deadline${alerts.urgent.count !== 1 ? 's' : ''}`} requiring immediate action.
                </p>
                <button
                  onClick={() => router.push('/calendar?filter=critical')}
                  className="btn-danger btn-sm"
                >
                  View Critical Deadlines
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Show upload prompt if no cases */}
        {!hasCases ? (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <Scale className="w-16 h-16 text-blue-600 mx-auto mb-4" />
              <h2 className="text-3xl font-bold text-slate-900 mb-2">Welcome to LitDocket</h2>
              <p className="text-slate-600">
                Get started by uploading your first court document. We'll analyze it and extract deadlines automatically.
              </p>
            </div>

            {/* Upload Dropzone */}
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
                transition-all duration-200
                ${isDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/30'
                }
                ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <input {...getInputProps()} />
              <Upload className={`w-16 h-16 mx-auto mb-4 ${isDragActive ? 'text-blue-600' : 'text-slate-400'}`} />
              <p className="text-xl font-semibold text-slate-800 mb-2">
                {uploading ? 'Uploading...' : isDragActive ? 'Drop your document here' : 'Upload Court Document'}
              </p>
              <p className="text-slate-600 mb-4">
                Drag and drop a PDF file, or click to browse
              </p>
              <p className="text-sm text-slate-500">
                Supported: Motions, Orders, Complaints, and other court filings
              </p>
            </div>

            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Quick Tools for new users */}
            <div className="mt-8">
              <QuickToolsGrid
                title="Quick Actions"
                tools={['calculator', 'jurisdiction', 'analyzer']}
                className="max-w-lg mx-auto"
              />
            </div>
          </div>
        ) : (
          <>
            {/* Error Display */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-800">Error loading dashboard</p>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
                <button
                  onClick={handleManualRefresh}
                  className="px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 rounded-lg transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Morning Briefing */}
            <div className="mb-8">
              <MorningReport onCaseClick={(caseId) => router.push(`/cases/${caseId}`)} />
            </div>

            {/* View Switcher - Clean Tabs */}
            <div className="mb-6">
              <div className="flex items-center justify-between">
                <div className="flex gap-0 bg-paper border border-ink">
                  <button
                    onClick={() => setActiveView('overview')}
                    className={`px-4 py-2 text-sm font-medium transition-transform ${
                      activeView === 'overview'
                        ? 'bg-steel text-white'
                        : 'text-ink hover:translate-x-0.5 hover:translate-y-0.5'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => setActiveView('heatmap')}
                    className={`px-4 py-2 text-sm font-medium border-l border-ink transition-transform ${
                      activeView === 'heatmap'
                        ? 'bg-steel text-white'
                        : 'text-ink hover:translate-x-0.5 hover:translate-y-0.5'
                    }`}
                  >
                    Heat Map
                  </button>
                  <button
                    onClick={() => setActiveView('cases')}
                    className={`px-4 py-2 text-sm font-medium border-l border-ink transition-transform ${
                      activeView === 'cases'
                        ? 'bg-steel text-white'
                        : 'text-ink hover:translate-x-0.5 hover:translate-y-0.5'
                    }`}
                  >
                    Cases
                  </button>
                </div>
              </div>
            </div>

            {/* Content based on active view */}
            {activeView === 'overview' && (
              <>
                {/* Stats Grid */}
                <Suspense fallback={<StatsSkeleton />}>
                  <StatsSection />
                </Suspense>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Left Column - Deadline Timeline */}
                  <div className="lg:col-span-2 space-y-6">
                    <Suspense fallback={<UpcomingSkeleton />}>
                      <UpcomingDeadlinesSection />
                    </Suspense>
                  </div>

                  {/* Right Column - Critical Cases & Recent Activity */}
                  <div className="space-y-6">
                    <CriticalCasesSection />
                    <Suspense fallback={<ActivitySkeleton />}>
                      <ActivityFeedSection />
                    </Suspense>
                  </div>
                </div>
              </>
            )}

            {activeView === 'heatmap' && (
              <div className="mb-8">
                <Suspense fallback={<HeatMapSkeleton />}>
                  <HeatMapSection />
                </Suspense>
              </div>
            )}

            {activeView === 'cases' && (
              <div className="mb-8">
                <Suspense fallback={<MatterHealthSkeleton />}>
                  <MatterHealthSection />
                </Suspense>
              </div>
            )}

            {/* Tool Suggestion when no critical items */}
            {activeView === 'overview' && alerts &&
              alerts.overdue.count === 0 &&
              alerts.urgent.count === 0 && (
              <div className="mt-6">
                <ToolSuggestionBanner
                  toolId="calculator"
                  message="Need to calculate a deadline?"
                />
              </div>
            )}

            {/* Quick Upload for Existing Users */}
            {activeView === 'overview' && (
              <div className="mt-8">
                <div className="card">
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">Upload More Documents</h3>
                  <div
                    {...getRootProps()}
                    className={`
                      border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
                      transition-all duration-200
                      ${isDragActive
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-300 bg-slate-50 hover:border-blue-400 hover:bg-blue-50/50'
                      }
                      ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                  >
                    <input {...getInputProps()} />
                    <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragActive ? 'text-blue-600' : 'text-slate-400'}`} />
                    <p className="font-medium text-slate-900 mb-1">
                      {uploading ? 'Uploading...' : isDragActive ? 'Drop here' : 'Upload Document'}
                    </p>
                    <p className="text-sm text-slate-600">
                      Drag & drop a PDF or click to browse
                    </p>
                  </div>
                  {error && (
                    <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
