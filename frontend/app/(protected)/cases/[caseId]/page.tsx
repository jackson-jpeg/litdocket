'use client';

/**
 * Case Room - Sovereign Design System
 *
 * 3-Pane Cockpit Layout:
 * - Left Pane (20%): Case Metadata
 * - Center Pane (60%): Master Data Grid (DeadlineTable)
 * - Right Pane (20%): Documents
 *
 * "Density is Reliability"
 */

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { FileText, Upload, Eye, Trash2 } from 'lucide-react';
import apiClient from '@/lib/api-client';
import { useCaseData, Trigger, Deadline } from '@/hooks/useCaseData';
import { useToast } from '@/components/Toast';
import { formatDateTime, formatDeadlineDate } from '@/lib/formatters';
import DocumentViewerWrapper from '@/components/DocumentViewerWrapper';
import TriggerModal from './triggers/TriggerModal';
import EditTriggerModal from '@/components/cases/triggers/EditTriggerModal';
import AddTriggerModal from '@/components/cases/triggers/AddTriggerModal';
import TriggerAlertBar from '@/components/cases/triggers/TriggerAlertBar';
import DeadlineListPanel from '@/components/cases/deadlines/DeadlineListPanel';
import DeadlineDetailModal from '@/components/cases/deadlines/DeadlineDetailModal';
import DeadlineChainView from '@/components/cases/deadlines/DeadlineChainView';
import { useCaseSync } from '@/hooks/useCaseSync';
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
  const [rightPaneCollapsed, setRightPaneCollapsed] = useState(false);

  // Legacy filter support - Terminal commands (kept for backwards compatibility)
  // The DeadlineListPanel now has its own comprehensive filtering

  // Handlers
  const handleTriggerSuccess = () => {
    refetch.deadlines();
    refetch.triggers();
    refetch.caseSummary();
    showSuccess('Trigger created successfully');
  };

  const handleDocumentClick = (doc: Document) => {
    console.log('[CaseRoom] Document clicked:', {
      id: doc.id,
      file_name: doc.file_name,
      storage_url: doc.storage_url,
      document_type: doc.document_type
    });

    if (!doc.storage_url) {
      console.error('[CaseRoom] Document has no storage_url:', doc);
      showError('This document cannot be opened. The file may not be available on the server.');
      return;
    }

    // Set the viewing document - this will open the viewer
    setViewingDocument(doc);
  };

  const handleDocumentDelete = async (doc: Document, e: React.MouseEvent) => {
    // Prevent triggering parent onClick (document view)
    e.stopPropagation();

    // Confirm deletion
    if (!confirm(`Delete "${doc.file_name}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    console.log('[CaseRoom] Deleting document:', {
      id: doc.id,
      file_name: doc.file_name,
      storage_url: doc.storage_url
    });

    try {
      // Optimistic update - remove from UI immediately
      optimistic.removeDocument(doc.id);

      // Call API
      await apiClient.delete(`/api/v1/documents/${doc.id}`);

      console.log('[CaseRoom] Document deleted successfully:', doc.id);
      showSuccess('Document deleted');

      // Refresh documents list (in case optimistic update missed something)
      refetch.documents();
    } catch (err: any) {
      console.error('[CaseRoom] Failed to delete document:', err);

      // Revert optimistic update by refetching
      refetch.documents();

      // User-friendly error messages
      if (err.response?.status === 404) {
        // Ghost document - already deleted or never existed
        showError('Document not found. It may have already been deleted.');
      } else if (err.response?.status === 403) {
        showError('You do not have permission to delete this document.');
      } else {
        showError('Failed to delete document. Please try again.');
      }
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

  const handleReschedule = async (id: string, newDate: Date) => {
    try {
      const dateStr = newDate.toISOString().split('T')[0];
      optimistic.updateDeadlineDate(id, dateStr);
      // Use correct reschedule endpoint with proper schema
      await apiClient.patch(`/api/v1/deadlines/${id}/reschedule`, {
        new_date: dateStr,
        reason: 'Rescheduled via calendar'
      });
      deadlineEvents.updated({ id, deadline_date: dateStr });
      showSuccess('Deadline rescheduled');
    } catch (err) {
      refetch.deadlines();
      showError('Failed to reschedule deadline');
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
          <div className="w-8 h-8 border-2 border-navy border-t-transparent animate-spin mx-auto mb-4" />
          <p className="text-ink-secondary font-mono text-sm">LOADING CASE DATA...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="panel panel-raised p-8 max-w-md text-center">
          <div className="text-alert text-4xl mb-4">!</div>
          <h2 className="font-serif text-xl mb-2">Error Loading Case</h2>
          <p className="text-ink-secondary mb-4">{error}</p>
          <button onClick={() => window.location.reload()} className="btn btn-primary btn-raised">
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

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Trigger Alert Bar */}
      <TriggerAlertBar
        triggers={triggers}
        deadlines={deadlines}
        onAddTrigger={() => setAddTriggerModalOpen(true)}
        onEditTrigger={(trigger) => setEditingTrigger(trigger)}
      />

      {/* 3-Pane Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANE: Case Metadata */}
        <div className="w-64 flex-shrink-0 border-r border-grid-line bg-steel overflow-y-auto">
          <div className="p-4">
            {/* Case Number Header */}
            <div className="panel panel-raised mb-4">
              <div className="panel-header">
                <span className="font-mono text-sm">{caseData.case_number}</span>
              </div>
              <div className="panel-body space-y-2">
                {caseData.court && (
                  <div>
                    <label className="text-xxs text-ink-muted uppercase tracking-wide">Court</label>
                    <p className="text-sm">{caseData.court}</p>
                  </div>
                )}
                {caseData.judge && (
                  <div>
                    <label className="text-xxs text-ink-muted uppercase tracking-wide">Judge</label>
                    <p className="text-sm">{caseData.judge}</p>
                  </div>
                )}
                {caseData.case_type && (
                  <div>
                    <label className="text-xxs text-ink-muted uppercase tracking-wide">Type</label>
                    <p className="text-sm capitalize">{caseData.case_type}</p>
                  </div>
                )}
                {caseData.jurisdiction && (
                  <div>
                    <label className="text-xxs text-ink-muted uppercase tracking-wide">Jurisdiction</label>
                    <p className="text-sm capitalize">{caseData.jurisdiction}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Stats - Sovereign Design with border accents */}
            <div className="panel mb-4">
              <div className="panel-header text-sm">Statistics</div>
              <div className="panel-body">
                <div className="grid grid-cols-2 gap-2 text-center">
                  {/* Overdue - Red left border */}
                  <div className={`p-2 bg-white border border-gray-200 ${overdueCount > 0 ? 'border-l-4 border-l-red-600' : 'border-l-4 border-l-gray-300'}`}>
                    <div className={`text-lg font-mono font-bold ${overdueCount > 0 ? 'text-red-600' : 'text-ink'}`}>
                      {overdueCount}
                    </div>
                    <div className="text-xxs text-ink-muted uppercase">Overdue</div>
                  </div>
                  {/* Pending - Gray left border */}
                  <div className="p-2 bg-white border border-gray-200 border-l-4 border-l-gray-600">
                    <div className="text-lg font-mono font-bold text-ink">{pendingCount}</div>
                    <div className="text-xxs text-ink-muted uppercase">Pending</div>
                  </div>
                  {/* Triggers - Navy left border */}
                  <div className="p-2 bg-white border border-gray-200 border-l-4 border-l-navy">
                    <div className="text-lg font-mono font-bold text-ink">{triggers.length}</div>
                    <div className="text-xxs text-ink-muted uppercase">Triggers</div>
                  </div>
                  {/* Documents - Gray left border */}
                  <div className="p-2 bg-white border border-gray-200 border-l-4 border-l-gray-400">
                    <div className="text-lg font-mono font-bold text-ink">{documents.length}</div>
                    <div className="text-xxs text-ink-muted uppercase">Documents</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Triggers List */}
            <div className="panel">
              <div className="panel-header text-sm flex items-center justify-between">
                <span>Triggers</span>
                <button
                  onClick={() => setAddTriggerModalOpen(true)}
                  className="text-xs text-navy hover:underline"
                >
                  + Add
                </button>
              </div>
              <div className="divide-y divide-grid-line">
                {triggers.length === 0 ? (
                  <div className="p-3 text-center text-ink-muted text-xs">No triggers</div>
                ) : (
                  triggers.map(trigger => (
                    <button
                      key={trigger.id}
                      onClick={() => setEditingTrigger(trigger)}
                      className="w-full p-2 text-left hover:bg-canvas transition-colors"
                    >
                      <div className="text-sm font-medium truncate">{trigger.title}</div>
                      <div className="text-xs text-ink-muted font-mono">
                        {trigger.trigger_date ? formatDeadlineDate(trigger.trigger_date) : 'No date'}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Parties */}
            {caseData.parties && caseData.parties.length > 0 && (
              <div className="panel mt-4">
                <div className="panel-header text-sm">Parties</div>
                <div className="divide-y divide-grid-line">
                  {caseData.parties.map((party, idx) => (
                    <div key={idx} className="p-2">
                      <div className="text-xxs text-ink-muted uppercase">{party.role}</div>
                      <div className="text-sm truncate">{party.name}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* CENTER PANE: Deadline List Panel */}
        <div className="flex-1 flex flex-col overflow-hidden bg-canvas p-4">
          <DeadlineListPanel
            deadlines={deadlines}
            triggers={triggers}
            caseId={caseId}
            onAddDeadline={() => setTriggerModalOpen(true)}
            onExportCalendar={exportToCalendar}
            onRefresh={() => refetch.deadlines()}
            onOptimisticUpdate={{
              updateDeadlineStatus: optimistic.updateDeadlineStatus,
              removeDeadline: optimistic.removeDeadline,
              updateDeadlineDate: optimistic.updateDeadlineDate,
            }}
          />
        </div>

        {/* RIGHT PANE: Documents */}
        <div className={`${rightPaneCollapsed ? 'w-8' : 'w-72'} flex-shrink-0 border-l border-grid-line bg-steel overflow-hidden transition-all`}>
          {rightPaneCollapsed ? (
            <button
              onClick={() => setRightPaneCollapsed(false)}
              className="w-full h-full flex items-center justify-center text-ink-muted hover:bg-canvas"
              title="Expand Documents"
            >
              <FileText className="w-4 h-4" />
            </button>
          ) : (
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between px-3 py-2 border-b border-grid-line bg-grid-header">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-ink-secondary" />
                  <span className="font-serif font-bold text-sm">Documents</span>
                  <span className="badge badge-neutral text-xs">{documents.length}</span>
                </div>
                <button
                  onClick={() => setRightPaneCollapsed(true)}
                  className="text-ink-muted hover:text-ink text-xs"
                >
                  ✕
                </button>
              </div>
              <div className="flex-1 overflow-y-auto">
                {documents.length === 0 ? (
                  <div className="p-4 text-center">
                    <Upload className="w-8 h-8 text-ink-muted mx-auto mb-2" />
                    <p className="text-xs text-ink-muted">No documents</p>
                  </div>
                ) : (
                  <div className="divide-y divide-grid-line">
                    {documents.map(doc => (
                      <div
                        key={doc.id}
                        className={`group relative transition-colors ${
                          doc.storage_url
                            ? 'hover:bg-canvas'
                            : 'bg-canvas/50'
                        }`}
                      >
                        <button
                          onClick={() => handleDocumentClick(doc)}
                          className="w-full p-3 text-left flex items-start gap-2"
                          disabled={!doc.storage_url}
                          title={!doc.storage_url ? 'This document is not available for viewing' : 'Click to view document'}
                        >
                          <FileText className={`w-4 h-4 flex-shrink-0 mt-0.5 ${doc.storage_url ? 'text-navy' : 'text-ink-muted'}`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{doc.file_name}</p>
                            {doc.document_type && (
                              <span className="badge badge-info text-xxs mt-1">{doc.document_type}</span>
                            )}
                            {!doc.storage_url && (
                              <p className="text-xxs text-red-600 mt-1">⚠ File unavailable</p>
                            )}
                            <p className="text-xxs text-ink-muted mt-1">
                              {formatDateTime(doc.created_at)}
                            </p>
                          </div>
                          {doc.storage_url && (
                            <Eye className="w-4 h-4 text-ink-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                          )}
                        </button>

                        {/* Delete Button - Always visible for ghost documents */}
                        <button
                          onClick={(e) => handleDocumentDelete(doc, e)}
                          className={`absolute right-2 top-3 p-1.5 rounded transition-all ${
                            doc.storage_url
                              ? 'opacity-0 group-hover:opacity-100 hover:bg-red-100 text-ink-muted hover:text-red-600'
                              : 'opacity-100 hover:bg-red-100 text-red-600'
                          }`}
                          title="Delete document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
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

      {viewingDocument && viewingDocument.storage_url && (
        <DocumentViewerWrapper
          isOpen={true}
          onClose={() => setViewingDocument(null)}
          documentUrl={viewingDocument.storage_url}
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
    </div>
  );
}
