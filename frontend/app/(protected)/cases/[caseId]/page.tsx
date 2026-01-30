'use client';

/**
 * Case Detail - Simplified with Unified Add Event
 *
 * Refactored to use:
 * - useCasePageModals hook for modal state management
 * - UnifiedAddEventModal for all event creation
 * - Removed separate Rules section (rules visible through chain badges on deadlines)
 */

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { FileText, Upload, Calendar, Clock, AlertTriangle, Building, User, Search, Sparkles, Trash2, Plus, ChevronDown, ChevronRight } from 'lucide-react';
import ChainBadge from '@/components/cases/deadlines/ChainBadge';
import CaseIntelligencePanel from '@/components/cases/CaseIntelligencePanel';
import DiscoveryTracker from '@/components/cases/DiscoveryTracker';
import BriefDraftingAssistant from '@/components/cases/BriefDraftingAssistant';
import CaseTimeline from '@/components/cases/CaseTimeline';
import SettlementCalculator from '@/components/cases/SettlementCalculator';
import apiClient from '@/lib/api-client';
import { useCaseData, Trigger, Deadline } from '@/hooks/useCaseData';
import { useToast } from '@/components/Toast';
import { formatDateTime, formatDeadlineDate } from '@/lib/formatters';
import DocumentViewerWrapper from '@/components/DocumentViewerWrapper';
import EditTriggerModal from '@/components/cases/triggers/EditTriggerModal';
import TriggerAlertBar from '@/components/cases/triggers/TriggerAlertBar';
import DeadlineDetailModal from '@/components/cases/deadlines/DeadlineDetailModal';
import DeadlineChainView from '@/components/cases/deadlines/DeadlineChainView';
import UnifiedAddEventModal from '@/components/cases/UnifiedAddEventModal';
import CaseInsights from '@/components/CaseInsights';
import { useCaseSync } from '@/hooks/useCaseSync';
import { useRAG } from '@/hooks/useRAG';
import { deadlineEvents } from '@/lib/eventBus';
import {
  useCasePageModals,
  getViewingDeadline,
  getViewingChainTrigger,
  getEditingTrigger,
  getViewingDocument,
  getAddEventTab,
} from '@/hooks/useCasePageModals';
import { useTrackCaseView } from '@/hooks/useRecentItems';
import { ContextualToolCard } from '@/components/ContextualToolCard';
import type { Document } from '@/types';

export default function CaseRoomPage() {
  const params = useParams();
  const caseId = params.caseId as string;
  const { caseData, documents, deadlines, triggers, loading, error, refetch, optimistic } = useCaseData(caseId);
  const { showSuccess, showError } = useToast();

  // Modal state management
  const modals = useCasePageModals();

  // Setup case synchronization
  useCaseSync({
    caseId,
    onDeadlinesUpdate: () => refetch.deadlines(),
    onDocumentsUpdate: () => refetch.documents(),
    onTriggersUpdate: () => refetch.triggers(),
    onCaseUpdate: () => refetch.caseSummary(),
    onInsightsUpdate: () => {},
  });

  // Track this case as recently viewed
  useTrackCaseView(caseData ? {
    id: caseData.id,
    case_number: caseData.case_number,
    title: caseData.title,
  } : null);

  // Document upload state
  const [uploading, setUploading] = useState(false);

  // Document search state
  const [documentSearchQuery, setDocumentSearchQuery] = useState('');
  const [smartSearchEnabled, setSmartSearchEnabled] = useState(false);
  const [searchResults, setSearchResults] = useState<Array<{ document_id: string; similarity: number }> | null>(null);

  // RAG (semantic search) hook
  const { search: ragSearch, loading: ragLoading } = useRAG({
    caseId,
    onError: (err) => showError(err.message),
  });

  // Handlers
  const handleTriggerSuccess = () => {
    refetch.deadlines();
    refetch.triggers();
    refetch.caseSummary();
    showSuccess('Rule applied successfully');
  };

  const handleDocumentClick = (doc: Document) => {
    if (!doc.storage_url) {
      showError('This document cannot be opened. The file may not be available on the server.');
      return;
    }
    modals.viewDocument(doc);
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
    } catch (err: unknown) {
      refetch.documents();
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) {
        showError('Document not found. It may have already been deleted.');
      } else if (status === 403) {
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

      modals.close();
      showSuccess(`Document uploaded. ${response.data.deadlines_extracted || 0} deadline(s) extracted.`);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      showError(detail || 'Failed to upload document');
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

  const handleDocumentSearch = async () => {
    if (!documentSearchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    if (smartSearchEnabled) {
      const results = await ragSearch(documentSearchQuery, 10);
      if (results) {
        setSearchResults(results.results || []);
      }
    } else {
      const filtered = documents.filter(doc =>
        doc.file_name.toLowerCase().includes(documentSearchQuery.toLowerCase()) ||
        doc.document_type?.toLowerCase().includes(documentSearchQuery.toLowerCase())
      );
      setSearchResults(filtered.map(doc => ({ document_id: doc.id, similarity: 1 })));
    }
  };

  const clearDocumentSearch = () => {
    setDocumentSearchQuery('');
    setSearchResults(null);
  };

  // Find trigger by ID for chain view
  const findTriggerById = (triggerId: string): Trigger | undefined => {
    return triggers.find(t => t.id === triggerId);
  };

  // Find trigger for a deadline (by trigger_event → trigger_type match)
  const findTriggerForDeadline = (deadline: Deadline): Trigger | undefined => {
    if (!deadline.trigger_event) return undefined;
    return triggers.find(t => t.trigger_type === deadline.trigger_event);
  };

  // Insights collapsed state
  const [insightsCollapsed, setInsightsCollapsed] = useState(true);

  // Get documents to display (filtered or all)
  const displayedDocuments = searchResults
    ? documents.filter(doc => searchResults.some(r => r.document_id === doc.id))
    : documents;

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

  // Extract data from modal state for rendering
  const viewingDeadline = getViewingDeadline(modals.modal);
  const viewingChainTrigger = getViewingChainTrigger(modals.modal);
  const editingTrigger = getEditingTrigger(modals.modal);
  const viewingDocument = getViewingDocument(modals.modal);
  const addEventTab = getAddEventTab(modals.modal);

  return (
    <div className="h-full overflow-auto">
      {/* Rule Alert Bar */}
      <TriggerAlertBar
        triggers={triggers}
        deadlines={deadlines}
        onEditTrigger={(trigger) => modals.editTrigger(trigger)}
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

        {/* AI Case Intelligence Panel */}
        <CaseIntelligencePanel
          caseId={caseId}
          judgeName={caseData.judge}
        />

        {/* Actions Row - Single Add Event button */}
        <div className="flex gap-2">
          <button
            onClick={() => modals.openAddEvent()}
            className="btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Event
          </button>
          <button
            onClick={() => modals.openUploadDocument()}
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
                {thisWeekDeadlines.map((deadline) => {
                  const parentTrigger = findTriggerForDeadline(deadline);
                  return (
                    <div
                      key={deadline.id}
                      className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                      onClick={() => modals.viewDeadline(deadline)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-medium text-slate-900">{deadline.title}</p>
                            {parentTrigger && (
                              <ChainBadge
                                trigger={parentTrigger}
                                deadlines={deadlines}
                                compact
                                onViewChain={(e) => {
                                  e?.stopPropagation();
                                  modals.viewChain(parentTrigger);
                                }}
                              />
                            )}
                          </div>
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
                  );
                })}
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
                {next30DaysDeadlines.map((deadline) => {
                  const parentTrigger = findTriggerForDeadline(deadline);
                  return (
                    <div
                      key={deadline.id}
                      className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                      onClick={() => modals.viewDeadline(deadline)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-medium text-slate-900">{deadline.title}</p>
                            {parentTrigger && (
                              <ChainBadge
                                trigger={parentTrigger}
                                deadlines={deadlines}
                                compact
                                onViewChain={(e) => {
                                  e?.stopPropagation();
                                  modals.viewChain(parentTrigger);
                                }}
                              />
                            )}
                          </div>
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
                  );
                })}
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
                {laterDeadlines.map((deadline) => {
                  const parentTrigger = findTriggerForDeadline(deadline);
                  return (
                    <div
                      key={deadline.id}
                      className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                      onClick={() => modals.viewDeadline(deadline)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-medium text-slate-900">{deadline.title}</p>
                            {parentTrigger && (
                              <ChainBadge
                                trigger={parentTrigger}
                                deadlines={deadlines}
                                compact
                                onViewChain={(e) => {
                                  e?.stopPropagation();
                                  modals.viewChain(parentTrigger);
                                }}
                              />
                            )}
                          </div>
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
                  );
                })}
              </div>
            </div>
          )}

          {/* No Deadlines State */}
          {activeDeadlines.length === 0 && (
            <div className="card text-center py-16">
              <Clock className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-lg font-medium text-slate-900 mb-2">No Active Deadlines</p>
              <p className="text-sm text-slate-600 mb-6">Add an event to create deadlines</p>
              <div className="flex flex-col items-center gap-4">
                <button
                  onClick={() => modals.openAddEvent('trigger')}
                  className="btn-primary"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Event
                </button>
                <div className="text-xs text-slate-500">or</div>
                <ContextualToolCard
                  toolId="calculator"
                  title="Calculate Deadlines"
                  description="Use the standalone calculator for quick calculations"
                  size="compact"
                  queryParams={caseData?.jurisdiction ? { jurisdiction: caseData.jurisdiction } : undefined}
                  className="max-w-sm"
                />
              </div>
            </div>
          )}
        </div>

        {/* AI Insights - Collapsed by default */}
        <div className="card">
          <button
            onClick={() => setInsightsCollapsed(!insightsCollapsed)}
            className="flex items-center justify-between w-full text-left"
          >
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              AI Insights
            </h2>
            {insightsCollapsed ? (
              <ChevronRight className="w-5 h-5 text-slate-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400" />
            )}
          </button>
          {!insightsCollapsed && (
            <div className="mt-4 pt-4 border-t border-slate-200">
              <CaseInsights caseId={caseId} />
            </div>
          )}
        </div>

        {/* Case Timeline */}
        <CaseTimeline caseId={caseId} className="card" />

        {/* Discovery Tracker */}
        <DiscoveryTracker caseId={caseId} />

        {/* Brief Drafting Assistant */}
        <BriefDraftingAssistant
          caseId={caseId}
          caseTitle={caseData.title}
          jurisdiction={caseData.jurisdiction}
        />

        {/* Settlement Calculator */}
        <SettlementCalculator
          caseId={caseId}
          caseType={caseData.case_type}
          jurisdiction={caseData.jurisdiction}
        />

        {/* Documents Section */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-600" />
              Documents
              {searchResults && (
                <span className="text-sm font-normal text-slate-500">
                  ({searchResults.length} result{searchResults.length !== 1 ? 's' : ''})
                </span>
              )}
            </h2>
            <button
              onClick={() => modals.openUploadDocument()}
              className="btn-secondary btn-sm"
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload
            </button>
          </div>

          {/* Document Search Bar */}
          {documents.length > 0 && (
            <div className="mb-4">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={documentSearchQuery}
                    onChange={(e) => setDocumentSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleDocumentSearch()}
                    placeholder={smartSearchEnabled ? "Search document content with AI..." : "Filter by filename..."}
                    className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <button
                  onClick={handleDocumentSearch}
                  disabled={ragLoading}
                  className="btn-primary btn-sm"
                >
                  {ragLoading ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    'Search'
                  )}
                </button>
                {searchResults && (
                  <button
                    onClick={clearDocumentSearch}
                    className="btn-ghost btn-sm"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={() => setSmartSearchEnabled(!smartSearchEnabled)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    smartSearchEnabled
                      ? 'bg-purple-100 text-purple-700 border border-purple-300'
                      : 'bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200'
                  }`}
                >
                  <Sparkles className={`w-3.5 h-3.5 ${smartSearchEnabled ? 'text-purple-600' : 'text-slate-400'}`} />
                  Smart Search
                </button>
                {smartSearchEnabled && (
                  <span className="text-xs text-slate-500">
                    AI-powered semantic search across document content
                  </span>
                )}
              </div>
            </div>
          )}

          {documents.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600 mb-4">No documents uploaded yet</p>
              <button
                onClick={() => modals.openUploadDocument()}
                className="btn-secondary"
              >
                Upload your first document
              </button>
            </div>
          ) : displayedDocuments.length === 0 ? (
            <div className="text-center py-8">
              <Search className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600 mb-2">No documents match your search</p>
              <button
                onClick={clearDocumentSearch}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Clear search
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {displayedDocuments.map(doc => {
                const searchResult = searchResults?.find(r => r.document_id === doc.id);
                const relevanceScore = searchResult?.similarity;

                return (
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
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          {doc.document_type && (
                            <span className="inline-block text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                              {doc.document_type}
                            </span>
                          )}
                          {smartSearchEnabled && relevanceScore !== undefined && relevanceScore < 1 && (
                            <span
                              className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded ${
                                relevanceScore >= 0.8
                                  ? 'bg-green-100 text-green-700'
                                  : relevanceScore >= 0.6
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-slate-100 text-slate-600'
                              }`}
                              title="Semantic relevance score"
                            >
                              <Sparkles className="w-3 h-3" />
                              {Math.round(relevanceScore * 100)}% match
                            </span>
                          )}
                        </div>
                        {!doc.storage_url && (
                          <p className="text-xs text-red-600 mt-1">File unavailable</p>
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
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <UnifiedAddEventModal
        isOpen={modals.isAddEventOpen}
        caseId={caseId}
        jurisdiction={caseData?.jurisdiction || 'florida_state'}
        courtType={caseData?.case_type || 'civil'}
        onClose={modals.close}
        onSuccess={() => {
          refetch.deadlines();
          refetch.triggers();
          refetch.caseSummary();
        }}
        initialTab={addEventTab || 'quick'}
      />

      {viewingDocument && (
        <DocumentViewerWrapper
          isOpen={true}
          onClose={modals.close}
          documentUrl={`/api/v1/documents/${viewingDocument.id}/download`}
          documentName={viewingDocument.file_name}
        />
      )}

      <EditTriggerModal
        isOpen={!!editingTrigger}
        trigger={editingTrigger}
        deadlines={deadlines}
        onClose={modals.close}
        onSuccess={() => {
          refetch.deadlines();
          refetch.triggers();
          modals.close();
        }}
      />

      <DeadlineDetailModal
        isOpen={!!viewingDeadline}
        deadline={viewingDeadline}
        triggers={triggers}
        onClose={modals.close}
        onUpdate={() => {
          refetch.deadlines();
          modals.close();
        }}
        onComplete={(id) => {
          handleComplete(id);
          modals.close();
        }}
        onDelete={(id) => {
          handleDelete(id);
          modals.close();
        }}
      />

      {viewingChainTrigger && (
        <DeadlineChainView
          trigger={viewingChainTrigger}
          deadlines={deadlines}
          onSelectDeadline={(deadline) => {
            modals.viewDeadline(deadline);
          }}
          onClose={modals.close}
        />
      )}

      {/* Upload Dialog */}
      {modals.isUploadDocumentOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3 className="text-lg font-semibold text-slate-900">Upload Document</h3>
              <button
                onClick={modals.close}
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
