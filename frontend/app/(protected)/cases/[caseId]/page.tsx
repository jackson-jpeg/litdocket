'use client';

/**
 * Case Detail - Paper & Steel Design
 *
 * Single Column Layout:
 * - Top: Case Header (Title, Number, Court)
 * - Middle: Stats Row (Simple numbers)
 * - Main: Deadlines List (grouped by timeframe)
 * - Documents: Integrated inline section
 */

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { FileText, Upload, Eye, Trash2, Calendar, Clock, AlertTriangle, Building, User, Scale, ChevronRight } from 'lucide-react';
import apiClient from '@/lib/api-client';
import { useCaseData, Trigger, Deadline } from '@/features/cases/hooks/useCaseData';
import { useToast } from '@/shared/components/ui/Toast';
import { formatDateTime, formatDeadlineDate } from '@/lib/formatters';
import DocumentViewerWrapper from '@/shared/components/ui/DocumentViewerWrapper';
import TriggerModal from './triggers/TriggerModal';
import EditTriggerModal from '@/features/cases/components/triggers/EditTriggerModal';
import AddTriggerModal from '@/features/cases/components/triggers/AddTriggerModal';
import TriggerAlertBar from '@/features/cases/components/triggers/TriggerAlertBar';
import DeadlineListPanel from '@/features/cases/components/deadlines/DeadlineListPanel';
import DeadlineDetailModal from '@/features/cases/components/deadlines/DeadlineDetailModal';
import DeadlineChainView from '@/features/cases/components/deadlines/DeadlineChainView';
import { useCaseSync } from '@/features/cases/hooks/useCaseSync';
import { deadlineEvents } from '@/lib/eventBus';
import type { Document } from '@/types';

export default function CaseRoomPage() {
  const params = useParams();
  const caseId = params.caseId as string;
  const { caseData, documents, deadlines, triggers, caseSummary, loading, error, refetch, optimistic } = useCaseData(caseId);
  const { showSuccess, showError } = useToast();

  // Setup case synchronization
  useCaseSync({
    caseId,
    onDeadlinesUpdate: () => refetch.deadlines(),
    onDocumentsUpdate: () => refetch.documents(),
    onTriggersUpdate: () => refetch.triggers(),
    onCaseUpdate: () => refetch.caseSummary(),
    onInsightsUpdate: () => {},
  });

  // UI state
  const [triggerModalOpen, setTriggerModalOpen] = useState(false);
  const [addTriggerModalOpen, setAddTriggerModalOpen] = useState(false);
  const [editingTrigger, setEditingTrigger] = useState<Trigger | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const [viewingDeadline, setViewingDeadline] = useState<Deadline | null>(null);
  const [viewingChainTrigger, setViewingChainTrigger] = useState<Trigger | null>(null);

  // Document upload state
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Handlers
  const handleTriggerSuccess = () => {
    refetch.deadlines();
    refetch.triggers();
    refetch.caseSummary();
    showSuccess('Trigger created successfully');
  };

  const handleDocumentClick = (doc: Document) => {
    if (!doc.storage_url) {
      showError('This document cannot be opened. The file may not be available on the server.');
      return;
    }
    setViewingDocument(doc);
  };

  const handleDocumentDelete = async (doc: Document, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Delete "${doc.file_name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      optimistic.removeDocument(doc.id);
      await apiClient.delete(`/api/v1/documents/${doc.id}`);
      showSuccess('Document deleted');
      refetch.documents();
    } catch (err: any) {
      refetch.documents();
      if (err.response?.status === 404) {
        showError('Document not found. It may have already been deleted.');
      } else if (err.response?.status === 403) {
        showError('You do not have permission to delete this document.');
      } else {
        showError('Failed to delete document. Please try again.');
      }
    }
  };

  const handleDocumentUpload = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('case_id', caseId);

      const response = await apiClient.post('/api/v1/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      await Promise.all([
        refetch.documents(),
        refetch.deadlines(),
        refetch.caseSummary()
      ]);

      setShowUploadDialog(false);
      showSuccess(`Document uploaded. ${response.data.deadlines_extracted || 0} deadline(s) extracted.`);
    } catch (err: any) {
      showError(err.response?.data?.detail || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  const handleComplete = async (id: string) => {
    try {
      optimistic.updateDeadlineStatus(id, 'completed');
      await apiClient.patch(`/api/v1/deadlines/${id}/status?status=completed`);
      deadlineEvents.updated({ id, status: 'completed' });
      showSuccess('Deadline completed');
    } catch (err) {
      refetch.deadlines();
      showError('Failed to complete deadline');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this deadline?')) return;
    try {
      optimistic.removeDeadline(id);
      await apiClient.delete(`/api/v1/deadlines/${id}`);
      deadlineEvents.deleted(id);
      showSuccess('Deadline deleted');
    } catch (err) {
      refetch.deadlines();
      showError('Failed to delete deadline');
    }
  };

  const exportToCalendar = async () => {
    try {
      const response = await apiClient.get(`/api/v1/deadlines/case/${caseId}/export/ical`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `deadlines_${caseData?.case_number?.replace('/', '-')}.ics`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      showSuccess('Calendar exported');
    } catch (err) {
      showError('Failed to export calendar');
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent animate-spin mx-auto mb-4 rounded-full" />
          <p className="text-slate-600 text-sm">Loading case data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="card max-w-md text-center py-12">
          <AlertTriangle className="w-12 h-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Error Loading Case</h2>
          <p className="text-slate-600 mb-6">{error}</p>
          <button onClick={() => window.location.reload()} className="btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!caseData) return null;

  // Stats
  const overdueCount = deadlines.filter(d => {
    const isActive = d.status !== 'completed' && d.status !== 'cancelled';
    const isOverdue = d.deadline_date && new Date(d.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));
    return isActive && isOverdue;
  }).length;

  const pendingCount = deadlines.filter(d => d.status !== 'completed' && d.status !== 'cancelled').length;

  // Group deadlines by timeframe
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const weekFromNow = new Date(today);
  weekFromNow.setDate(weekFromNow.getDate() + 7);
  const monthFromNow = new Date(today);
  monthFromNow.setDate(monthFromNow.getDate() + 30);

  const activeDeadlines = deadlines.filter(d => d.status !== 'completed' && d.status !== 'cancelled');

  const thisWeekDeadlines = activeDeadlines.filter(d => {
    if (!d.deadline_date) return false;
    const deadlineDate = new Date(d.deadline_date);
    return deadlineDate >= today && deadlineDate < weekFromNow;
  });

  const next30DaysDeadlines = activeDeadlines.filter(d => {
    if (!d.deadline_date) return false;
    const deadlineDate = new Date(d.deadline_date);
    return deadlineDate >= weekFromNow && deadlineDate < monthFromNow;
  });

  const laterDeadlines = activeDeadlines.filter(d => {
    if (!d.deadline_date) return false;
    const deadlineDate = new Date(d.deadline_date);
    return deadlineDate >= monthFromNow;
  });

  return (
    <div className="h-full overflow-auto">
      {/* Trigger Alert Bar */}
      <TriggerAlertBar
        triggers={triggers}
        deadlines={deadlines}
        onAddTrigger={() => setAddTriggerModalOpen(true)}
        onEditTrigger={(trigger) => setEditingTrigger(trigger)}
      />

      <div className="max-w-5xl mx-auto p-8 space-y-6">
        {/* Case Header Card */}
        <div className="card">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <p className="text-sm font-mono text-blue-600 mb-2">{caseData.case_number}</p>
              <h1 className="text-2xl font-bold text-slate-900 mb-3">{caseData.title}</h1>
              <div className="flex flex-wrap gap-4 text-sm text-slate-600">
                {caseData.court && (
                  <div className="flex items-center gap-2">
                    <Building className="w-4 h-4 text-slate-400" />
                    <span>{caseData.court}</span>
                  </div>
                )}
                {caseData.judge && (
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-slate-400" />
                    <span>Judge {caseData.judge}</span>
                  </div>
                )}
                {caseData.jurisdiction && (
                  <span className="badge badge-standard capitalize">{caseData.jurisdiction}</span>
                )}
                {caseData.case_type && (
                  <span className="badge badge-info capitalize">{caseData.case_type}</span>
                )}
              </div>
            </div>
          </div>

          {/* Parties */}
          {caseData.parties && caseData.parties.length > 0 && (
            <div className="pt-4 border-t border-slate-200">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Parties</h3>
              <div className="grid grid-cols-2 gap-3">
                {caseData.parties.map((party, idx) => (
                  <div key={idx} className="text-sm">
                    <div className="text-xs text-slate-500 uppercase">{party.role}</div>
                    <div className="text-slate-900">{party.name}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className={`text-3xl font-bold mb-1 ${overdueCount > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {overdueCount}
            </div>
            <div className="text-sm text-slate-600">Overdue</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-amber-600 mb-1">{pendingCount}</div>
            <div className="text-sm text-slate-600">Pending</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600 mb-1">{triggers.length}</div>
            <div className="text-sm text-slate-600">Triggers</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600 mb-1">{documents.length}</div>
            <div className="text-sm text-slate-600">Documents</div>
          </div>
        </div>

        {/* Actions Row */}
        <div className="flex gap-2">
          <button
            onClick={() => setAddTriggerModalOpen(true)}
            className="btn-primary"
          >
            Add Trigger
          </button>
          <button
            onClick={() => setShowUploadDialog(true)}
            className="btn-secondary"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload Document
          </button>
          <button
            onClick={exportToCalendar}
            className="btn-ghost"
          >
            <Calendar className="w-4 h-4 mr-2" />
            Export Calendar
          </button>
        </div>

        {/* Deadlines Section - Grouped */}
        <div className="space-y-6">
          {/* This Week */}
          {thisWeekDeadlines.length > 0 && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-slate-900">This Week</h2>
                <span className="badge badge-important">{thisWeekDeadlines.length}</span>
              </div>
              <div className="space-y-3">
                {thisWeekDeadlines.map((deadline) => (
                  <div
                    key={deadline.id}
                    className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                    onClick={() => setViewingDeadline(deadline)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-medium text-slate-900">{deadline.title}</p>
                        <p className="text-sm text-slate-600 mt-1">
                          {formatDeadlineDate(deadline.deadline_date)}
                        </p>
                        {deadline.action_required && (
                          <p className="text-sm text-slate-500 mt-2">{deadline.action_required}</p>
                        )}
                      </div>
                      <span className={`badge ${
                        deadline.priority === 'fatal' ? 'badge-fatal' :
                        deadline.priority === 'critical' ? 'badge-critical' :
                        deadline.priority === 'important' ? 'badge-important' : 'badge-standard'
                      }`}>
                        {deadline.priority?.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Next 30 Days */}
          {next30DaysDeadlines.length > 0 && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-slate-900">Next 30 Days</h2>
                <span className="badge badge-standard">{next30DaysDeadlines.length}</span>
              </div>
              <div className="space-y-3">
                {next30DaysDeadlines.map((deadline) => (
                  <div
                    key={deadline.id}
                    className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                    onClick={() => setViewingDeadline(deadline)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-medium text-slate-900">{deadline.title}</p>
                        <p className="text-sm text-slate-600 mt-1">
                          {formatDeadlineDate(deadline.deadline_date)}
                        </p>
                      </div>
                      <span className={`badge ${
                        deadline.priority === 'fatal' ? 'badge-fatal' :
                        deadline.priority === 'critical' ? 'badge-critical' :
                        deadline.priority === 'important' ? 'badge-important' : 'badge-standard'
                      }`}>
                        {deadline.priority?.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Later */}
          {laterDeadlines.length > 0 && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-slate-900">Later</h2>
                <span className="badge badge-info">{laterDeadlines.length}</span>
              </div>
              <div className="space-y-3">
                {laterDeadlines.map((deadline) => (
                  <div
                    key={deadline.id}
                    className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                    onClick={() => setViewingDeadline(deadline)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-medium text-slate-900">{deadline.title}</p>
                        <p className="text-sm text-slate-600 mt-1">
                          {formatDeadlineDate(deadline.deadline_date)}
                        </p>
                      </div>
                      <span className={`badge ${
                        deadline.priority === 'fatal' ? 'badge-fatal' :
                        deadline.priority === 'critical' ? 'badge-critical' :
                        deadline.priority === 'important' ? 'badge-important' : 'badge-standard'
                      }`}>
                        {deadline.priority?.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Deadlines State */}
          {activeDeadlines.length === 0 && (
            <div className="card text-center py-16">
              <Clock className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-lg font-medium text-slate-900 mb-2">No Active Deadlines</p>
              <p className="text-sm text-slate-600 mb-6">Add a trigger to generate deadlines automatically</p>
              <button
                onClick={() => setAddTriggerModalOpen(true)}
                className="btn-primary"
              >
                Add Trigger
              </button>
            </div>
          )}
        </div>

        {/* Documents Section */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-600" />
              Documents
            </h2>
            <button
              onClick={() => setShowUploadDialog(true)}
              className="btn-secondary btn-sm"
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload
            </button>
          </div>

          {documents.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600 mb-4">No documents uploaded yet</p>
              <button
                onClick={() => setShowUploadDialog(true)}
                className="btn-secondary"
              >
                Upload your first document
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {documents.map(doc => (
                <div
                  key={doc.id}
                  className={`group relative border border-slate-200 rounded-lg p-4 transition-all ${
                    doc.storage_url
                      ? 'hover:border-blue-300 hover:shadow-md cursor-pointer'
                      : 'bg-slate-50'
                  }`}
                  onClick={() => doc.storage_url && handleDocumentClick(doc)}
                >
                  <div className="flex items-start gap-3">
                    <FileText className={`w-5 h-5 flex-shrink-0 ${doc.storage_url ? 'text-purple-600' : 'text-slate-400'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{doc.file_name}</p>
                      {doc.document_type && (
                        <span className="inline-block mt-1 text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                          {doc.document_type}
                        </span>
                      )}
                      {!doc.storage_url && (
                        <p className="text-xs text-red-600 mt-1">⚠ File unavailable</p>
                      )}
                      <p className="text-xs text-slate-500 mt-1">
                        {formatDateTime(doc.created_at)}
                      </p>
                    </div>
                    <button
                      onClick={(e) => handleDocumentDelete(doc, e)}
                      className="p-1.5 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition-all"
                      title="Delete document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Triggers Section */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-slate-900">Triggers</h2>
            <button
              onClick={() => setAddTriggerModalOpen(true)}
              className="btn-secondary btn-sm"
            >
              Add Trigger
            </button>
          </div>

          {triggers.length === 0 ? (
            <div className="text-center py-12">
              <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600">No triggers set</p>
            </div>
          ) : (
            <div className="space-y-2">
              {triggers.map(trigger => (
                <button
                  key={trigger.id}
                  onClick={() => setEditingTrigger(trigger)}
                  className="w-full border border-slate-200 rounded-lg p-4 text-left hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-slate-900">{trigger.title}</p>
                      <p className="text-sm text-slate-600 mt-1">
                        {trigger.trigger_date ? formatDeadlineDate(trigger.trigger_date) : 'No date'}
                      </p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-slate-400" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <TriggerModal
        isOpen={triggerModalOpen}
        onClose={() => setTriggerModalOpen(false)}
        caseId={caseId}
        jurisdiction={caseData?.jurisdiction || 'florida_state'}
        courtType={caseData?.case_type || 'civil'}
        onSuccess={handleTriggerSuccess}
      />

      {viewingDocument && (
        <DocumentViewerWrapper
          isOpen={true}
          onClose={() => setViewingDocument(null)}
          documentUrl={`/api/v1/documents/${viewingDocument.id}/download`}
          documentName={viewingDocument.file_name}
        />
      )}

      <EditTriggerModal
        isOpen={!!editingTrigger}
        trigger={editingTrigger}
        deadlines={deadlines}
        onClose={() => setEditingTrigger(null)}
        onSuccess={() => {
          refetch.deadlines();
          refetch.triggers();
          setEditingTrigger(null);
        }}
      />

      <AddTriggerModal
        isOpen={addTriggerModalOpen}
        caseId={caseId}
        jurisdiction={caseData?.jurisdiction || 'florida_state'}
        courtType={caseData?.case_type || 'civil'}
        onClose={() => setAddTriggerModalOpen(false)}
        onSuccess={() => {
          refetch.deadlines();
          refetch.triggers();
          refetch.caseSummary();
        }}
      />

      <DeadlineDetailModal
        isOpen={!!viewingDeadline}
        deadline={viewingDeadline}
        triggers={triggers}
        onClose={() => setViewingDeadline(null)}
        onUpdate={() => {
          refetch.deadlines();
          setViewingDeadline(null);
        }}
        onComplete={(id) => {
          handleComplete(id);
          setViewingDeadline(null);
        }}
        onDelete={(id) => {
          handleDelete(id);
          setViewingDeadline(null);
        }}
      />

      {viewingChainTrigger && (
        <DeadlineChainView
          trigger={viewingChainTrigger}
          deadlines={deadlines}
          onSelectDeadline={(deadline) => {
            setViewingChainTrigger(null);
            setViewingDeadline(deadline);
          }}
          onClose={() => setViewingChainTrigger(null)}
        />
      )}

      {/* Upload Dialog */}
      {showUploadDialog && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3 className="text-lg font-semibold text-slate-900">Upload Document</h3>
              <button
                onClick={() => setShowUploadDialog(false)}
                className="text-slate-400 hover:text-slate-600"
                disabled={uploading}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handleDocumentUpload(file);
                  }
                }}
                disabled={uploading}
                className="block w-full text-sm text-slate-600
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-medium
                  file:bg-blue-600 file:text-white
                  hover:file:bg-blue-700
                  file:cursor-pointer
                  cursor-pointer"
              />
              <p className="mt-3 text-sm text-slate-600">
                Upload a PDF document to attach to this case. The document will be analyzed for deadlines and case information.
              </p>
              {uploading && (
                <div className="mt-4 flex items-center justify-center gap-2 text-blue-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  <span className="text-sm">Uploading and analyzing...</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
