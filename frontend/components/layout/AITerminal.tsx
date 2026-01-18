'use client';

/**
 * AI Terminal - The ONE Brain
 *
 * The Sovereign Design System's command interface.
 * This is the ONLY way to communicate with the AI.
 * Dark terminal aesthetic with actual API integration.
 *
 * V2: In-Stream Docketing - Upload documents directly from chat
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import apiClient from '@/lib/api-client';
import { deadlineEvents, filterEvents } from '@/lib/eventBus';
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

  // Match /cases/[caseId] pattern
  const match = pathname?.match(/\/cases\/([a-zA-Z0-9-]+)/);

  return {
    caseId: match ? match[1] : null,
    casePath: match ? pathname : null,
  };
}

export function AITerminal() {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
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
    caseId: caseId || '',
    onToken: (token: string) => {
      // Update current AI message with new token
      if (currentAIMessageId) {
        setMessages(prev => prev.map(msg =>
          msg.id === currentAIMessageId
            ? { ...msg, content: msg.content + token }
            : msg
        ));
      }
    },
    onStatus: (status: string, message: string) => {
      console.log(`[STREAMING] Status: ${status} - ${message}`);
    },
    onToolUse: (toolCall: any) => {
      console.log(`[STREAMING] Tool use: ${toolCall.tool_name}`, toolCall);
    },
    onToolResult: (toolId: string, result: any) => {
      console.log(`[STREAMING] Tool result:`, result);

      // Handle deadline events for UI updates
      if (result.success) {
        // Parse tool name from result or track it separately
        // For now, we'll rely on WebSocket events in Phase 2
        // Phase 1: just log the result
      }
    },
    onError: (error: string, code?: string) => {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        type: 'error',
        content: `ERROR [${code || 'UNKNOWN'}]: ${error}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    },
    onDone: (data: { message_id: string; tokens_used: number }) => {
      console.log(`[STREAMING] Done. Tokens: ${data.tokens_used}`);
      setCurrentAIMessageId(null);
    }
  });

  // Initialize with system message
  useEffect(() => {
    const systemMsg: Message = {
      id: 'system-init',
      type: 'system',
      content: caseId
        ? `LITDOCKET AI TERMINAL v2.0 // CASE CONTEXT ACTIVE`
        : `LITDOCKET AI TERMINAL v2.0 // NO CASE SELECTED`,
      timestamp: new Date(),
    };
    setMessages([systemMsg]);
    setHasHistory(false);
  }, [caseId]);

  // Load chat history when case context changes
  useEffect(() => {
    if (caseId && !hasHistory) {
      loadChatHistory();
    }
  }, [caseId, hasHistory]);

  const loadChatHistory = async () => {
    if (!caseId) return;

    try {
      const response = await apiClient.get(`/api/v1/chat/case/${caseId}/history?limit=20`);

      if (response.data && response.data.length > 0) {
        const historyMessages: Message[] = response.data.map((msg: any) => ({
          id: msg.id,
          type: msg.role === 'user' ? 'user' : 'ai',
          content: msg.content,
          timestamp: new Date(msg.created_at),
          citations: msg.context_rules,
        }));

        // Prepend system message, then history
        setMessages(prev => {
          const systemMsg = prev.find(m => m.id === 'system-init');
          const historyNote: Message = {
            id: 'history-loaded',
            type: 'system',
            content: `[LOADED ${historyMessages.length} MESSAGES FROM HISTORY]`,
            timestamp: new Date(),
          };
          return [
            systemMsg!,
            historyNote,
            ...historyMessages,
          ].filter(Boolean);
        });
        setHasHistory(true);
      }
    } catch (err) {
      console.error('[TERMINAL] Failed to load history:', err);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    if (expanded && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, expanded]);

  // Focus input when expanded
  useEffect(() => {
    if (expanded && inputRef.current) {
      inputRef.current.focus();
    }
  }, [expanded]);

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
    if (!stagedFile || !caseId || isUploading) return;

    setIsUploading(true);
    setUploadProgress(10);

    // Add system message about upload
    const uploadingMsg: Message = {
      id: `uploading-${Date.now()}`,
      type: 'system',
      content: `UPLOADING: ${stagedFile.name}...`,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, uploadingMsg]);

    try {
      setUploadProgress(30);

      const formData = new FormData();
      formData.append('file', stagedFile);
      formData.append('case_id', caseId);

      setUploadProgress(50);

      const response = await apiClient.post('/api/v1/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setUploadProgress(90);

      // Count priority levels from analysis
      const analysis = response.data.analysis || {};
      const deadlinesMentioned = analysis.deadlines_mentioned || [];
      let fatalCount = 0;
      let criticalCount = 0;
      deadlinesMentioned.forEach((d: any) => {
        const priority = (d.priority || '').toLowerCase();
        if (priority === 'fatal') fatalCount++;
        if (priority === 'critical') criticalCount++;
      });

      // Create docket card message
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

      // Remove "uploading" message and add docket card
      setMessages(prev => prev.filter(m => m.id !== uploadingMsg.id).concat(docketMsg));

      // Clear staged file
      setStagedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      setUploadProgress(100);

      // Emit deadline created events if any
      if (response.data.deadlines_extracted > 0) {
        deadlineEvents.created({ case_id: caseId });
      }

    } catch (err: any) {
      console.error('[TERMINAL] Upload failed:', err);
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        type: 'error',
        content: `UPLOAD FAILED: ${err.response?.data?.detail || err.message || 'Unknown error'}`,
        timestamp: new Date(),
      };
      // Remove "uploading" message and add error
      setMessages(prev => prev.filter(m => m.id !== uploadingMsg.id).concat(errorMsg));
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  // Auto-upload when file is staged (or wait for send)
  // For now, upload immediately on file selection
  useEffect(() => {
    if (stagedFile && caseId && !isUploading) {
      uploadDocument();
    }
  }, [stagedFile, caseId]);

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
      setMessages([{
        id: 'system-clear',
        type: 'system',
        content: 'TERMINAL CLEARED',
        timestamp: new Date(),
      }]);
      return;
    }

    if (command.toLowerCase() === 'help') {
      const helpMsg: Message = {
        id: `help-${Date.now()}`,
        type: 'system',
        content: `AVAILABLE COMMANDS:
• clear - Clear terminal
• help - Show this help

DOCUMENT UPLOAD:
• Click the paperclip icon to upload a PDF
• Documents are auto-analyzed and deadlines extracted

FILTER COMMANDS:
• show all - Show all deadlines
• show overdue - Show overdue deadlines
• show pending - Show pending deadlines
• show completed - Show completed deadlines
• filter critical - Show critical/fatal deadlines
• filter high - Show high priority deadlines
• search [query] - Search deadlines

AI QUERIES (STREAMING):
• "What's due in the next 30 days?"
• "Set trial date to March 15, 2025"
• "Add a deposition deadline for next Friday"
• Destructive actions require approval`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, helpMsg]);
      return;
    }

    // Handle filter commands locally (no AI needed)
    const cmdLower = command.toLowerCase();

    // Show commands
    if (cmdLower === 'show all') {
      filterEvents.showAll();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Showing all deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }
    if (cmdLower === 'show overdue') {
      filterEvents.showOverdue();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Showing overdue deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }
    if (cmdLower === 'show pending') {
      filterEvents.showPending();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Showing pending deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }
    if (cmdLower === 'show completed') {
      filterEvents.showCompleted();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Showing completed deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }

    // Filter by priority
    if (cmdLower.startsWith('filter ')) {
      const priority = command.slice(7).trim().toLowerCase();
      filterEvents.filterByPriority(priority);
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: `FILTER: Showing ${priority} priority deadlines`, timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }

    // Search
    if (cmdLower.startsWith('search ')) {
      const query = command.slice(7).trim();
      filterEvents.search(query);
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: `SEARCH: "${query}"`, timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }

    // Clear filters
    if (cmdLower === 'reset' || cmdLower === 'clear filters') {
      filterEvents.clear();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Cleared all filters', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      return;
    }

    // Check if we have case context
    if (!caseId) {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        type: 'error',
        content: 'NO CASE CONTEXT. Navigate to a case first or specify case ID.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
      return;
    }

    // Create placeholder AI message for streaming
    const aiMessageId = `ai-${Date.now()}`;
    const aiMsg: Message = {
      id: aiMessageId,
      type: 'ai',
      content: '',
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, aiMsg]);
    setCurrentAIMessageId(aiMessageId);

    // Send to AI via streaming
    try {
      await sendMessage(command);
    } catch (err: any) {
      console.error('[TERMINAL] Streaming error:', err);
      // Error will be handled by onError callback
    }
  };

  const formatActions = (actions: ActionTaken[]): string => {
    return actions.map(a => {
      const toolName = a.tool.replace(/_/g, ' ').toUpperCase();
      const status = a.result?.success !== false ? '✓' : '✗';
      return `[${status}] ${toolName}`;
    }).join('\n');
  };

  const toggleExpanded = () => {
    setExpanded(!expanded);
  };

  const getMessageColor = (type: Message['type']) => {
    switch (type) {
      case 'user': return 'text-terminal-text';
      case 'system': return 'text-terminal-amber';
      case 'ai': return 'text-terminal-green';
      case 'error': return 'text-red-500';
      case 'action': return 'text-blue-400';
      case 'docket': return 'text-cyan-400';
      default: return 'text-terminal-text';
    }
  };

  const getMessagePrefix = (type: Message['type']) => {
    switch (type) {
      case 'user': return '>';
      case 'system': return '[SYS]';
      case 'ai': return '[AI]';
      case 'error': return '[ERR]';
      case 'action': return '[ACT]';
      case 'docket': return '[DOC]';
      default: return '>';
    }
  };

  // Render Mini-Docket Card
  const renderDocketCard = (card: DocketCardData) => {
    return (
      <div className="mt-2 bg-slate-800 border border-slate-600 font-mono text-xs">
        {/* Header */}
        <div className="bg-slate-700 border-b border-slate-600 px-3 py-2 flex items-center gap-2">
          <FileText className="w-4 h-4 text-cyan-400" />
          <span className="text-white font-bold truncate">{card.filename}</span>
        </div>
        {/* Body */}
        <div className="px-3 py-2 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">TYPE:</span>
            <span className="text-white">{card.documentType}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">DEADLINES:</span>
            <span className="flex items-center gap-2">
              {card.fatalCount > 0 && (
                <span className="text-red-500">{card.fatalCount} Fatal</span>
              )}
              {card.criticalCount > 0 && (
                <span className="text-amber-500">{card.criticalCount} Critical</span>
              )}
              {card.fatalCount === 0 && card.criticalCount === 0 && (
                <span className="text-emerald-400">{card.deadlinesExtracted} Found</span>
              )}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">METHOD:</span>
            <span className={card.extractionMethod === 'trigger' ? 'text-cyan-400' : 'text-slate-300'}>
              {card.extractionMethod === 'trigger' ? 'Rule-Based Chain' : 'AI Extraction'}
            </span>
          </div>
        </div>
        {/* Actions */}
        <div className="border-t border-slate-600 px-3 py-2 flex gap-2">
          <button
            onClick={() => router.push(`/cases/${card.caseId}`)}
            className="flex-1 bg-slate-700 hover:bg-slate-600 py-1 text-center text-cyan-400 transition-colors"
          >
            View Case
          </button>
          <button
            onClick={() => {
              // Scroll to deadlines or navigate
              router.push(`/cases/${card.caseId}?tab=deadlines`);
            }}
            className="flex-1 bg-slate-700 hover:bg-slate-600 py-1 text-center text-cyan-400 transition-colors"
          >
            View Deadlines
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="cockpit-terminal">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Collapsed Bar */}
      {!expanded && (
        <div className="terminal-collapsed" onClick={toggleExpanded}>
          <div className="flex items-center gap-3">
            <span className="text-terminal-green font-mono text-sm">{'>'}_</span>
            <span className="text-terminal-text font-mono text-sm">
              AI Terminal
            </span>
            {caseId && (
              <span className="text-terminal-amber font-mono text-xs">
                [CASE:{caseId.slice(0, 8)}...]
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            <span className="text-terminal-text font-mono text-xs opacity-60">
              [Click to expand]
            </span>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 ${caseId ? 'bg-terminal-green' : 'bg-terminal-amber'}`}></span>
              <span className="text-terminal-text font-mono text-xs">
                {caseId ? 'READY' : 'NO CASE'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Expanded Terminal */}
      {expanded && (
        <div className="terminal">
          {/* Terminal Header */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
            <div className="flex items-center gap-3">
              <span className="text-terminal-green font-mono text-sm">{'>'}_</span>
              <span className="text-terminal-text font-mono text-sm">
                AI Terminal
              </span>
              {caseId && (
                <span className="text-terminal-amber font-mono text-xs">
                  [CASE:{caseId.slice(0, 8)}...]
                </span>
              )}
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 ${isStreaming || isUploading ? 'bg-terminal-amber animate-pulse' : (caseId ? 'bg-terminal-green' : 'bg-terminal-amber')}`}></span>
                <span className="text-terminal-text font-mono text-xs">
                  {isUploading ? 'UPLOADING' : isStreaming ? 'STREAMING' : isAwaitingApproval ? 'AWAITING APPROVAL' : (caseId ? 'READY' : 'NO CASE')}
                </span>
              </div>
              <button
                onClick={toggleExpanded}
                className="text-terminal-text hover:text-red-400 transition-colors p-1"
                title="Minimize terminal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Upload Progress Bar */}
          {isUploading && uploadProgress > 0 && (
            <div className="px-4 py-2 bg-slate-800 border-b border-gray-700">
              <div className="flex items-center gap-3 mb-1">
                <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                <span className="text-cyan-400 font-mono text-xs">PROCESSING DOCUMENT...</span>
              </div>
              <div className="h-1 bg-slate-700 overflow-hidden">
                <div
                  className="h-full bg-cyan-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Messages Area */}
          <div className="terminal-expanded custom-scrollbar">
            {messages.map((msg) => (
              <div key={msg.id} className="mb-2 font-mono text-sm">
                <div className={`${getMessageColor(msg.type)}`}>
                  <span className="text-terminal-amber">{getMessagePrefix(msg.type)} </span>
                  {msg.type === 'ai' ? (
                    <div className="inline prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <span>{children}</span>,
                          code: ({ children }) => (
                            <code className="bg-gray-800 px-1 text-terminal-green">{children}</code>
                          ),
                          ul: ({ children }) => <ul className="list-disc ml-4 my-1">{children}</ul>,
                          ol: ({ children }) => <ol className="list-decimal ml-4 my-1">{children}</ol>,
                          li: ({ children }) => <li className="my-0">{children}</li>,
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  ) : msg.type === 'docket' && msg.docketCard ? (
                    <div>
                      <span className="whitespace-pre-wrap">{msg.content}</span>
                      {renderDocketCard(msg.docketCard)}
                    </div>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="ml-6 mt-1 text-xs text-terminal-amber opacity-75">
                    [REF: {msg.citations.join(', ')}]
                  </div>
                )}
              </div>
            ))}

            {/* Streaming indicator */}
            {isStreaming && !isAwaitingApproval && (
              <div className="text-terminal-green font-mono text-sm">
                <span className="text-terminal-amber">[AI] </span>
                <span className="animate-pulse">Streaming response...</span>
                <span className="terminal-cursor ml-1" />
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
            <div className="px-4 py-2 bg-slate-800 border-t border-gray-700 flex items-center gap-3">
              <FileText className="w-4 h-4 text-cyan-400" />
              <span className="text-white font-mono text-sm flex-1 truncate">{stagedFile.name}</span>
              <span className="text-slate-400 font-mono text-xs">
                {(stagedFile.size / 1024 / 1024).toFixed(2)} MB
              </span>
              <button
                onClick={() => {
                  setStagedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="text-slate-400 hover:text-red-400 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Input Area */}
          <form onSubmit={handleSubmit} className="flex items-center px-4 py-2 border-t border-gray-700 bg-terminal-bg">
            {/* Paperclip Upload Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={!caseId || isUploading}
              className={`mr-2 p-1 transition-colors ${
                caseId && !isUploading
                  ? 'text-slate-400 hover:text-cyan-400'
                  : 'text-slate-600 cursor-not-allowed'
              }`}
              title={caseId ? 'Upload document' : 'Navigate to a case first'}
            >
              <Paperclip className="w-4 h-4" />
            </button>

            <span className="text-terminal-amber font-mono text-sm mr-2">{'>'}</span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={caseId ? "Type a command or ask a question..." : "Navigate to a case first..."}
              className="terminal-input flex-1"
              disabled={isUploading}
              autoComplete="off"
              spellCheck={false}
            />
            {!isStreaming && input.length > 0 && (
              <button
                type="submit"
                className="text-terminal-green font-mono text-sm ml-2 hover:text-white transition-colors"
              >
                [SEND]
              </button>
            )}
            {isStreaming && (
              <button
                type="button"
                onClick={cancelStream}
                className="text-red-400 font-mono text-sm ml-2 hover:text-red-300 transition-colors"
              >
                [CANCEL]
              </button>
            )}
          </form>
        </div>
      )}
    </div>
  );
}

export default AITerminal;
