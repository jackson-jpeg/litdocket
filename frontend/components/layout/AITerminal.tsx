'use client';

/**
 * AI Terminal - The ONE Brain
 *
 * The Sovereign Design System's command interface.
 * This is the ONLY way to communicate with the AI.
 * Dark terminal aesthetic with actual API integration.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import apiClient from '@/lib/api-client';
import { deadlineEvents, filterEvents } from '@/lib/eventBus';

interface Message {
  id: string;
  type: 'user' | 'system' | 'ai' | 'error' | 'action';
  content: string;
  timestamp: Date;
  actions?: ActionTaken[];
  citations?: string[];
}

interface ActionTaken {
  tool: string;
  input: any;
  result: any;
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
  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [hasHistory, setHasHistory] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { caseId, casePath } = useCaseContext();

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const command = input.trim();
    if (!command || isProcessing) return;

    // Add user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: command,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsProcessing(true);

    // Handle special commands
    if (command.toLowerCase() === 'clear') {
      setMessages([{
        id: 'system-clear',
        type: 'system',
        content: 'TERMINAL CLEARED',
        timestamp: new Date(),
      }]);
      setIsProcessing(false);
      return;
    }

    if (command.toLowerCase() === 'help') {
      const helpMsg: Message = {
        id: `help-${Date.now()}`,
        type: 'system',
        content: `AVAILABLE COMMANDS:
• clear - Clear terminal
• help - Show this help

FILTER COMMANDS:
• show all - Show all deadlines
• show overdue - Show overdue deadlines
• show pending - Show pending deadlines
• show completed - Show completed deadlines
• filter critical - Show critical/fatal deadlines
• filter high - Show high priority deadlines
• search [query] - Search deadlines

AI QUERIES:
• "What's due in the next 30 days?"
• "Set trial date to March 15, 2025"
• "Add a deposition deadline for next Friday"`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, helpMsg]);
      setIsProcessing(false);
      return;
    }

    // Handle filter commands locally (no AI needed)
    const cmdLower = command.toLowerCase();

    // Show commands
    if (cmdLower === 'show all') {
      filterEvents.showAll();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Showing all deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      setIsProcessing(false);
      return;
    }
    if (cmdLower === 'show overdue') {
      filterEvents.showOverdue();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Showing overdue deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      setIsProcessing(false);
      return;
    }
    if (cmdLower === 'show pending') {
      filterEvents.showPending();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Showing pending deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      setIsProcessing(false);
      return;
    }
    if (cmdLower === 'show completed') {
      filterEvents.showCompleted();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Showing completed deadlines', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      setIsProcessing(false);
      return;
    }

    // Filter by priority
    if (cmdLower.startsWith('filter ')) {
      const priority = command.slice(7).trim().toLowerCase();
      filterEvents.filterByPriority(priority);
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: `FILTER: Showing ${priority} priority deadlines`, timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      setIsProcessing(false);
      return;
    }

    // Search
    if (cmdLower.startsWith('search ')) {
      const query = command.slice(7).trim();
      filterEvents.search(query);
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: `SEARCH: "${query}"`, timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      setIsProcessing(false);
      return;
    }

    // Clear filters
    if (cmdLower === 'reset' || cmdLower === 'clear filters') {
      filterEvents.clear();
      const msg: Message = { id: `filter-${Date.now()}`, type: 'system', content: 'FILTER: Cleared all filters', timestamp: new Date() };
      setMessages(prev => [...prev, msg]);
      setIsProcessing(false);
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
      setIsProcessing(false);
      return;
    }

    // Send to AI
    try {
      const response = await apiClient.post('/api/v1/chat/message', {
        message: command,
        case_id: caseId,
      });

      // Parse response
      const aiMsg: Message = {
        id: response.data.message_id || `ai-${Date.now()}`,
        type: 'ai',
        content: response.data.response,
        timestamp: new Date(),
        citations: response.data.citations,
        actions: response.data.actions_taken,
      };

      setMessages(prev => [...prev, aiMsg]);

      // Handle actions taken
      if (response.data.actions_taken && response.data.actions_taken.length > 0) {
        // Log actions
        const actionMsg: Message = {
          id: `action-${Date.now()}`,
          type: 'action',
          content: formatActions(response.data.actions_taken),
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, actionMsg]);

        // Emit events for UI updates
        response.data.actions_taken.forEach((action: ActionTaken) => {
          if (action.tool === 'create_deadline' || action.tool === 'create_trigger_deadline') {
            deadlineEvents.created(action.result);
          } else if (action.tool === 'update_deadline') {
            deadlineEvents.updated(action.result);
          } else if (action.tool === 'delete_deadline') {
            deadlineEvents.deleted(action.input?.deadline_id);
          }
        });
      }

    } catch (err: any) {
      console.error('[TERMINAL] API error:', err);
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        type: 'error',
        content: `ERROR: ${err.response?.data?.detail || err.message || 'Failed to process request'}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsProcessing(false);
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
      default: return '>';
    }
  };

  return (
    <div className="cockpit-terminal">
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
          <div
            className="flex items-center justify-between px-4 py-2 border-b border-gray-700 cursor-pointer"
            onClick={toggleExpanded}
          >
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
                [Click to collapse]
              </span>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 ${isProcessing ? 'bg-terminal-amber animate-pulse' : (caseId ? 'bg-terminal-green' : 'bg-terminal-amber')}`}></span>
                <span className="text-terminal-text font-mono text-xs">
                  {isProcessing ? 'PROCESSING' : (caseId ? 'READY' : 'NO CASE')}
                </span>
              </div>
            </div>
          </div>

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

            {isProcessing && (
              <div className="text-terminal-green font-mono text-sm">
                <span className="text-terminal-amber">[AI] </span>
                <span className="animate-pulse">Processing...</span>
                <span className="terminal-cursor ml-1" />
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <form onSubmit={handleSubmit} className="flex items-center px-4 py-2 border-t border-gray-700 bg-terminal-bg">
            <span className="text-terminal-amber font-mono text-sm mr-2">{'>'}</span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={caseId ? "Type a command or ask a question..." : "Navigate to a case first..."}
              className="terminal-input flex-1"
              disabled={isProcessing}
              autoComplete="off"
              spellCheck={false}
            />
            {!isProcessing && input.length > 0 && (
              <button
                type="submit"
                className="text-terminal-green font-mono text-sm ml-2 hover:text-white transition-colors"
              >
                [SEND]
              </button>
            )}
          </form>
        </div>
      )}
    </div>
  );
}

export default AITerminal;
