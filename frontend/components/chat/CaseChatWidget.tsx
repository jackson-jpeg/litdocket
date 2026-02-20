'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare,
  X,
  Send,
  Loader2,
  Bot,
  User,
  AlertCircle,
  ChevronDown,
  Scale,
  Sparkles,
  Settings,
  EyeOff,
} from 'lucide-react';
import { getApiBaseUrl } from '@/lib/config';
import AgentSelector, { Agent } from './AgentSelector';
import { deadlineEvents, chatEvents } from '@/lib/eventBus';
import { ProposalApprovalCard } from './ProposalApprovalCard';
import { useProposals } from '@/hooks/useProposals';
import { Proposal } from '@/types';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  citations?: string[];
}

interface CaseChatWidgetProps {
  caseId?: string;
  caseName?: string;
}

const STORAGE_KEY = 'litdocket_chat_history';
const SESSION_ID_KEY = 'litdocket_chat_session';
const BUBBLE_HIDDEN_KEY = 'litdocket_chat_bubble_hidden';
const TOOLTIP_SHOWN_KEY = 'litdocket_chat_tooltip_shown';

// Extract rule citations from text (e.g., "Fla. R. Civ. P. 1.140")
function extractCitations(text: string): string[] {
  const patterns = [
    /Fla\. R\. Civ\. P\. \d+\.\d+/gi,
    /Fed\. R\. Civ\. P\. \d+/gi,
    /F\.R\.C\.P\. \d+/gi,
    /Rule \d+\.\d+/gi,
    /\d+ U\.S\.C\. § \d+/gi,
    /\d+ F\.\d+d \d+/gi,
    /\d+ So\.\d+d \d+/gi,
  ];

  const citations = new Set<string>();
  patterns.forEach((pattern) => {
    const matches = text.match(pattern);
    if (matches) {
      matches.forEach((m) => citations.add(m));
    }
  });

  return Array.from(citations);
}

// Generate unique session ID
function generateSessionId(): string {
  return `chat_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

export default function CaseChatWidget({ caseId, caseName }: CaseChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState('');

  // Agent state
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [suggestedAgent, setSuggestedAgent] = useState<Agent | null>(null);
  const [showAgentSelector, setShowAgentSelector] = useState(false);

  // Bubble visibility and tooltip state
  const [isBubbleHidden, setIsBubbleHidden] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  // Phase 7 Step 11: Proposal state
  const [pendingProposals, setPendingProposals] = useState<Proposal[]>([]);
  const { fetchProposal, fetchProposals } = useProposals();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Initialize session ID
  useEffect(() => {
    const stored = localStorage.getItem(SESSION_ID_KEY);
    if (stored) {
      setSessionId(stored);
    } else {
      const newId = generateSessionId();
      localStorage.setItem(SESSION_ID_KEY, newId);
      setSessionId(newId);
    }
  }, []);

  // Initialize bubble visibility and tooltip
  useEffect(() => {
    const bubbleHidden = localStorage.getItem(BUBBLE_HIDDEN_KEY) === 'true';
    setIsBubbleHidden(bubbleHidden);

    // Show tooltip only once per session (sessionStorage)
    const tooltipShown = sessionStorage.getItem(TOOLTIP_SHOWN_KEY);
    if (!tooltipShown && !bubbleHidden) {
      setShowTooltip(true);
      const timer = setTimeout(() => {
        setShowTooltip(false);
        sessionStorage.setItem(TOOLTIP_SHOWN_KEY, 'true');
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  // Fetch available agents
  useEffect(() => {
    const fetchAgents = async () => {
      const token = getAuthToken();
      if (!token) return;

      try {
        const apiUrl = getApiBaseUrl();
        const response = await fetch(`${apiUrl}/api/v1/agents/`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && Array.isArray(data.data)) {
            setAgents(data.data);
          }
        }
      } catch (err) {
        console.warn('Failed to fetch agents:', err);
      }
    };

    fetchAgents();
  }, []);

  // Phase 7 Step 11: Fetch pending proposals for this case
  useEffect(() => {
    const loadPendingProposals = async () => {
      if (!caseId) return;

      try {
        // Fetch proposals with 'pending' status for this case
        const response = await fetchProposals(caseId, 'pending');
        // The fetchProposals hook updates its internal state, but we also
        // want to track proposals locally for this chat session
      } catch (err) {
        console.warn('Failed to fetch pending proposals:', err);
      }
    };

    loadPendingProposals();
  }, [caseId, fetchProposals]);

  // Detect suggested agent based on input
  useEffect(() => {
    if (!inputValue.trim() || agents.length === 0) {
      setSuggestedAgent(null);
      return;
    }

    const messageLower = inputValue.toLowerCase();
    let bestMatch: Agent | null = null;
    let bestScore = 0;

    for (const agent of agents) {
      const phrases = agent.triggering_phrases || [];
      let score = 0;

      for (const phrase of phrases) {
        if (messageLower.includes(phrase.toLowerCase())) {
          score += 1;
        }
      }

      if (score > bestScore) {
        bestScore = score;
        bestMatch = agent;
      }
    }

    // Only suggest if we found a match and it's different from current selection
    if (bestMatch && bestMatch.slug !== selectedAgent?.slug) {
      setSuggestedAgent(bestMatch);
    } else {
      setSuggestedAgent(null);
    }
  }, [inputValue, agents, selectedAgent]);

  // Load chat history from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setMessages(
          parsed.map((m: ChatMessage) => ({
            ...m,
            timestamp: new Date(m.timestamp),
          }))
        );
      } catch {
        // Invalid stored chat history, ignore
      }
    }
  }, []);

  // Save chat history to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      // Keep last 50 messages
      const toStore = messages.slice(-50);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
    }
  }, [messages]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Focus input when opening
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const getAuthToken = (): string | null => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token');
    }
    return null;
  };

  const sendMessage = useCallback(async () => {
    if (!inputValue.trim() || isStreaming) return;

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsStreaming(true);
    setStreamingContent('');
    setError(null);

    // Build SSE URL with auth token as query param
    const token = getAuthToken();
    if (!token) {
      setError('Not authenticated');
      setIsStreaming(false);
      return;
    }

    const apiUrl = getApiBaseUrl();
    const params = new URLSearchParams({
      session_id: sessionId,
      message: userMessage.content,
      token: token,
    });

    if (caseId) {
      params.append('case_id', caseId);
    }

    // Add agent parameter if selected
    if (selectedAgent) {
      params.append('agent', selectedAgent.slug);
    }

    const sseUrl = `${apiUrl}/api/v1/chat/stream?${params.toString()}`;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(sseUrl);
    eventSourceRef.current = eventSource;

    let accumulatedContent = '';
    let citations: string[] = [];

    eventSource.addEventListener('status', () => {
      // Status events (thinking, building_context, etc.) - handled silently
    });

    eventSource.addEventListener('token', (e) => {
      const data = JSON.parse(e.data);
      accumulatedContent += data.text;
      setStreamingContent(accumulatedContent);
    });

    eventSource.addEventListener('done', (e) => {
      const data = JSON.parse(e.data);

      // Extract citations from the content
      citations = extractCitations(accumulatedContent);

      // Add citations from backend if provided
      if (data.citations && Array.isArray(data.citations)) {
        data.citations.forEach((c: string) => {
          if (!citations.includes(c)) {
            citations.push(c);
          }
        });
      }

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: data.message_id || `msg_${Date.now()}`,
        role: 'assistant',
        content: accumulatedContent,
        timestamp: new Date(),
        citations: citations.length > 0 ? citations : undefined,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setStreamingContent('');
      setIsStreaming(false);

      // Phase 7: Emit event bus events for actions taken
      if (data.actions && Array.isArray(data.actions)) {
        data.actions.forEach(async (action: any) => {
          const tool = action.tool;
          const result = action.result;

          // Phase 7 Step 11: Check for proposals that need approval
          if (result.requires_approval && result.proposal_id) {
            // Fetch the full proposal details
            try {
              const proposal = await fetchProposal(result.proposal_id);
              if (proposal) {
                setPendingProposals(prev => {
                  // Avoid duplicates
                  if (prev.some(p => p.id === proposal.id)) {
                    return prev;
                  }
                  return [...prev, proposal];
                });
              }
            } catch (err) {
              console.error('Failed to fetch proposal:', err);
            }
          }

          // Emit deadline events based on tool used (only if not a proposal)
          if (!result.requires_approval) {
            if (tool === 'create_deadline' || tool === 'create_trigger_deadline' || tool === 'execute_trigger') {
              if (result.success && result.deadline_id) {
                deadlineEvents.created({ id: result.deadline_id, ...result });
              }
              // Handle bulk deadline creation from triggers
              if (result.success && result.deadlines && Array.isArray(result.deadlines)) {
                result.deadlines.forEach((dl: any) => {
                  if (dl.id) {
                    deadlineEvents.created({ id: dl.id, ...dl });
                  }
                });
              }
            } else if (tool === 'update_deadline' || tool === 'move_deadline') {
              if (result.success && result.deadline_id) {
                deadlineEvents.updated({ id: result.deadline_id, ...result });
              }
            } else if (tool === 'delete_deadline') {
              if (result.success && action.tool_input?.deadline_id) {
                deadlineEvents.deleted(action.tool_input.deadline_id);
              }
            } else if (tool === 'manage_deadline') {
              // Handle power tool actions
              const actionType = action.tool_input?.action;
              if (actionType === 'create' && result.success && result.deadline_id) {
                deadlineEvents.created({ id: result.deadline_id, ...result });
              } else if (actionType === 'update' && result.success) {
                deadlineEvents.updated({ id: action.tool_input?.deadline_id, ...result });
              } else if (actionType === 'delete' && result.success) {
                deadlineEvents.deleted(action.tool_input?.deadline_id);
              }
            }
          }

          // Emit general chat action event
          chatEvents.actionTaken({ type: tool, payload: result });
        });
      }

      eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
      let errorMessage = 'Connection error';
      try {
        const data = JSON.parse((e as MessageEvent).data || '{}');
        errorMessage = data.error || data.detail || 'Stream error';
      } catch {
        // Not a JSON error event
      }

      setError(errorMessage);
      setIsStreaming(false);
      setStreamingContent('');
      eventSource.close();
    });

    eventSource.onerror = () => {
      if (eventSource.readyState === EventSource.CLOSED) {
        setIsStreaming(false);
        if (!accumulatedContent) {
          setError('Connection closed unexpectedly');
        }
      }
    };
  }, [inputValue, isStreaming, sessionId, caseId, selectedAgent]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearHistory = () => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
    // Generate new session
    const newId = generateSessionId();
    localStorage.setItem(SESSION_ID_KEY, newId);
    setSessionId(newId);
  };

  // Don't render anything if bubble is hidden
  if (isBubbleHidden) {
    return null;
  }

  return (
    <>
      {/* Tooltip - shows once per session */}
      {showTooltip && !isOpen && (
        <div className="fixed bottom-24 right-6 bg-slate-800 text-white text-sm px-3 py-2 rounded-lg shadow-lg z-40">
          Ask about your cases and deadlines
          <div className="absolute bottom-0 right-8 transform translate-y-1/2 rotate-45 w-2 h-2 bg-slate-800" />
        </div>
      )}

      {/* Toggle Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? 'Close chat assistant' : 'Open chat assistant'}
        aria-expanded={isOpen}
        className={`fixed bottom-6 right-6 w-14 h-14 text-white rounded-full shadow-lg flex items-center justify-center transition-colors z-40 ${
          selectedAgent?.color === 'red'
            ? 'bg-red-600 hover:bg-red-700'
            : selectedAgent?.color === 'purple'
            ? 'bg-purple-600 hover:bg-purple-700'
            : selectedAgent?.color === 'green'
            ? 'bg-green-600 hover:bg-green-700'
            : selectedAgent?.color === 'orange'
            ? 'bg-orange-600 hover:bg-orange-700'
            : 'bg-blue-600 hover:bg-blue-700'
        }`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
            >
              <ChevronDown className="w-6 h-6" />
            </motion.div>
          ) : (
            <motion.div
              key="open"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
            >
              <MessageSquare className="w-6 h-6" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Chat Drawer */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed bottom-24 right-6 w-96 max-w-[calc(100vw-3rem)] h-[500px] bg-white rounded-lg shadow-2xl flex flex-col z-50 border border-slate-200"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50 rounded-t-lg">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <Scale className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 text-sm">
                    {selectedAgent ? selectedAgent.name : 'Case Assistant'}
                  </h3>
                  {caseName ? (
                    <p className="text-xs text-slate-500 truncate max-w-[200px]">{caseName}</p>
                  ) : (
                    <p className="text-xs text-slate-500">General Assistance</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setShowAgentSelector(!showAgentSelector)}
                  aria-label="Select AI Agent"
                  aria-expanded={showAgentSelector}
                  className={`p-1.5 rounded transition-colors ${
                    showAgentSelector
                      ? 'bg-blue-100 text-blue-600'
                      : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
                  }`}
                  title="Select AI Agent"
                >
                  <Settings className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setIsOpen(false);
                    setIsBubbleHidden(true);
                    localStorage.setItem(BUBBLE_HIDDEN_KEY, 'true');
                  }}
                  aria-label="Hide chat widget"
                  className="p-1 text-slate-400 hover:text-slate-600 rounded"
                  title="Hide chat widget"
                >
                  <EyeOff className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  aria-label="Close chat"
                  className="p-1 text-slate-400 hover:text-slate-600 rounded"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Agent Selector (collapsible) */}
            <AnimatePresence>
              {showAgentSelector && agents.length > 0 && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-b border-slate-200 bg-slate-50/50 overflow-hidden"
                >
                  <div className="p-3">
                    <p className="text-xs text-slate-500 mb-2 uppercase tracking-wide font-medium">
                      Select Agent
                    </p>
                    <AgentSelector
                      agents={agents}
                      selectedAgent={selectedAgent}
                      onSelectAgent={(agent) => {
                        setSelectedAgent(agent);
                        setSuggestedAgent(null);
                      }}
                      suggestedAgent={suggestedAgent}
                      compact
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && !isStreaming && (
                <div className="text-center py-8">
                  <Sparkles className="w-10 h-10 text-blue-500 mx-auto mb-3" />
                  <p className="text-sm font-medium text-slate-700 mb-1">
                    AI-Powered Docketing Assistant
                  </p>
                  <p className="text-xs text-slate-500">
                    Ask questions about your cases, deadlines, or court rules.
                  </p>
                </div>
              )}

              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-2 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot className="w-4 h-4 text-blue-600" />
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] rounded-lg px-3 py-2 ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-100 text-slate-800'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                    {/* Citations */}
                    {message.citations && message.citations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-200/50">
                        <p className="text-xs text-slate-500 mb-1">Citations:</p>
                        <div className="flex flex-wrap gap-1">
                          {message.citations.map((citation, i) => (
                            <span
                              key={i}
                              className="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-700 text-xs rounded font-medium"
                            >
                              {citation}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {message.role === 'user' && (
                    <div className="w-7 h-7 bg-slate-200 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                      <User className="w-4 h-4 text-slate-600" />
                    </div>
                  )}
                </div>
              ))}

              {/* Streaming Message */}
              {isStreaming && streamingContent && (
                <div className="flex gap-2 justify-start">
                  <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="max-w-[80%] rounded-lg px-3 py-2 bg-slate-100 text-slate-800">
                    <p className="text-sm whitespace-pre-wrap">{streamingContent}</p>
                    <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse" />
                  </div>
                </div>
              )}

              {/* Loading Indicator */}
              {isStreaming && !streamingContent && (
                <div className="flex gap-2 justify-start" role="status" aria-label="Assistant is thinking">
                  <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="px-3 py-2 bg-slate-100 rounded-lg">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div role="alert" className="flex items-start gap-2 p-2 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="w-4 h-4 text-red-500 mt-0.5" aria-hidden="true" />
                  <p className="text-xs text-red-700">{error}</p>
                </div>
              )}

              {/* Phase 7 Step 11: Pending Proposals */}
              {pendingProposals.length > 0 && (
                <div className="space-y-3 mt-4">
                  {pendingProposals.map((proposal) => (
                    <ProposalApprovalCard
                      key={proposal.id}
                      proposal={proposal}
                      onApprovalComplete={() => {
                        // Remove from pending list
                        setPendingProposals(prev => prev.filter(p => p.id !== proposal.id));
                        // Scroll to bottom
                        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                      }}
                    />
                  ))}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t border-slate-200 bg-slate-50 rounded-b-lg">
              {/* Agent suggestion banner */}
              {suggestedAgent && !selectedAgent && (
                <div className="mb-2 p-2 bg-yellow-50 border border-yellow-200 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-yellow-800">
                      Try <strong>{suggestedAgent.name}</strong> for this question
                    </span>
                    <button
                      onClick={() => {
                        setSelectedAgent(suggestedAgent);
                        setSuggestedAgent(null);
                      }}
                      className="px-2 py-0.5 bg-yellow-200 text-yellow-800 hover:bg-yellow-300 transition-colors font-medium"
                    >
                      Use
                    </button>
                  </div>
                </div>
              )}
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={caseId ? 'Ask about this case...' : 'Ask anything...'}
                  disabled={isStreaming}
                  className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
                <button
                  onClick={sendMessage}
                  disabled={isStreaming || !inputValue.trim()}
                  aria-label={isStreaming ? 'Sending message' : 'Send message'}
                  className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isStreaming ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>

              {/* Quick Actions */}
              <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
                <span>Press Enter to send</span>
                {messages.length > 0 && (
                  <button
                    onClick={clearHistory}
                    className="text-slate-400 hover:text-red-500 transition-colors"
                  >
                    Clear history
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
