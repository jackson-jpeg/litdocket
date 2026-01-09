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
import { useState, useEffect, useCallback } from 'react';
import { FileText, Upload, Eye, Download, Plus, RefreshCw, Calendar, X } from 'lucide-react';
import apiClient from '@/lib/api-client';
import { useCaseData, Trigger, Deadline } from '@/hooks/useCaseData';
import { useToast } from '@/components/Toast';
import { formatDateTime, formatDeadlineDate } from '@/lib/formatters';
import DocumentViewerWrapper from '@/components/DocumentViewerWrapper';
import TriggerModal from './triggers/TriggerModal';
import EditTriggerModal from '@/components/cases/triggers/EditTriggerModal';
import AddTriggerModal from '@/components/cases/triggers/AddTriggerModal';
import TriggerAlertBar from '@/components/cases/triggers/TriggerAlertBar';
import DeadlineTable from '@/components/cases/deadlines/DeadlineTable';
import { useCaseSync } from '@/hooks/useCaseSync';
import { deadlineEvents, useEventBus, FilterCommand } from '@/lib/eventBus';
import type { Document } from '@/types';

// Filter state type
interface FilterState {
  showFilter: 'all' | 'overdue' | 'pending' | 'completed' | null;
  priority: string | null;
  search: string | null;
}

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
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [rightPaneCollapsed, setRightPaneCollapsed] = useState(false);

  // Filter state (controlled by terminal commands)
  const [filters, setFilters] = useState<FilterState>({
    showFilter: null,
    priority: null,
    search: null,
  });

  // Listen for filter events from terminal
  const handleFilterApply = useCallback((filter: FilterCommand) => {
    if (filter.type === 'show') {
      setFilters(prev => ({ ...prev, showFilter: filter.value, priority: null }));
    } else if (filter.type === 'priority') {
      setFilters(prev => ({ ...prev, priority: filter.value, showFilter: null }));
    } else if (filter.type === 'search') {
      setFilters(prev => ({ ...prev, search: filter.value }));
    } else if (filter.type === 'clear') {
      setFilters({ showFilter: null, priority: null, search: null });
    }
  }, []);

  const handleFilterClear = useCallback(() => {
    setFilters({ showFilter: null, priority: null, search: null });
  }, []);

  // Subscribe to filter events
  useEventBus('filter:apply', handleFilterApply);
  useEventBus('filter:clear', handleFilterClear);

  // Check if any filter is active
  const hasActiveFilter = filters.showFilter || filters.priority || filters.search;

  // Handlers
  const handleTriggerSuccess = () => {
    refetch.deadlines();
    refetch.triggers();
    refetch.caseSummary();
    showSuccess('Trigger created successfully');
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
      await apiClient.patch(`/api/v1/deadlines/${id}`, { deadline_date: dateStr });
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

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
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

  // Apply filters and sort deadlines
  const filteredDeadlines = deadlines.filter(d => {
    // Show filter
    if (filters.showFilter === 'overdue') {
      const isActive = d.status !== 'completed' && d.status !== 'cancelled';
      const isOverdue = d.deadline_date && new Date(d.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));
      if (!isActive || !isOverdue) return false;
    } else if (filters.showFilter === 'pending') {
      if (d.status === 'completed' || d.status === 'cancelled') return false;
    } else if (filters.showFilter === 'completed') {
      if (d.status !== 'completed') return false;
    }

    // Priority filter
    if (filters.priority) {
      const priorityLower = filters.priority.toLowerCase();
      if (priorityLower === 'critical' || priorityLower === 'fatal') {
        if (d.priority !== 'critical' && d.priority !== 'fatal') return false;
      } else if (d.priority?.toLowerCase() !== priorityLower) {
        return false;
      }
    }

    // Search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      const matchesTitle = d.title?.toLowerCase().includes(searchLower);
      const matchesRule = d.applicable_rule?.toLowerCase().includes(searchLower);
      if (!matchesTitle && !matchesRule) return false;
    }

    return true;
  });

  const sortedDeadlines = [...filteredDeadlines].sort((a, b) => {
    if (!a.deadline_date) return 1;
    if (!b.deadline_date) return -1;
    return new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime();
  });

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

            {/* Stats */}
            <div className="panel mb-4">
              <div className="panel-header text-sm">Statistics</div>
              <div className="panel-body">
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className={`p-2 ${overdueCount > 0 ? 'bg-red-100' : 'bg-steel'}`}>
                    <div className={`text-lg font-mono font-bold ${overdueCount > 0 ? 'text-alert' : 'text-ink'}`}>
                      {overdueCount}
                    </div>
                    <div className="text-xxs text-ink-muted uppercase">Overdue</div>
                  </div>
                  <div className="p-2 bg-steel">
                    <div className="text-lg font-mono font-bold text-ink">{pendingCount}</div>
                    <div className="text-xxs text-ink-muted uppercase">Pending</div>
                  </div>
                  <div className="p-2 bg-steel">
                    <div className="text-lg font-mono font-bold text-ink">{triggers.length}</div>
                    <div className="text-xxs text-ink-muted uppercase">Triggers</div>
                  </div>
                  <div className="p-2 bg-steel">
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

        {/* CENTER PANE: Deadline Table */}
        <div className="flex-1 flex flex-col overflow-hidden bg-canvas">
          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 py-2 bg-steel border-b border-grid-line">
            <div className="flex items-center gap-2">
              <h2 className="font-serif font-bold">Deadlines</h2>
              <span className="badge badge-neutral">{sortedDeadlines.length}</span>
              {hasActiveFilter && (
                <>
                  <span className="text-ink-muted">/</span>
                  <span className="text-xs text-ink-muted">{deadlines.length} total</span>
                  <button
                    onClick={handleFilterClear}
                    className="badge badge-warning flex items-center gap-1"
                    title="Clear filter"
                  >
                    {filters.showFilter && `${filters.showFilter}`}
                    {filters.priority && `${filters.priority}`}
                    {filters.search && `"${filters.search}"`}
                    <X className="w-3 h-3" />
                  </button>
                </>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSelectionMode(!selectionMode)}
                className={`btn btn-secondary btn-raised text-xs ${selectionMode ? 'bg-navy text-white' : ''}`}
              >
                {selectionMode ? 'Cancel' : 'Select'}
              </button>
              <button
                onClick={() => setTriggerModalOpen(true)}
                className="btn btn-secondary btn-raised text-xs"
              >
                <Plus className="w-3 h-3 mr-1" />
                Add
              </button>
              <button
                onClick={exportToCalendar}
                className="btn btn-secondary btn-raised text-xs"
                title="Export to Calendar"
              >
                <Download className="w-3 h-3 mr-1" />
                iCal
              </button>
              <button
                onClick={() => refetch.deadlines()}
                className="btn btn-secondary btn-raised text-xs"
                title="Refresh"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto p-4">
            <DeadlineTable
              deadlines={sortedDeadlines}
              triggers={triggers}
              selectionMode={selectionMode}
              selectedIds={selectedIds}
              onToggleSelection={toggleSelection}
              onComplete={handleComplete}
              onDelete={handleDelete}
              onReschedule={handleReschedule}
            />
          </div>
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
                      <button
                        key={doc.id}
                        onClick={() => setViewingDocument(doc)}
                        className="w-full p-3 text-left hover:bg-canvas transition-colors group"
                      >
                        <div className="flex items-start gap-2">
                          <FileText className="w-4 h-4 text-navy flex-shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{doc.file_name}</p>
                            {doc.document_type && (
                              <span className="badge badge-info text-xxs mt-1">{doc.document_type}</span>
                            )}
                            <p className="text-xxs text-ink-muted mt-1">
                              {formatDateTime(doc.created_at)}
                            </p>
                          </div>
                          <Eye className="w-4 h-4 text-ink-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                      </button>
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
    </div>
  );
}
