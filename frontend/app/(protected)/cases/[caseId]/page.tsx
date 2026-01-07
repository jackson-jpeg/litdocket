'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Scale, FileText, Calendar, MessageSquare, ArrowLeft, Loader2, Upload, Zap, Eye, Download, CheckSquare, Trash2, Edit3, Clock, X, Check } from 'lucide-react';
import Link from 'next/link';
import apiClient from '@/lib/api-client';
import { useCaseData, Trigger } from '@/hooks/useCaseData';
import { useToast } from '@/components/Toast';
import { validateChatMessage, validateBulkSelection } from '@/lib/validation';
import { formatDateTime } from '@/lib/formatters';
import DocumentViewerWrapper from '@/components/DocumentViewerWrapper';
import TriggerModal from './triggers/TriggerModal';
import BulkEditModal from './BulkEditModal';
import SnoozeModal from './SnoozeModal';
import DeadlineCard from './DeadlineCard';
import EnhancedChat from '@/components/EnhancedChat';
import CaseInsights from '@/components/CaseInsights';
import { DeadlineCardSkeleton, DocumentCardSkeleton, ChatSkeleton, CaseSummarySkeleton } from '@/components/Skeleton';
import { useCaseSync } from '@/hooks/useCaseSync';
import { deadlineEvents, uiEvents } from '@/lib/eventBus';
import type { Document, ChatMessage } from '@/types';

// New deadline components
import DeadlineListPanel from '@/components/cases/deadlines/DeadlineListPanel';
import TriggerEventsPanel from '@/components/cases/triggers/TriggerEventsPanel';
import EditTriggerModal from '@/components/cases/triggers/EditTriggerModal';
import AddTriggerModal from '@/components/cases/triggers/AddTriggerModal';

export default function CaseRoomPage() {
  const params = useParams();
  const caseId = params.caseId as string;
  const { caseData, documents, deadlines, triggers, caseSummary, loading, error, refetch, optimistic } = useCaseData(caseId);
  const { showSuccess, showError, showWarning } = useToast();

  // Setup case synchronization across all components
  const caseSync = useCaseSync({
    caseId,
    onDeadlinesUpdate: () => refetch.deadlines(),
    onDocumentsUpdate: () => refetch.documents(),
    onTriggersUpdate: () => refetch.triggers(),
    onCaseUpdate: () => refetch.caseSummary(),
    onInsightsUpdate: () => {
      // Insights will refresh automatically via its own component
    },
  });

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);

  // UI state
  const [triggerModalOpen, setTriggerModalOpen] = useState(false);
  const [addTriggerModalOpen, setAddTriggerModalOpen] = useState(false);
  const [editingTrigger, setEditingTrigger] = useState<Trigger | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const [mobileActiveTab, setMobileActiveTab] = useState<'documents' | 'deadlines' | 'chat'>('deadlines');
  const [useNewDeadlineUI, setUseNewDeadlineUI] = useState(true); // Feature flag for new UI

  // Deadline management state
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedDeadlines, setSelectedDeadlines] = useState<Set<string>>(new Set());
  const [bulkEditOpen, setBulkEditOpen] = useState(false);
  const [snoozeOpen, setSnoozeOpen] = useState(false);
  const [processingBulk, setProcessingBulk] = useState(false);
  const [showCompletedDeadlines, setShowCompletedDeadlines] = useState(false);

  useEffect(() => {
    fetchChatHistory();
  }, [caseId]);

  const fetchChatHistory = async () => {
    try {
      const response = await apiClient.get(`/api/v1/chat/case/${caseId}/history`);
      setChatMessages(response.data);
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  };

  const handleTriggerSuccess = () => {
    refetch.deadlines();
    refetch.triggers();
    refetch.caseSummary();
    showSuccess('Trigger created successfully');
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
      showSuccess('Calendar exported successfully');
    } catch (err) {
      showError('Failed to export calendar');
    }
  };

  const sendChatMessage = async () => {
    const validation = validateChatMessage(chatInput);
    if (!validation.isValid) {
      showWarning(validation.error || 'Invalid message');
      return;
    }

    const userMessage = chatInput.trim();
    setChatInput('');
    setSendingMessage(true);

    const tempUserMsg: ChatMessage = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setChatMessages(prev => [...prev, tempUserMsg]);

    try {
      const response = await apiClient.post('/api/v1/chat/message', {
        message: userMessage,
        case_id: caseId
      });

      const assistantMsg: ChatMessage = {
        id: response.data.message_id,
        role: 'assistant',
        content: response.data.response,
        created_at: new Date().toISOString(),
        context_rules: response.data.citations
      };

      setChatMessages(prev => [...prev, assistantMsg]);

      if (response.data.actions_taken && response.data.actions_taken.length > 0) {
        refetch.deadlines();
        refetch.caseSummary();
      }
    } catch (err: any) {
      showError('Failed to send message. Please try again.');
      const errorMsg: ChatMessage = {
        id: 'error-' + Date.now(),
        role: 'assistant',
        content: '❌ Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString()
      };
      setChatMessages(prev => [...prev, errorMsg]);
    } finally {
      setSendingMessage(false);
    }
  };

  // Deadline management functions
  const toggleDeadlineSelection = (id: string) => {
    const newSet = new Set(selectedDeadlines);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedDeadlines(newSet);
  };

  const selectAllDeadlines = () => {
    setSelectedDeadlines(new Set(deadlines.map(d => d.id)));
  };

  const clearDeadlineSelection = () => {
    setSelectedDeadlines(new Set());
    setSelectionMode(false);
  };

  const handleBulkComplete = async () => {
    const validation = validateBulkSelection(selectedDeadlines.size);
    if (!validation.isValid) {
      showWarning(validation.error || 'No deadlines selected');
      return;
    }

    setProcessingBulk(true);
    const count = selectedDeadlines.size;

    try {
      await Promise.all(
        Array.from(selectedDeadlines).map(id =>
          apiClient.patch(`/api/v1/deadlines/${id}/status?status=completed`)
        )
      );

      // Emit event for bulk update
      deadlineEvents.bulkUpdated(Array.from(selectedDeadlines));

      clearDeadlineSelection();
      uiEvents.showSuccess(`✅ ${count} deadline${count > 1 ? 's' : ''} marked as completed`);
    } catch (err) {
      uiEvents.showError('Failed to complete deadlines');
    } finally {
      setProcessingBulk(false);
    }
  };

  const handleBulkDelete = async () => {
    const validation = validateBulkSelection(selectedDeadlines.size);
    if (!validation.isValid) {
      showWarning(validation.error || 'No deadlines selected');
      return;
    }

    if (!confirm(`Delete ${selectedDeadlines.size} deadline(s)? This cannot be undone.`)) {
      return;
    }

    setProcessingBulk(true);
    const count = selectedDeadlines.size;

    try {
      await Promise.all(
        Array.from(selectedDeadlines).map(id =>
          apiClient.delete(`/api/v1/deadlines/${id}`)
        )
      );

      // Emit events for each deleted deadline
      Array.from(selectedDeadlines).forEach(id => {
        deadlineEvents.deleted(id);
      });

      clearDeadlineSelection();
      uiEvents.showSuccess(`🗑️ ${count} deadline${count > 1 ? 's' : ''} deleted`);
    } catch (err) {
      uiEvents.showError('Failed to delete deadlines');
    } finally {
      setProcessingBulk(false);
    }
  };

  const handleBulkEdit = async (priority: string, status: string) => {
    setProcessingBulk(true);
    try {
      await Promise.all(
        Array.from(selectedDeadlines).map(async (id) => {
          if (status) {
            await apiClient.patch(`/api/v1/deadlines/${id}/status?status=${status}`);
          }
        })
      );
      await refetch.deadlines();
      clearDeadlineSelection();
      showSuccess(`${selectedDeadlines.size} deadline(s) updated`);
    } catch (err) {
      throw err;
    } finally {
      setProcessingBulk(false);
    }
  };

  const handleSnooze = async (days: number, reason: string) => {
    // Note: Backend endpoint not fully implemented yet
    showWarning(
      `Snooze feature: Would push ${selectedDeadlines.size} deadline(s) forward by ${days} days. Backend endpoint pending.`
    );
    clearDeadlineSelection();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50">
        {/* Header Skeleton */}
        <div className="bg-white border-b border-slate-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="h-8 w-8 bg-gray-200 rounded animate-pulse" />
              <div className="h-6 w-48 bg-gray-200 rounded animate-pulse" />
            </div>
            <div className="h-4 w-64 bg-gray-200 rounded animate-pulse" />
          </div>
        </div>

        {/* Main Content Skeleton */}
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Panel A: Documents Skeleton */}
            <div className="lg:col-span-1 space-y-4">
              <CaseSummarySkeleton />
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="h-6 w-32 bg-gray-200 rounded animate-pulse mb-4" />
                <div className="space-y-3">
                  <DocumentCardSkeleton />
                  <DocumentCardSkeleton />
                  <DocumentCardSkeleton />
                </div>
              </div>
            </div>

            {/* Panel B: Deadlines Skeleton */}
            <div className="lg:col-span-1 space-y-4">
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="h-6 w-40 bg-gray-200 rounded animate-pulse mb-4" />
                <div className="space-y-3">
                  <DeadlineCardSkeleton />
                  <DeadlineCardSkeleton />
                  <DeadlineCardSkeleton />
                  <DeadlineCardSkeleton />
                </div>
              </div>
            </div>

            {/* Panel C: Chat Skeleton */}
            <div className="lg:col-span-1">
              <ChatSkeleton />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-red-50 border-2 border-red-200 rounded-xl p-8">
            <h2 className="text-xl font-bold text-red-900 mb-2">Error Loading Case</h2>
            <p className="text-red-700 mb-4">{error}</p>
            <Link href="/" className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              Return Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!caseData) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Scale className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-slate-800">LitDocket</h1>
                <p className="text-sm text-slate-600">{caseData.case_number}</p>
              </div>
            </div>
            <Link
              href="/"
              className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Home</span>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Case Info Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-8">
          <h2 className="text-2xl font-bold text-slate-800 mb-6">Case Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <label className="text-sm font-medium text-slate-500 uppercase tracking-wide">Case Number</label>
              <p className="text-lg font-semibold text-slate-900 mt-1">{caseData.case_number}</p>
            </div>

            {caseData.court && (
              <div>
                <label className="text-sm font-medium text-slate-500 uppercase tracking-wide">Court</label>
                <p className="text-lg text-slate-900 mt-1">{caseData.court}</p>
              </div>
            )}

            {caseData.judge && (
              <div>
                <label className="text-sm font-medium text-slate-500 uppercase tracking-wide">Judge</label>
                <p className="text-lg text-slate-900 mt-1">{caseData.judge}</p>
              </div>
            )}

            {caseData.case_type && (
              <div>
                <label className="text-sm font-medium text-slate-500 uppercase tracking-wide">Case Type</label>
                <p className="text-lg text-slate-900 mt-1 capitalize">{caseData.case_type}</p>
              </div>
            )}

            {caseData.jurisdiction && (
              <div>
                <label className="text-sm font-medium text-slate-500 uppercase tracking-wide">Jurisdiction</label>
                <p className="text-lg text-slate-900 mt-1 capitalize">{caseData.jurisdiction}</p>
              </div>
            )}

            {caseData.district && (
              <div>
                <label className="text-sm font-medium text-slate-500 uppercase tracking-wide">District</label>
                <p className="text-lg text-slate-900 mt-1">{caseData.district}</p>
              </div>
            )}
          </div>

          {caseData.title && caseData.title !== caseData.case_number && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <label className="text-sm font-medium text-slate-500 uppercase tracking-wide">Title</label>
              <p className="text-base text-slate-900 mt-1">{caseData.title}</p>
            </div>
          )}

          {caseData.parties && caseData.parties.length > 0 && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <label className="text-sm font-medium text-slate-500 uppercase tracking-wide mb-3 block">Parties</label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {caseData.parties.map((party, index) => (
                  <div key={index} className="bg-slate-50 rounded-lg p-3">
                    <span className="text-xs font-medium text-slate-600 uppercase tracking-wide">{party.role}</span>
                    <p className="text-sm text-slate-900 mt-1">{party.name}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Intelligent Case Insights */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-800 mb-4">Case Insights</h2>
          <CaseInsights caseId={caseId} />
        </div>

        {/* Case Summary (if available) */}
        {caseSummary && (
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl shadow-sm border-2 border-blue-200 p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-blue-900">Case Summary</h2>
              <span className="text-xs text-blue-600">
                Updated {formatDateTime(caseSummary.last_updated)}
              </span>
            </div>

            <div className="mb-6">
              <h3 className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Overview</h3>
              <p className="text-slate-700">{caseSummary.overview}</p>
            </div>

            <div className="mb-6">
              <h3 className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Current Status</h3>
              <p className="text-slate-700">{caseSummary.current_status}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {caseSummary.key_documents.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Key Documents</h3>
                  <ul className="space-y-1 text-sm text-slate-700">
                    {caseSummary.key_documents.map((doc, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-blue-600 mt-1">•</span>
                        <span>{doc}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {caseSummary.critical_deadlines.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Critical Deadlines</h3>
                  <ul className="space-y-1 text-sm text-slate-700">
                    {caseSummary.critical_deadlines.map((deadline, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-red-600 mt-1">⚠</span>
                        <span>{deadline}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {caseSummary.action_items.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Action Items</h3>
                  <ul className="space-y-1 text-sm text-slate-700">
                    {caseSummary.action_items.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-600 mt-1">✓</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {caseSummary.timeline.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Timeline</h3>
                  <ul className="space-y-1 text-sm text-slate-700">
                    {caseSummary.timeline.slice(0, 5).map((event, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-slate-400 mt-1">▸</span>
                        <span>{event}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Mobile Tab Navigation */}
        <div className="lg:hidden mb-4">
          <div className="bg-white rounded-lg border border-gray-200 p-1 flex gap-1">
            <button
              onClick={() => setMobileActiveTab('documents')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-colors ${
                mobileActiveTab === 'documents'
                  ? 'bg-blue-500 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Documents</span>
              <span className="text-xs opacity-75">({documents.length})</span>
            </button>
            <button
              onClick={() => setMobileActiveTab('deadlines')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-colors ${
                mobileActiveTab === 'deadlines'
                  ? 'bg-blue-500 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Calendar className="w-4 h-4" />
              <span>Deadlines</span>
              <span className="text-xs opacity-75">({deadlines.length})</span>
            </button>
            <button
              onClick={() => setMobileActiveTab('chat')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-colors ${
                mobileActiveTab === 'chat'
                  ? 'bg-blue-500 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Chat</span>
            </button>
          </div>
        </div>

        {/* 3-Panel Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Panel A: Documents */}
          <div className={`bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-1 ${
            mobileActiveTab !== 'documents' ? 'hidden lg:block' : ''
          }`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <FileText className="w-6 h-6 text-blue-600" />
                <h3 className="text-lg font-semibold text-slate-800">Documents</h3>
              </div>
              <span className="text-sm font-medium text-slate-500">{documents.length}</span>
            </div>

            {documents.length === 0 ? (
              <div className="text-center py-8">
                <Upload className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <p className="text-sm text-slate-500">No documents yet</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {documents.map((doc) => (
                  <div key={doc.id} className="border border-slate-200 rounded-lg p-4 hover:bg-slate-50 transition-colors group">
                    <div className="flex items-start gap-3">
                      <FileText className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-slate-900 truncate">{doc.file_name}</p>
                          <button
                            onClick={() => setViewingDocument(doc)}
                            className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <Eye className="w-3 h-3" />
                            View
                          </button>
                        </div>
                        {doc.document_type && (
                          <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded">
                            {doc.document_type}
                          </span>
                        )}
                        {doc.ai_summary && (
                          <p className="text-xs text-slate-600 mt-2 line-clamp-2">{doc.ai_summary}</p>
                        )}
                        <p className="text-xs text-slate-400 mt-2">
                          {formatDateTime(doc.created_at)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Panel B: Deadlines - New Enhanced UI */}
          <div className={`lg:col-span-1 space-y-4 ${
            mobileActiveTab !== 'deadlines' ? 'hidden lg:block' : ''
          }`}>
            {/* Trigger Events Panel */}
            <TriggerEventsPanel
              triggers={triggers}
              deadlines={deadlines}
              caseId={caseId}
              onAddTrigger={() => setAddTriggerModalOpen(true)}
              onEditTrigger={(trigger) => setEditingTrigger(trigger)}
              onRefresh={() => {
                refetch.deadlines();
                refetch.triggers();
              }}
            />

            {/* Enhanced Deadline List Panel */}
            <DeadlineListPanel
              deadlines={deadlines}
              triggers={triggers}
              caseId={caseId}
              onAddDeadline={() => setTriggerModalOpen(true)}
              onExportCalendar={exportToCalendar}
              onRefresh={() => {
                refetch.deadlines();
                refetch.triggers();
              }}
              onOptimisticUpdate={optimistic}
            />
          </div>

          {/* Panel C: Enhanced AI Chat */}
          <div className={`lg:col-span-1 ${
            mobileActiveTab !== 'chat' ? 'hidden lg:block' : ''
          }`} style={{ height: '650px' }}>
            <EnhancedChat
              caseId={caseId}
              caseNumber={caseData?.case_number}
              onActionTaken={() => {
                refetch.deadlines();
                refetch.triggers();
                refetch.caseSummary();
              }}
            />
          </div>
        </div>
      </main>

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

      <BulkEditModal
        isOpen={bulkEditOpen}
        onClose={() => setBulkEditOpen(false)}
        selectedCount={selectedDeadlines.size}
        onSave={handleBulkEdit}
      />

      <SnoozeModal
        isOpen={snoozeOpen}
        onClose={() => setSnoozeOpen(false)}
        selectedCount={selectedDeadlines.size}
        onSnooze={handleSnooze}
      />

      {/* Edit Trigger Modal */}
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

      {/* Add Trigger Modal - New CompuLaw-style */}
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
