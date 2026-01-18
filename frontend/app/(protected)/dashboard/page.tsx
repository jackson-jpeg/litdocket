'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import {
  Upload, FileText, AlertTriangle, Clock, CheckCircle, TrendingUp,
  Calendar, Folder, Scale, Loader2, AlertCircle, ChevronRight, Search, BarChart3, RefreshCw, LogOut, Settings
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import MorningReport from '@/components/MorningReport';
import DeadlineHeatMap from '@/components/DeadlineHeatMap';
import MatterHealthCards from '@/components/MatterHealthCards';
import DashboardCharts from '@/components/DashboardCharts';
import ActivityFeed from '@/components/ActivityFeed';
import GlobalSearch from '@/components/GlobalSearch';
import NotificationCenter from '@/components/NotificationCenter';
import { HeatMapSkeleton, MatterHealthSkeleton } from '@/components/Skeleton';
import { useAuth } from '@/lib/auth/auth-context';

interface DashboardData {
  case_statistics: {
    total_cases: number;
    total_documents: number;
    total_pending_deadlines: number;
    by_jurisdiction: {
      state: number;
      federal: number;
      unknown: number;
    };
    by_case_type: {
      civil: number;
      criminal: number;
      appellate: number;
      other: number;
    };
  };
  deadline_alerts: {
    overdue: { count: number; deadlines: any[] };
    urgent: { count: number; deadlines: any[] };
    upcoming_week: { count: number; deadlines: any[] };
    upcoming_month: { count: number; deadlines: any[] };
  };
  recent_activity: any[];
  critical_cases: any[];
  upcoming_deadlines: any[];
  heat_map?: {
    matrix: any;
    summary: any;
  };
  matter_health_cards?: any[];
}

export default function DashboardPage() {
  const router = useRouter();
  const { signOut, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeView, setActiveView] = useState<'overview' | 'heatmap' | 'cases'>('overview');
  const [refreshing, setRefreshing] = useState(false);

  const handleLogout = async () => {
    try {
      await signOut();
      router.push('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  // Auto-refresh dashboard data every 30 seconds when tab is visible
  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchDashboard();
      }
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, []);

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

  const fetchDashboard = async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setRefreshing(true);
    }

    try {
      const response = await apiClient.get('/api/v1/dashboard');
      setDashboardData(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
      if (isManualRefresh) {
        setRefreshing(false);
      }
    }
  };

  const handleManualRefresh = () => {
    fetchDashboard(true);
  };

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

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
      setUploading(false);
    }
  }, [router]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: uploading,
  });

  const getUrgencyColor = (urgencyLevel: string) => {
    switch (urgencyLevel) {
      case 'overdue': return 'bg-red-100 text-red-700 border-red-200';
      case 'urgent': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'upcoming-week': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      default: return 'bg-blue-100 text-blue-700 border-blue-200';
    }
  };

  const getUrgencyIcon = (urgencyLevel: string) => {
    switch (urgencyLevel) {
      case 'overdue': return <AlertTriangle className="w-4 h-4" />;
      case 'urgent': return <AlertCircle className="w-4 h-4" />;
      case 'upcoming-week': return <Clock className="w-4 h-4" />;
      default: return <Calendar className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-accent-info animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full">
      {/* Global Search Modal */}
      <GlobalSearch isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Header Actions Bar */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary mb-1">Dashboard</h1>
          <p className="text-sm text-text-muted">Overview of all cases and deadlines</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="btn-ghost disabled:opacity-50"
            title="Refresh dashboard"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setSearchOpen(true)}
            className="btn-ghost"
            title="Search (Cmd/Ctrl+K)"
          >
            <Search className="w-4 h-4" />
            <kbd className="ml-2 px-1.5 py-0.5 text-xxs bg-terminal-elevated text-text-muted rounded border border-border-subtle font-mono">
              ⌘K
            </kbd>
          </button>
        </div>
      </div>

      <div className="space-y-6">
        {/* Show upload prompt if no cases */}
        {dashboardData && dashboardData.case_statistics.total_cases === 0 ? (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <Scale className="w-16 h-16 text-accent-info mx-auto mb-4" />
              <h2 className="text-3xl font-bold text-text-primary mb-2">Welcome to LitDocket</h2>
              <p className="text-text-secondary">
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

            {/* View Switcher - Bloomberg Terminal Style */}
            <div className="mb-6">
              <div className="flex items-center justify-between">
                <div className="flex gap-2 bg-terminal-surface rounded-lg p-1 border border-border-subtle">
                  <button
                    onClick={() => setActiveView('overview')}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      activeView === 'overview'
                        ? 'bg-accent-info text-terminal-bg shadow-glow-info'
                        : 'text-text-secondary hover:bg-terminal-elevated hover:text-text-primary'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => setActiveView('heatmap')}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      activeView === 'heatmap'
                        ? 'bg-accent-info text-terminal-bg shadow-glow-info'
                        : 'text-text-secondary hover:bg-terminal-elevated hover:text-text-primary'
                    }`}
                  >
                    Heat Map
                  </button>
                  <button
                    onClick={() => setActiveView('cases')}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      activeView === 'cases'
                        ? 'bg-accent-info text-terminal-bg shadow-glow-info'
                        : 'text-text-secondary hover:bg-terminal-elevated hover:text-text-primary'
                    }`}
                  >
                    Cases
                  </button>
                </div>
                <p className="text-xs text-text-muted font-mono">
                  ⟳ Auto-refresh: 30s
                </p>
              </div>
            </div>

        {/* Content based on active view */}
        {activeView === 'overview' && (
          <>
            {/* Stats Grid - Enhanced Bloomberg Terminal Style */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {/* Critical/Overdue Card */}
              <div
                onClick={() => router.push('/calendar?filter=overdue')}
                className={`cursor-pointer hover:scale-105 transition-all duration-200 ${
                  (dashboardData?.deadline_alerts.overdue.count || 0) > 0
                    ? 'stat-card-critical hover:shadow-glow-critical'
                    : 'stat-card-success hover:shadow-glow-success'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold text-text-muted uppercase tracking-wide">Critical</div>
                  {(dashboardData?.deadline_alerts.overdue.count || 0) > 0 ? (
                    <TrendingUp className="w-3 h-3 text-accent-critical" />
                  ) : (
                    <CheckCircle className="w-3 h-3 text-accent-success" />
                  )}
                </div>
                <div className="flex items-baseline gap-2">
                  <span className={`text-4xl font-bold font-mono ${
                    (dashboardData?.deadline_alerts.overdue.count || 0) > 0
                      ? 'text-accent-critical'
                      : 'text-accent-success'
                  }`}>
                    {(dashboardData?.deadline_alerts.overdue.count || 0) +
                     (dashboardData?.deadline_alerts.urgent.count || 0)}
                  </span>
                  <span className={`text-xs font-mono ${
                    (dashboardData?.deadline_alerts.overdue.count || 0) > 0
                      ? 'text-accent-critical'
                      : 'text-accent-success'
                  }`}>
                    {(dashboardData?.deadline_alerts.overdue.count || 0) > 0 ? '+20%' : '0'}
                  </span>
                </div>
                <div className="text-xs text-text-secondary mt-1">
                  {dashboardData?.deadline_alerts.overdue.count || 0} overdue, {dashboardData?.deadline_alerts.urgent.count || 0} urgent
                </div>
              </div>

              {/* Pending Deadlines */}
              <div
                onClick={() => router.push('/calendar?filter=pending')}
                className="stat-card-warning cursor-pointer hover:scale-105 transition-all duration-200 hover:shadow-glow-warning"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold text-text-muted uppercase tracking-wide">Pending</div>
                  <Clock className="w-4 h-4 text-accent-warning" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold font-mono text-accent-warning">
                    {dashboardData?.case_statistics.total_pending_deadlines || 0}
                  </span>
                  <span className="text-xs font-mono text-text-muted">+3%</span>
                </div>
                <div className="text-xs text-text-secondary mt-1">
                  {dashboardData?.deadline_alerts.upcoming_week.count || 0} this week · {dashboardData?.deadline_alerts.upcoming_month.count || 0} this month
                </div>
              </div>

              {/* Active Cases */}
              <div
                onClick={() => router.push('/cases')}
                className="stat-card-info cursor-pointer hover:scale-105 transition-all duration-200 hover:shadow-glow-info"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold text-text-muted uppercase tracking-wide">Cases</div>
                  <TrendingUp className="w-3 h-3 text-accent-success" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold font-mono text-accent-info">
                    {dashboardData?.case_statistics.total_cases || 0}
                  </span>
                  <span className="text-xs font-mono text-accent-success">+5%</span>
                </div>
                <div className="text-xs text-text-secondary mt-1">
                  {dashboardData?.case_statistics.by_jurisdiction.state || 0} State · {dashboardData?.case_statistics.by_jurisdiction.federal || 0} Federal
                </div>
              </div>

              {/* Documents */}
              <div
                onClick={() => router.push('/cases')}
                className="stat-card cursor-pointer hover:scale-105 transition-all duration-200 hover:shadow-glow-info border-l-4 border-l-accent-purple"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold text-text-muted uppercase tracking-wide">Documents</div>
                  <TrendingUp className="w-3 h-3 text-accent-success" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold font-mono text-accent-purple">
                    {dashboardData?.case_statistics.total_documents || 0}
                  </span>
                  <span className="text-xs font-mono text-accent-success">+8%</span>
                </div>
                {dashboardData && dashboardData.case_statistics.total_cases > 0 && (
                  <div className="text-xs text-text-secondary mt-1">
                    ~{Math.round(dashboardData.case_statistics.total_documents / dashboardData.case_statistics.total_cases)} per case
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column - Deadline Alerts & Upload */}
              <div className="lg:col-span-2 space-y-6">
                {/* Critical Deadline Alerts */}
                {dashboardData && (dashboardData.deadline_alerts.overdue.count > 0 ||
                                    dashboardData.deadline_alerts.urgent.count > 0) && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                    <div className="p-6 border-b border-slate-200">
                      <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-red-500" />
                        Critical Deadlines
                      </h3>
                    </div>
                    <div className="p-6 space-y-3 max-h-96 overflow-y-auto">
                      {dashboardData.deadline_alerts.overdue.deadlines.map((deadline) => (
                        <div
                          key={deadline.id}
                          className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg cursor-pointer hover:bg-red-100 transition-colors"
                          onClick={() => router.push(`/cases/${deadline.case_id}`)}
                        >
                          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-800 truncate">{deadline.title}</p>
                            <p className="text-sm text-red-700 mt-1">
                              OVERDUE: {deadline.deadline_date} ({Math.abs(deadline.days_until)} days ago)
                            </p>
                            {deadline.action_required && (
                              <p className="text-sm text-slate-600 mt-1">{deadline.action_required}</p>
                            )}
                          </div>
                          <ChevronRight className="w-5 h-5 text-slate-400" />
                        </div>
                      ))}

                      {dashboardData.deadline_alerts.urgent.deadlines.map((deadline) => (
                        <div
                          key={deadline.id}
                          className="flex items-start gap-3 p-4 bg-orange-50 border border-orange-200 rounded-lg cursor-pointer hover:bg-orange-100 transition-colors"
                          onClick={() => router.push(`/cases/${deadline.case_id}`)}
                        >
                          <AlertCircle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-800 truncate">{deadline.title}</p>
                            <p className="text-sm text-orange-700 mt-1">
                              Due: {deadline.deadline_date} ({deadline.days_until} days)
                            </p>
                            {deadline.action_required && (
                              <p className="text-sm text-slate-600 mt-1">{deadline.action_required}</p>
                            )}
                          </div>
                          <ChevronRight className="w-5 h-5 text-slate-400" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Upcoming Deadlines */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                  <div className="p-6 border-b border-slate-200">
                    <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                      <Calendar className="w-5 h-5 text-blue-500" />
                      Upcoming Deadlines
                    </h3>
                  </div>
                  <div className="p-6 space-y-3 max-h-96 overflow-y-auto">
                    {dashboardData?.upcoming_deadlines.slice(0, 10).map((deadline) => (
                      <div
                        key={deadline.id}
                        className={`
                          flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-colors
                          ${getUrgencyColor(deadline.urgency_level)} hover:opacity-80
                        `}
                        onClick={() => router.push(`/cases/${deadline.case_id}`)}
                      >
                        {getUrgencyIcon(deadline.urgency_level)}
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-slate-800 truncate">{deadline.title}</p>
                          <p className="text-sm mt-1">
                            {deadline.deadline_date} ({deadline.days_until} days)
                          </p>
                          {deadline.party_role && (
                            <p className="text-xs mt-1">Party: {deadline.party_role}</p>
                          )}
                        </div>
                        <ChevronRight className="w-5 h-5" />
                      </div>
                    ))}

                    {(!dashboardData?.upcoming_deadlines || dashboardData.upcoming_deadlines.length === 0) && (
                      <div className="text-center py-8 text-slate-500">
                        <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
                        <p>No upcoming deadlines</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column - Critical Cases & Recent Activity */}
              <div className="space-y-6">
                {/* Critical Cases */}
                {dashboardData && dashboardData.critical_cases.length > 0 && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                    <div className="p-6 border-b border-slate-200">
                      <h3 className="text-lg font-semibold text-slate-800">Critical Cases</h3>
                    </div>
                    <div className="p-6 space-y-3">
                      {dashboardData.critical_cases.slice(0, 5).map((caseItem) => (
                        <div
                          key={caseItem.case_id}
                          className="p-4 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors"
                          onClick={() => router.push(`/cases/${caseItem.case_id}`)}
                        >
                          <p className="font-medium text-slate-800">{caseItem.case_number}</p>
                          <p className="text-sm text-slate-600 mt-1">{caseItem.title}</p>
                          <div className="mt-3 flex items-center justify-between">
                            <span className={`
                              text-xs px-2 py-1 rounded
                              ${caseItem.urgency_level === 'critical' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}
                            `}>
                              {caseItem.days_until_deadline} days until deadline
                            </span>
                            <ChevronRight className="w-4 h-4 text-slate-400" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Activity */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                  <div className="p-6 border-b border-slate-200">
                    <h3 className="text-lg font-semibold text-slate-800">Recent Activity</h3>
                  </div>
                  <div className="p-6 space-y-4">
                    {dashboardData?.recent_activity.slice(0, 8).map((activity, idx) => (
                      <div key={idx} className="flex items-start gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <FileText className="w-4 h-4 text-blue-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-800 truncate">
                            {activity.case_number}
                          </p>
                          <p className="text-xs text-slate-600 truncate">
                            {activity.description}
                          </p>
                          <p className="text-xs text-slate-400 mt-1">
                            {new Date(activity.timestamp).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    ))}

                    {(!dashboardData?.recent_activity || dashboardData.recent_activity.length === 0) && (
                      <p className="text-center text-slate-500 py-4">No recent activity</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

            {activeView === 'heatmap' && (
              <div className="mb-8">
                {loading ? (
                  <HeatMapSkeleton />
                ) : dashboardData?.heat_map ? (
                  <DeadlineHeatMap
                    heatMapData={dashboardData.heat_map}
                    onCaseClick={(caseId) => router.push(`/cases/${caseId}`)}
                  />
                ) : (
                  <div className="panel-glass p-12 text-center">
                    <Calendar className="w-16 h-16 text-text-muted mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-text-primary mb-2">
                      No Heat Map Data
                    </h3>
                    <p className="text-sm text-text-secondary">
                      Add deadlines to cases to see the deadline heat map visualization
                    </p>
                  </div>
                )}
              </div>
            )}

            {activeView === 'cases' && (
              <div className="mb-8">
                {loading ? (
                  <MatterHealthSkeleton />
                ) : dashboardData?.matter_health_cards && dashboardData.matter_health_cards.length > 0 ? (
                  <MatterHealthCards
                    healthCards={dashboardData.matter_health_cards}
                    onCaseClick={(caseId) => router.push(`/cases/${caseId}`)}
                  />
                ) : (
                  <div className="panel-glass p-12 text-center">
                    <Folder className="w-16 h-16 text-text-muted mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-text-primary mb-2">
                      No Cases with Pending Deadlines
                    </h3>
                    <p className="text-sm text-text-secondary mb-6">
                      All cases are up to date or have no active deadlines
                    </p>
                    <button
                      onClick={() => router.push('/cases')}
                      className="btn-primary"
                    >
                      View All Cases
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Quick Upload for Existing Users */}
            {activeView === 'overview' && (
              <div className="mt-8">
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-slate-800 mb-4">Upload New Document</h3>
                  <div
                    {...getRootProps()}
                    className={`
                      border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
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
                    <p className="font-medium text-slate-700 mb-1">
                      {uploading ? 'Uploading...' : isDragActive ? 'Drop here' : 'Upload Document'}
                    </p>
                    <p className="text-sm text-slate-500">
                      Drag & drop a PDF or click to browse
                    </p>
                  </div>
                  {error && (
                    <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
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
