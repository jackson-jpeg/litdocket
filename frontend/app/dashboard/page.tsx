'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import {
  Upload, FileText, AlertTriangle, Clock, CheckCircle, TrendingUp,
  Calendar, Folder, Scale, Loader2, AlertCircle, ChevronRight, Bell
} from 'lucide-react';
import apiClient from '@/lib/api-client';

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
}

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await apiClient.get('/api/v1/dashboard');
      setDashboardData(response.data);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push('/')}>
              <Scale className="w-7 h-7 text-blue-600" />
              <h1 className="text-xl font-bold text-slate-800">
                Florida Legal Docketing Assistant
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/cases')}
                className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors font-medium"
              >
                All Cases
              </button>
              <button
                onClick={() => router.push('/')}
                className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors font-medium"
              >
                Upload Document
              </button>
              <button className="p-2 hover:bg-slate-100 rounded-lg relative">
                <Bell className="w-5 h-5 text-slate-600" />
                {dashboardData && (dashboardData.deadline_alerts.overdue.count + dashboardData.deadline_alerts.urgent.count) > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Dashboard</h2>
          <p className="text-slate-600">Overview of your cases and upcoming deadlines</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Cases */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Folder className="w-6 h-6 text-blue-600" />
              </div>
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <h3 className="text-3xl font-bold text-slate-800">
              {dashboardData?.case_statistics.total_cases || 0}
            </h3>
            <p className="text-sm text-slate-600 mt-1">Total Cases</p>
          </div>

          {/* Pending Deadlines */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-orange-100 rounded-lg">
                <Clock className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <h3 className="text-3xl font-bold text-slate-800">
              {dashboardData?.case_statistics.total_pending_deadlines || 0}
            </h3>
            <p className="text-sm text-slate-600 mt-1">Pending Deadlines</p>
          </div>

          {/* Documents */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-purple-100 rounded-lg">
                <FileText className="w-6 h-6 text-purple-600" />
              </div>
            </div>
            <h3 className="text-3xl font-bold text-slate-800">
              {dashboardData?.case_statistics.total_documents || 0}
            </h3>
            <p className="text-sm text-slate-600 mt-1">Documents Filed</p>
          </div>

          {/* Overdue/Urgent */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-red-100 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
            </div>
            <h3 className="text-3xl font-bold text-slate-800">
              {(dashboardData?.deadline_alerts.overdue.count || 0) +
               (dashboardData?.deadline_alerts.urgent.count || 0)}
            </h3>
            <p className="text-sm text-slate-600 mt-1">Needs Attention</p>
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

            {/* Quick Upload */}
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
                transition-all duration-200
                ${isDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/30'
                }
                ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <input {...getInputProps()} />
              <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragActive ? 'text-blue-600' : 'text-slate-400'}`} />
              <p className="font-medium text-slate-700 mb-1">
                {uploading ? 'Uploading...' : 'Upload New Document'}
              </p>
              <p className="text-sm text-slate-500">
                Drag & drop a PDF or click to select
              </p>
            </div>

            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}
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
      </main>
    </div>
  );
}
