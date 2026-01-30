'use client';

/**
 * AI Command Bar - Paper & Steel Design
 *
 * Floating command bar (⌘K) that opens a centered modal overlay
 * Clean white interface with professional chat bubbles
 * No fixed terminal - appears on demand
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import apiClient from '@/lib/api-client';
import { deadlineEvents, filterEvents, eventBus, caseEvents } from '@/lib/eventBus';
import { useStreamingChat } from '@/hooks/useStreamingChat';
import { ProposalCard, StreamingIndicator } from '@/components/chat/ProposalCard';
import {
  Paperclip,
  X,
  FileText,
  Upload,
  AlertTriangle,
  CheckCircle,
  Clock,
  ExternalLink,
  Loader2,
  MessageSquare,
  Command,
} from 'lucide-react';

interface Message {
  id: string;
  type: 'user' | 'system' | 'ai' | 'error' | 'action' | 'docket';
  content: string;
  timestamp: Date;
  actions?: ActionTaken[];
  citations?: string[];
  docketCard?: DocketCardData;
}

interface ActionTaken {
  tool: string;
  input: any;
  result: any;
}

interface DocketCardData {
  filename: string;
  documentType?: string;
  deadlinesExtracted: number;
  fatalCount: number;
  criticalCount: number;
  documentId: string;
  caseId: string;
  extractionMethod: string;
}

// Extract case ID from URL path
function useCaseContext(): { caseId: string | null; casePath: string | null } {
  const pathname = usePathname();
  const match = pathname?.match(/\/cases\/([a-zA-Z0-9-]+)/);
  return {
    caseId: match ? match[1] : null,
    casePath: match ? pathname : null,
  };
}

export function AITerminal() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [hasHistory, setHasHistory] = useState(false);

  // File upload state
  const [stagedFile, setStagedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { caseId, casePath } = useCaseContext();

  // Quick View case selection (overrides URL-based context)
  const [quickViewCaseId, setQuickViewCaseId] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = eventBus.on('case:selected', (data: { id: string | null }) => {
      setQuickViewCaseId(data?.id || null);
    });
    return unsubscribe;
  }, []);

  // Priority: Quick View selection > URL-based detection
  const activeCaseId = quickViewCaseId || caseId;

  // Streaming state
  const [currentAIMessageId, setCurrentAIMessageId] = useState<string | null>(null);

  // Initialize streaming chat hook
  const {
    streamState,
    currentMessage,
    sendMessage,
    approveToolUse,
    rejectToolUse,
    cancelStream,
    isStreaming,
    isAwaitingApproval,
    hasError
  } = useStreamingChat({
    caseId: activeCaseId || '',
    onToken: (token: string) => {
      // Tokens are accumulated in currentMessage state by the hook
    },
    onStatus: (_status: string, _message: string) => {
      // Status updates handled silently
    },
    onToolUse: (_toolCall: any) => {
      // Tool use handled silently
    },
    onToolResult: (_toolId: string, _result: any) => {
      // Tool result handled silently
    },
    onError: (error: string, code?: string) => {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        type: 'error',
        content: error,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
      setCurrentAIMessageId(null);
    },
    onDone: (_data: { message_id: string; tokens_used: number }) => {
      // Add complete AI message to messages array
      if (currentMessage.trim()) {
        const aiMsg: Message = {
          id: `ai-${Date.now()}`,
          type: 'ai',
          content: currentMessage,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, aiMsg]);
      } else {
        // Handle empty response - provide user feedback
        const emptyMsg: Message = {
          id: `system-${Date.now()}`,
          type: 'system',
          content: 'No response generated. Try rephrasing your question or providing more context.',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, emptyMsg]);
      }

      setCurrentAIMessageId(null);
    }
  });

  // Keyboard shortcut (⌘K or Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Load chat history when modal opens with case context
  useEffect(() => {
    if (isOpen && activeCaseId && !hasHistory) {
      loadChatHistory();
    }
  }, [isOpen, activeCaseId, hasHistory]);

  const loadChatHistory = async () => {
    if (!activeCaseId) return;

    try {
      const response = await apiClient.get(`/api/v1/chat/case/${activeCaseId}/history?limit=20`);

      if (response.data && response.data.length > 0) {
        const historyMessages: Message[] = response.data.map((msg: any) => ({
          id: msg.id,
          type: msg.role === 'user' ? 'user' : 'ai',
          content: msg.content,
          timestamp: new Date(msg.created_at),
          citations: msg.context_rules,
        }));

        setMessages(historyMessages);
        setHasHistory(true);
      }
    } catch (err) {
      console.error('[AI] Failed to load history:', err);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    if (isOpen && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, currentMessage, isStreaming]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Handle file selection
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type === 'application/pdf') {
        setStagedFile(file);
      } else {
        const errorMsg: Message = {
          id: `error-${Date.now()}`,
          type: 'error',
          content: 'Only PDF files are accepted',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, errorMsg]);
      }
    }
  }, []);

  // Upload document
  const uploadDocument = async () => {
    if (!stagedFile || !activeCaseId || isUploading) return;

    setIsUploading(true);
    setUploadProgress(10);

    const uploadingMsg: Message = {
      id: `uploading-${Date.now()}`,
      type: 'system',
      content: `Uploading: ${stagedFile.name}...`,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, uploadingMsg]);

    try {
      setUploadProgress(30);

      const formData = new FormData();
      formData.append('file', stagedFile);
      formData.append('case_id', activeCaseId);

      setUploadProgress(50);

      const response = await apiClient.post('/api/v1/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setUploadProgress(90);

      const analysis = response.data.analysis || {};
      const deadlinesMentioned = analysis.deadlines_mentioned || [];
      let fatalCount = 0;
      let criticalCount = 0;
      deadlinesMentioned.forEach((d: any) => {
        const priority = (d.priority || '').toLowerCase();
        if (priority === 'fatal') fatalCount++;
        if (priority === 'critical') criticalCount++;
      });

      const docketMsg: Message = {
        id: `docket-${Date.now()}`,
        type: 'docket',
        content: response.data.docketing_message || response.data.message || 'Document processed',
        timestamp: new Date(),
        docketCard: {
          filename: stagedFile.name,
          documentType: analysis.document_type || 'Legal Document',
          deadlinesExtracted: response.data.deadlines_extracted || 0,
          fatalCount,
          criticalCount,
          documentId: response.data.document_id,
          caseId: response.data.case_id,
          extractionMethod: response.data.extraction_method || 'manual',
        },
      };

      setMessages(prev => prev.filter(m => m.id !== uploadingMsg.id).concat(docketMsg));
      setStagedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      setUploadProgress(100);

      if (response.data.deadlines_extracted > 0) {
        deadlineEvents.created({ case_id: activeCaseId });
      }

    } catch (err: any) {
      console.error('[AI] Upload failed:', err);
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        type: 'error',
        content: `Upload failed: ${err.response?.data?.detail || err.message || 'Unknown error'}`,
        timestamp: new Date(),
      };
      setMessages(prev => prev.filter(m => m.id !== uploadingMsg.id).concat(errorMsg));
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  // Auto-upload when file is staged
  useEffect(() => {
    if (stagedFile && activeCaseId && !isUploading) {
      uploadDocument();
    }
  }, [stagedFile, activeCaseId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const command = input.trim();
    if (!command || isStreaming) return;

    // Add user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: command,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');

    // Handle special commands
    if (command.toLowerCase() === 'clear') {
      setMessages([]);
      return;
    }

    // Handle filter commands locally
    const cmdLower = command.toLowerCase();

    if (cmdLower === 'show all') {
      filterEvents.showAll();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'Showing all deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }
    if (cmdLower === 'show overdue') {
      filterEvents.showOverdue();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'Showing overdue deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }
    if (cmdLower === 'show pending') {
      filterEvents.showPending();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'Showing pending deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }
    if (cmdLower === 'show completed') {
      filterEvents.showCompleted();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'Showing completed deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }

    if (cmdLower.startsWith('filter ')) {
      const priority = command.slice(7).trim().toLowerCase();
      filterEvents.filterByPriority(priority);
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: `Showing ${priority} priority deadlines`, timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }

    if (cmdLower.startsWith('search ')) {
      const query = command.slice(7).trim();
      filterEvents.search(query);
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: `Searching for: "${query}"`, timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }

    if (cmdLower === 'reset' || cmdLower === 'clear filters') {
      filterEvents.clear();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'Cleared all filters', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }

    // Send to AI via streaming
    try {
      await sendMessage(command);
    } catch (err: any) {
      console.error('[AI] Streaming error:', err);
    }
  };

  // Render document card
  const renderDocketCard = (card: DocketCardData) => {
    return (
      <div className="mt-3 bg-slate-50 border border-slate-200 rounded-lg overflow-hidden">
        <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-semibold text-slate-900 truncate">{card.filename}</span>
        </div>
        <div className="px-4 py-3 space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Type:</span>
            <span className="text-slate-900 font-medium">{card.documentType}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Deadlines:</span>
            <span className="flex items-center gap-2">
              {card.fatalCount > 0 && (
                <span className="text-red-600 font-medium">{card.fatalCount} Fatal</span>
              )}
              {card.criticalCount > 0 && (
                <span className="text-orange-600 font-medium">{card.criticalCount} Critical</span>
              )}
              {card.fatalCount === 0 && card.criticalCount === 0 && (
                <span className="text-green-600 font-medium">{card.deadlinesExtracted} Found</span>
              )}
            </span>
          </div>
        </div>
        <div className="border-t border-slate-200 px-4 py-3 flex gap-2">
          <button
            onClick={() => router.push(`/cases/${card.caseId}`)}
            className="flex-1 btn-secondary text-xs py-2"
          >
            View Case
          </button>
          <button
            onClick={() => router.push(`/cases/${card.caseId}?tab=deadlines`)}
            className="flex-1 btn-primary text-xs py-2"
          >
            View Deadlines
          </button>
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Floating Command Bar - Always visible at bottom */}
      {!isOpen && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-40">
          <button
            onClick={() => setIsOpen(true)}
            className="bg-white border border-slate-300 shadow-lg rounded-full px-6 py-3 flex items-center gap-3 hover:shadow-xl transition-all hover:scale-105"
          >
            <MessageSquare className="w-4 h-4 text-slate-600" />
            <span className="text-sm text-slate-600">Ask about cases, deadlines, or rules</span>
            <kbd className="px-2 py-0.5 bg-slate-100 border border-slate-300 rounded text-xs font-mono text-slate-500">
              ⌘K
            </kbd>
          </button>
        </div>
      )}

      {/* Modal Overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-modal w-full max-w-4xl h-[80vh] flex flex-col animate-scale-in">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <MessageSquare className="w-5 h-5 text-blue-600" />
                <h2 className="text-lg font-semibold text-slate-900">AI Assistant</h2>
                {activeCaseId && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-mono">
                    Case Active
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {isStreaming && (
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Thinking...
                  </span>
                )}
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Upload Progress Bar */}
            {isUploading && uploadProgress > 0 && (
              <div className="px-6 py-3 bg-slate-50 border-b border-slate-200">
                <div className="flex items-center gap-3 mb-2">
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  <span className="text-sm text-slate-600">Processing document...</span>
                </div>
                <div className="h-1 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600 transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-light">
              {messages.length === 0 && (
                <div className="text-center py-12">
                  <MessageSquare className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500 text-sm">Start a conversation with the AI assistant</p>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.type === 'user' ? (
                    <div className="bg-blue-600 text-white rounded-2xl px-4 py-2 max-w-[80%]">
                      <p className="text-sm">{msg.content}</p>
                    </div>
                  ) : msg.type === 'ai' ? (
                    <div className="bg-slate-100 text-slate-900 rounded-2xl px-4 py-3 max-w-[80%]">
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  ) : msg.type === 'system' ? (
                    <div className="bg-amber-50 text-amber-800 rounded-lg px-3 py-2 text-xs">
                      {msg.content}
                    </div>
                  ) : msg.type === 'error' ? (
                    <div className="bg-red-50 text-red-700 rounded-lg px-3 py-2 text-sm">
                      {msg.content}
                    </div>
                  ) : msg.type === 'docket' && msg.docketCard ? (
                    <div className="w-full">
                      {renderDocketCard(msg.docketCard)}
                    </div>
                  ) : null}
                </div>
              ))}

              {/* Streaming content */}
              {isStreaming && currentMessage && !isAwaitingApproval && (
                <div className="flex justify-start">
                  <div className="bg-slate-100 text-slate-900 rounded-2xl px-4 py-3 max-w-[80%]">
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown>{currentMessage}</ReactMarkdown>
                    </div>
                    <div className="w-2 h-4 bg-blue-600 animate-pulse inline-block ml-1" />
                  </div>
                </div>
              )}

              {/* Approval card */}
              {isAwaitingApproval && streamState.type === 'awaiting_approval' && (
                <ProposalCard
                  toolCall={streamState.toolCall}
                  approvalId={streamState.approvalId}
                  onApprove={(modifications) => {
                    approveToolUse(streamState.approvalId, modifications);
                  }}
                  onReject={(reason) => {
                    rejectToolUse(streamState.approvalId, reason);
                  }}
                />
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Staged File Preview */}
            {stagedFile && !isUploading && (
              <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex items-center gap-3">
                <FileText className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-slate-700 flex-1 truncate">{stagedFile.name}</span>
                <span className="text-xs text-slate-500">
                  {(stagedFile.size / 1024 / 1024).toFixed(2)} MB
                </span>
                <button
                  onClick={() => {
                    setStagedFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                  className="text-slate-400 hover:text-red-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Input Area */}
            <form onSubmit={handleSubmit} className="px-6 py-4 border-t border-slate-200 flex items-center gap-3">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={!activeCaseId || isUploading}
                className={`p-2 rounded-lg transition-colors ${
                  activeCaseId && !isUploading
                    ? 'text-slate-600 hover:bg-slate-100'
                    : 'text-slate-300 cursor-not-allowed'
                }`}
                title={activeCaseId ? 'Upload document' : 'Navigate to a case first'}
              >
                <Paperclip className="w-5 h-5" />
              </button>

              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={activeCaseId ? "Ask a question or type a command..." : "Navigate to a case first..."}
                className="flex-1 input"
                disabled={isUploading || isStreaming}
                autoComplete="off"
              />

              {!isStreaming && input.length > 0 && (
                <button
                  type="submit"
                  className="btn-primary"
                >
                  Send
                </button>
              )}

              {isStreaming && (
                <button
                  type="button"
                  onClick={cancelStream}
                  className="btn-danger"
                >
                  Cancel
                </button>
              )}
            </form>
          </div>
        </div>
      )}
    </>
  );
}

export default AITerminal;
