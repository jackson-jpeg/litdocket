'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import {
  Upload, FileText, AlertTriangle, Clock, CheckCircle, TrendingUp,
  Calendar, Folder, Scale, Loader2, AlertCircle, ChevronRight, Search, BarChart3, RefreshCw, LogOut, Settings
} from 'lucide-react';
import apiClient, { extractApiError, ApiError } from '@/lib/api-client';
import MorningReport from '@/features/dashboard/components/MorningReport';
import DeadlineHeatMap from '@/shared/components/ui/DeadlineHeatMap';
import MatterHealthCards from '@/features/dashboard/components/MatterHealthCards';
import DashboardCharts from '@/features/dashboard/components/DashboardCharts';
import ActivityFeed from '@/features/dashboard/components/ActivityFeed';
import GlobalSearch from '@/shared/components/ui/GlobalSearch';
import NotificationCenter from '@/shared/components/ui/NotificationCenter';
import { HeatMapSkeleton, MatterHealthSkeleton } from '@/shared/components/ui/Skeleton';
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

      // Validate response data structure
      const data = response.data;
      if (data) {
        // Ensure required nested structures exist with defaults
        const validatedData: DashboardData = {
          case_statistics: data.case_statistics || {
            total_cases: 0,
            total_documents: 0,
            total_pending_deadlines: 0,
            by_jurisdiction: { state: 0, federal: 0, unknown: 0 },
            by_case_type: { civil: 0, criminal: 0, appellate: 0, other: 0 }
          },
          deadline_alerts: data.deadline_alerts || {
            overdue: { count: 0, deadlines: [] },
            urgent: { count: 0, deadlines: [] },
            upcoming_week: { count: 0, deadlines: [] },
            upcoming_month: { count: 0, deadlines: [] }
          },
          recent_activity: data.recent_activity || [],
          critical_cases: data.critical_cases || [],
          upcoming_deadlines: data.upcoming_deadlines || [],
          heat_map: data.heat_map,
          matter_health_cards: data.matter_health_cards || []
        };
        setDashboardData(validatedData);
      }
      setError(null);
    } catch (err: unknown) {
      console.error('Failed to load dashboard:', err);
      const apiError = extractApiError(err);
      setError(apiError.message);
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
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full">
      {/* Global Search Modal */}
      <GlobalSearch isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Header Actions Bar */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Dashboard</h1>
          <p className="text-sm text-slate-500">Overview of all cases and deadlines</p>
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
        {dashboardData && (dashboardData.deadline_alerts.overdue.count > 0 || dashboardData.deadline_alerts.urgent.count > 0) && (
          <div className="bg-red-50 border-l-4 border-red-600 rounded-lg p-6 mb-6">
            <div className="flex items-start gap-4">
              <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-900 mb-2">Critical Attention Required</h3>
                <p className="text-sm text-red-800 mb-3">
                  You have {dashboardData.deadline_alerts.overdue.count} overdue deadline{dashboardData.deadline_alerts.overdue.count !== 1 ? 's' : ''}
                  {dashboardData.deadline_alerts.urgent.count > 0 && ` and ${dashboardData.deadline_alerts.urgent.count} urgent deadline${dashboardData.deadline_alerts.urgent.count !== 1 ? 's' : ''}`} requiring immediate action.
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
        {dashboardData && dashboardData.case_statistics.total_cases === 0 ? (
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
                <div className="flex gap-2 bg-white rounded-lg p-1 border border-slate-200">
                  <button
                    onClick={() => setActiveView('overview')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeView === 'overview'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => setActiveView('heatmap')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeView === 'heatmap'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Heat Map
                  </button>
                  <button
                    onClick={() => setActiveView('cases')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeView === 'cases'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Cases
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  Auto-refresh: 30s
                </p>
              </div>
            </div>

        {/* Content based on active view */}
        {activeView === 'overview' && (
          <>
            {/* Stats Grid - Clean Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Critical/Overdue Card */}
              <div
                onClick={() => router.push('/calendar?filter=overdue')}
                className="card-hover cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Critical</div>
                  {(dashboardData?.deadline_alerts.overdue.count || 0) > 0 ? (
                    <div className="w-2 h-2 rounded-full bg-red-600"></div>
                  ) : (
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  )}
                </div>
                <div className="flex items-baseline gap-2 mb-2">
                  <span className={`text-4xl font-bold ${
                    (dashboardData?.deadline_alerts.overdue.count || 0) > 0
                      ? 'text-red-600'
                      : 'text-green-600'
                  }`}>
                    {(dashboardData?.deadline_alerts.overdue.count || 0) +
                     (dashboardData?.deadline_alerts.urgent.count || 0)}
                  </span>
                </div>
                <p className="text-sm text-slate-600">
                  {dashboardData?.deadline_alerts.overdue.count || 0} overdue, {dashboardData?.deadline_alerts.urgent.count || 0} urgent
                </p>
              </div>

              {/* Pending Deadlines */}
              <div
                onClick={() => router.push('/calendar?filter=pending')}
                className="card-hover cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Pending</div>
                  <Clock className="w-4 h-4 text-amber-600" />
                </div>
                <div className="flex items-baseline gap-2 mb-2">
                  <span className="text-4xl font-bold text-amber-600">
                    {dashboardData?.case_statistics.total_pending_deadlines || 0}
                  </span>
                </div>
                <p className="text-sm text-slate-600">
                  {dashboardData?.deadline_alerts.upcoming_week.count || 0} this week · {dashboardData?.deadline_alerts.upcoming_month.count || 0} this month
                </p>
              </div>

              {/* Active Cases */}
              <div
                onClick={() => router.push('/cases')}
                className="card-hover cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Cases</div>
                  <Folder className="w-4 h-4 text-blue-600" />
                </div>
                <div className="flex items-baseline gap-2 mb-2">
                  <span className="text-4xl font-bold text-blue-600">
                    {dashboardData?.case_statistics.total_cases || 0}
                  </span>
                </div>
                <p className="text-sm text-slate-600">
                  {dashboardData?.case_statistics.by_jurisdiction.state || 0} State · {dashboardData?.case_statistics.by_jurisdiction.federal || 0} Federal
                </p>
              </div>

              {/* Documents */}
              <div
                onClick={() => router.push('/cases')}
                className="card-hover cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Documents</div>
                  <FileText className="w-4 h-4 text-purple-600" />
                </div>
                <div className="flex items-baseline gap-2 mb-2">
                  <span className="text-4xl font-bold text-purple-600">
                    {dashboardData?.case_statistics.total_documents || 0}
                  </span>
                </div>
                {dashboardData && dashboardData.case_statistics.total_cases > 0 && (
                  <p className="text-sm text-slate-600">
                    ~{Math.round(dashboardData.case_statistics.total_documents / dashboardData.case_statistics.total_cases)} per case
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column - Deadline Timeline */}
              <div className="lg:col-span-2 space-y-6">
                {/* Upcoming Deadlines - Timeline View */}
                <div className="card">
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
                      <Calendar className="w-5 h-5 text-blue-600" />
                      Upcoming Deadlines
                    </h3>
                  </div>

                  {dashboardData?.upcoming_deadlines && dashboardData.upcoming_deadlines.length > 0 ? (
                    <div className="timeline">
                      {dashboardData.upcoming_deadlines.slice(0, 10).map((deadline) => (
                        <div
                          key={deadline.id}
                          className="timeline-item cursor-pointer group"
                          onClick={() => router.push(`/cases/${deadline.case_id}`)}
                        >
                          <div className={`timeline-dot ${
                            deadline.urgency_level === 'overdue' ? 'bg-red-600' :
                            deadline.urgency_level === 'urgent' ? 'bg-orange-600' :
                            deadline.urgency_level === 'upcoming-week' ? 'bg-amber-500' : 'bg-blue-500'
                          }`}></div>
                          <div className="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-slate-900 truncate group-hover:text-blue-600">{deadline.title}</p>
                                <p className="text-sm text-slate-600 mt-1">
                                  {deadline.deadline_date} • {Math.abs(deadline.days_until)} day{Math.abs(deadline.days_until) !== 1 ? 's' : ''} {deadline.days_until < 0 ? 'overdue' : 'remaining'}
                                </p>
                                {deadline.action_required && (
                                  <p className="text-sm text-slate-500 mt-2">{deadline.action_required}</p>
                                )}
                                {deadline.party_role && (
                                  <span className="inline-block mt-2 text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">
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
                    <div className="text-center py-12 text-slate-500">
                      <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-600" />
                      <p className="font-medium">All clear!</p>
                      <p className="text-sm mt-1">No upcoming deadlines</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column - Critical Cases & Recent Activity */}
              <div className="space-y-6">
                {/* Critical Cases */}
                {dashboardData && dashboardData.critical_cases.length > 0 && (
                  <div className="card">
                    <h3 className="text-lg font-semibold text-slate-900 mb-4">Critical Cases</h3>
                    <div className="space-y-3">
                      {dashboardData.critical_cases.slice(0, 5).map((caseItem) => (
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
                )}

                {/* Recent Activity */}
                <div className="card">
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">Recent Activity</h3>
                  <div className="space-y-4">
                    {dashboardData?.recent_activity.slice(0, 8).map((activity, idx) => (
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

                    {(!dashboardData?.recent_activity || dashboardData.recent_activity.length === 0) && (
                      <p className="text-center text-slate-500 py-4 text-sm">No recent activity</p>
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
                  <div className="card text-center py-16">
                    <Calendar className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">
                      No Heat Map Data
                    </h3>
                    <p className="text-sm text-slate-600">
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
                )}
              </div>
            )}

            {/* Quick Upload for Existing Users */}
            {activeView === 'overview' && (
              <div className="mt-8">
                <div className="card">
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">Upload New Document</h3>
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
