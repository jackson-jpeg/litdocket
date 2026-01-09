'use client';

/**
 * CaseQuickView - Right-Side Drawer for Quick Case Preview
 *
 * Gold Standard Design System:
 * - Slide-over drawer (40% of screen)
 * - Critical Deadlines (Top 3)
 * - Recent Filings (Last 3)
 * - Quick actions without full navigation
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  X,
  Calendar,
  Clock,
  FileText,
  Upload,
  ChevronRight,
  AlertTriangle,
  CheckCircle,
  Scale,
  User,
  Building,
  ExternalLink,
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface Case {
  id: string;
  case_number: string;
  title: string;
  court: string;
  judge: string;
  jurisdiction: string;
  case_type: string;
  status: string;
}

interface Deadline {
  id: string;
  title: string;
  deadline_date: string;
  priority: string;
  status: string;
}

interface Document {
  id: string;
  filename: string;
  document_type: string;
  created_at: string;
}

interface CaseQuickViewProps {
  isOpen: boolean;
  caseData: Case | null;
  onClose: () => void;
}

export default function CaseQuickView({ isOpen, caseData, onClose }: CaseQuickViewProps) {
  const router = useRouter();
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && caseData) {
      fetchCaseDetails();
    }
  }, [isOpen, caseData?.id]);

  const fetchCaseDetails = async () => {
    if (!caseData) return;
    setLoading(true);
    try {
      const [deadlinesRes, docsRes] = await Promise.all([
        apiClient.get(`/api/v1/deadlines/case/${caseData.id}`).catch(() => ({ data: [] })),
        apiClient.get(`/api/v1/cases/${caseData.id}/documents`).catch(() => ({ data: [] })),
      ]);

      // Get pending deadlines sorted by date
      const pendingDeadlines = (deadlinesRes.data || [])
        .filter((d: Deadline) => d.status === 'pending')
        .sort((a: Deadline, b: Deadline) =>
          new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime()
        )
        .slice(0, 3);

      // Get recent documents sorted by date
      const recentDocs = (docsRes.data || [])
        .sort((a: Document, b: Document) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        .slice(0, 3);

      setDeadlines(pendingDeadlines);
      setDocuments(recentDocs);
    } catch (err) {
      console.error('Failed to fetch case details:', err);
    } finally {
      setLoading(false);
    }
  };

  const getDeadlineUrgency = (deadline: Deadline) => {
    const days = Math.ceil(
      (new Date(deadline.deadline_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );
    if (days < 0) return { color: 'border-red-500 bg-red-50', text: 'OVERDUE', textColor: 'text-red-600' };
    if (days <= 3) return { color: 'border-orange-500 bg-orange-50', text: `${days}d`, textColor: 'text-orange-600' };
    if (days <= 7) return { color: 'border-yellow-500 bg-yellow-50', text: `${days}d`, textColor: 'text-yellow-600' };
    return { color: 'border-blue-500 bg-blue-50', text: `${days}d`, textColor: 'text-blue-600' };
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'fatal':
        return <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-xs font-bold rounded">FATAL</span>;
      case 'critical':
        return <span className="px-1.5 py-0.5 bg-red-50 text-red-600 text-xs font-medium rounded">CRITICAL</span>;
      case 'important':
        return <span className="px-1.5 py-0.5 bg-amber-50 text-amber-600 text-xs font-medium rounded">IMPORTANT</span>;
      default:
        return null;
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl z-50 flex flex-col transform transition-transform">
        {/* Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Scale className="w-5 h-5 text-blue-400" />
            <span className="font-semibold">Quick View</span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {caseData && (
          <>
            {/* Case Info */}
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <p className="font-mono text-sm text-blue-600 font-medium mb-1">
                {caseData.case_number}
              </p>
              <h2 className="font-semibold text-slate-900 text-lg leading-tight mb-3">
                {caseData.title}
              </h2>
              <div className="flex flex-wrap gap-2 text-xs">
                {caseData.court && (
                  <span className="flex items-center gap-1 px-2 py-1 bg-white border border-slate-200 rounded">
                    <Building className="w-3 h-3 text-slate-400" />
                    {caseData.court}
                  </span>
                )}
                {caseData.judge && (
                  <span className="flex items-center gap-1 px-2 py-1 bg-white border border-slate-200 rounded">
                    <User className="w-3 h-3 text-slate-400" />
                    Judge {caseData.judge}
                  </span>
                )}
                {caseData.status && (
                  <span className={`px-2 py-1 rounded font-medium ${
                    caseData.status === 'active' ? 'bg-green-100 text-green-700' :
                    caseData.status === 'stayed' ? 'bg-amber-100 text-amber-700' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {caseData.status.toUpperCase()}
                  </span>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="p-6 text-center text-slate-500">
                  Loading...
                </div>
              ) : (
                <>
                  {/* Critical Deadlines */}
                  <div className="p-6 border-b border-slate-200">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-orange-500" />
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                          Critical Deadlines
                        </h3>
                      </div>
                      <span className="text-xs text-slate-400">{deadlines.length} upcoming</span>
                    </div>

                    {deadlines.length > 0 ? (
                      <div className="space-y-3">
                        {deadlines.map((deadline) => {
                          const urgency = getDeadlineUrgency(deadline);
                          return (
                            <div
                              key={deadline.id}
                              className={`border-l-4 ${urgency.color} p-3 rounded-r-lg`}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <p className="text-sm font-medium text-slate-800 leading-tight">
                                    {deadline.title}
                                  </p>
                                  <div className="flex items-center gap-2 mt-1">
                                    <span className={`text-xs font-mono font-bold ${urgency.textColor}`}>
                                      {new Date(deadline.deadline_date).toLocaleDateString()}
                                    </span>
                                    {getPriorityBadge(deadline.priority)}
                                  </div>
                                </div>
                                <span className={`text-xs font-bold ${urgency.textColor}`}>
                                  {urgency.text}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-center py-4 text-slate-500 text-sm bg-slate-50 rounded-lg">
                        <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
                        No pending deadlines
                      </div>
                    )}
                  </div>

                  {/* Recent Filings */}
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-blue-500" />
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                          Recent Filings
                        </h3>
                      </div>
                      <span className="text-xs text-slate-400">{documents.length} shown</span>
                    </div>

                    {documents.length > 0 ? (
                      <div className="space-y-2">
                        {documents.map((doc) => (
                          <div
                            key={doc.id}
                            className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                          >
                            <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-slate-700 truncate">
                                {doc.filename}
                              </p>
                              <p className="text-xs text-slate-500">
                                {doc.document_type || 'Document'} · {new Date(doc.created_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-4 text-slate-500 text-sm bg-slate-50 rounded-lg">
                        No documents yet
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Footer Actions */}
            <div className="border-t border-slate-200 p-4 bg-slate-50">
              <div className="grid grid-cols-2 gap-3 mb-3">
                <button
                  onClick={() => {
                    onClose();
                    router.push(`/cases/${caseData.id}`);
                  }}
                  className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors text-sm font-medium"
                >
                  <Upload className="w-4 h-4" />
                  Upload Doc
                </button>
                <button
                  onClick={() => {
                    onClose();
                    router.push('/calendar');
                  }}
                  className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors text-sm font-medium"
                >
                  <Calendar className="w-4 h-4" />
                  View Calendar
                </button>
              </div>
              <button
                onClick={() => {
                  onClose();
                  router.push(`/cases/${caseData.id}`);
                }}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors font-medium"
              >
                Go to Case Dashboard
                <ExternalLink className="w-4 h-4" />
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
