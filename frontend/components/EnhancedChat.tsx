'use client'

import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Send, Loader2, CheckCircle2, XCircle, Sparkles, User, Bot, Copy, Check, Zap } from 'lucide-react'
import { chatEvents, deadlineEvents } from '@/lib/eventBus'
import { API_URL } from '@/lib/config'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: string[]
  actions_taken?: Array<{
    tool: string
    input: any
    result: any
  }>
  tokens_used?: number
  created_at: string
}

interface EnhancedChatProps {
  caseId: string
  caseNumber?: string
  onActionTaken?: () => void
}

export default function EnhancedChat({ caseId, caseNumber, onActionTaken }: EnhancedChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState<string>('')
  const [lastUserMessage, setLastUserMessage] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    loadChatHistory()
  }, [caseId])

  const loadChatHistory = async () => {
    try {
      const token = localStorage.getItem('accessToken')
      const response = await fetch(`${API_URL}/api/v1/chat/case/${caseId}/history?limit=50`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (response.ok) {
        const history = await response.json()
        const formattedMessages: Message[] = history.map((msg: any) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          citations: msg.context_rules,
          created_at: msg.created_at
        }))
        setMessages(formattedMessages)
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }

  const sendMessage = async (messageOverride?: string) => {
    const userMessage = messageOverride || input.trim()
    if (!userMessage || isLoading) return

    if (!messageOverride) {
      setInput('')
      // Reset textarea height
      if (inputRef.current) {
        inputRef.current.style.height = '48px'
      }
    }

    setLastUserMessage(userMessage)

    // Add user message immediately (only if not a retry)
    if (!messageOverride) {
      const tempUserMsg: Message = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content: userMessage,
        created_at: new Date().toISOString()
      }
      setMessages(prev => [...prev, tempUserMsg])
    }

    setIsLoading(true)
    setLoadingMessage('Analyzing your request...')

    try {
      const token = localStorage.getItem('accessToken')
      const response = await fetch(`${API_URL}/api/v1/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userMessage,
          case_id: caseId
        })
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const result = await response.json()

      // Robust circular reference handler
      const getCircularReplacer = () => {
        const seen = new WeakSet();
        return (key: string, value: any) => {
          if (typeof value === "object" && value !== null) {
            if (seen.has(value)) {
              return "[Circular Reference]";
            }
            seen.add(value);
          }
          return value;
        };
      };

      // Deep clone to remove circular references
      let sanitizedResult;
      try {
        const stringified = JSON.stringify(result, getCircularReplacer());
        const parsed = JSON.parse(stringified);
        sanitizedResult = {
          message_id: parsed.message_id || `msg-${Date.now()}`,
          response: parsed.response || '',
          citations: parsed.citations || [],
          actions_taken: parsed.actions_taken || [],
          tokens_used: parsed.tokens_used || 0
        };
      } catch (e) {
        // Fallback to basic object if JSON fails
        console.warn('JSON sanitization failed, using fallback:', e);
        sanitizedResult = {
          message_id: `msg-${Date.now()}`,
          response: typeof result.response === 'string' ? result.response : 'Response received',
          citations: [],
          actions_taken: [],
          tokens_used: 0
        };
      }

      // Add assistant message
      const assistantMsg: Message = {
        id: sanitizedResult.message_id || `msg-${Date.now()}`,
        role: 'assistant',
        content: sanitizedResult.response,
        citations: sanitizedResult.citations,
        actions_taken: sanitizedResult.actions_taken,
        tokens_used: sanitizedResult.tokens_used,
        created_at: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMsg])

      // Emit chat events - wrap in try/catch to prevent event errors from breaking chat
      try {
        chatEvents.messageSent({
          id: assistantMsg.id,
          role: assistantMsg.role,
          content: assistantMsg.content
        });
      } catch (e) {
        console.warn('Event emission error (non-critical):', e);
      }

      // If actions were taken, emit specific events and trigger refresh
      if (sanitizedResult.actions_taken && sanitizedResult.actions_taken.length > 0) {
        try {
          // Emit event for each action type
          sanitizedResult.actions_taken.forEach((action: any) => {
            if (action.tool === 'create_deadline' || action.tool === 'create_trigger_deadline') {
              deadlineEvents.created(action.result);
            } else if (action.tool === 'update_deadline') {
              deadlineEvents.updated(action.result);
            } else if (action.tool === 'delete_deadline') {
              deadlineEvents.deleted(action.input?.deadline_id);
            }
          });

          // Emit general action taken event
          chatEvents.actionTaken(sanitizedResult.actions_taken);
        } catch (e) {
          console.warn('Event emission error (non-critical):', e);
        }

        // Call the callback for backward compatibility
        if (onActionTaken) {
          onActionTaken();
        }
      }
    } catch (error) {
      // Safely log error without circular references
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      console.error('Chat error:', errorMessage)

      // Remove loading state and show error with retry option
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: '❌ **Oops! Something went wrong.**\n\nI encountered an error processing your request. This could be due to a network issue or a temporary problem with the AI service.',
        created_at: new Date().toISOString()
      }
      setMessages(prev => {
        // Remove last user message if it was just added (to avoid duplication on retry)
        const filtered = prev.filter(msg => msg.id !== `temp-${Date.now()}`)
        return [...filtered, errorMsg]
      })
    } finally {
      setIsLoading(false)
      setLoadingMessage('')
    }
  }

  const retryLastMessage = () => {
    if (lastUserMessage) {
      // Remove last error message
      setMessages(prev => prev.filter(msg => !msg.id.startsWith('error-')))
      sendMessage(lastUserMessage)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)

    // Auto-resize textarea
    const textarea = e.target
    textarea.style.height = '48px'
    const scrollHeight = textarea.scrollHeight
    textarea.style.height = Math.min(scrollHeight, 120) + 'px'
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500 rounded-lg">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">AI Docketing Assistant</h3>
            <p className="text-sm text-gray-600">
              {caseNumber ? `Case ${caseNumber}` : 'Ask me anything about this case'}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-block p-4 bg-blue-50 rounded-full mb-4">
              <Bot className="w-12 h-12 text-blue-500" />
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">
              Welcome to your AI Assistant!
            </h4>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              I can help you manage deadlines, answer questions about your case, and provide expert guidance.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-3xl mx-auto">
              <SuggestionChip
                icon="📅"
                onClick={() => setInput("What's due in the next 30 days?")}
                text="What's due next month?"
                description="View upcoming deadlines"
              />
              <SuggestionChip
                icon="⚖️"
                onClick={() => setInput("Set trial date to September 15, 2025")}
                text="Set a trial date"
                description="Auto-generate pretrial deadlines"
              />
              <SuggestionChip
                icon="📄"
                onClick={() => setInput("What templates do you have for appeals?")}
                text="Browse templates"
                description="See all deadline templates"
              />
              <SuggestionChip
                icon="🔔"
                onClick={() => setInput("Show me all critical deadlines")}
                text="Critical deadlines"
                description="View high-priority items"
              />
            </div>
          </div>
        )}

        {messages.map((message, idx) => (
          <div key={message.id}>
            <MessageBubble message={message} />
            {message.id.startsWith('error-') && idx === messages.length - 1 && (
              <div className="flex justify-start mt-3">
                <button
                  onClick={retryLastMessage}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm font-medium flex items-center gap-2"
                >
                  <Loader2 className="w-4 h-4" />
                  Retry
                </button>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <div className="bg-gray-50 rounded-2xl px-4 py-3 inline-block">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  <span className="text-sm text-gray-600">{loadingMessage}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask me anything or give me a command..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            rows={1}
            disabled={isLoading}
            style={{
              minHeight: '48px',
              maxHeight: '120px',
              height: '48px'
            }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 font-medium"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Send className="w-5 h-5" />
                Send
              </>
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = React.useState(false)

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-gradient-to-br from-gray-500 to-gray-700'
            : 'bg-gradient-to-br from-blue-500 to-indigo-600'
        }`}
      >
        {isUser ? (
          <User className="w-6 h-6 text-white" />
        ) : (
          <Bot className="w-6 h-6 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 ${isUser ? 'flex justify-end' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-blue-500 text-white'
              : 'bg-gray-50 text-gray-900 border border-gray-200'
          } ${isUser ? 'max-w-md' : 'max-w-full'}`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-blue">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || '')
                    const inline = !match
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    )
                  },
                  table({ children }) {
                    return (
                      <div className="overflow-x-auto my-4">
                        <table className="min-w-full divide-y divide-gray-300 border border-gray-200 rounded-lg">
                          {children}
                        </table>
                      </div>
                    )
                  },
                  thead({ children }) {
                    return <thead className="bg-gray-50">{children}</thead>
                  },
                  th({ children }) {
                    return (
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-900 uppercase tracking-wider">
                        {children}
                      </th>
                    )
                  },
                  td({ children }) {
                    return <td className="px-4 py-2 text-sm text-gray-700">{children}</td>
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Actions Taken */}
          {message.actions_taken && message.actions_taken.length > 0 && (
            <div className="mt-3 space-y-2">
              <div className="text-xs font-semibold text-gray-600 mb-2">Actions Taken:</div>
              {message.actions_taken.map((action, idx) => (
                <ActionIndicator key={idx} action={action} />
              ))}
            </div>
          )}

          {/* Citations */}
          {message.citations && message.citations.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="text-xs font-semibold text-gray-600 mb-1">Rule Citations:</div>
              <div className="flex flex-wrap gap-2">
                {message.citations.map((citation, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium"
                  >
                    {citation}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Timestamp and Actions */}
        <div className={`flex items-center gap-2 mt-1 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
          <div className="text-xs text-gray-500">
            {new Date(message.created_at).toLocaleTimeString()}
          </div>
          {!isUser && (
            <button
              onClick={copyToClipboard}
              className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded hover:bg-gray-100"
              title="Copy message"
            >
              {copied ? (
                <Check className="w-3 h-3 text-green-500" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function ActionIndicator({ action }: { action: any }) {
  const isSuccess = action.result?.success !== false
  const [isAnimating, setIsAnimating] = React.useState(true)

  React.useEffect(() => {
    const timer = setTimeout(() => setIsAnimating(false), 600)
    return () => clearTimeout(timer)
  }, [])

  const toolNames: Record<string, string> = {
    create_deadline: 'Created Deadline',
    create_trigger_deadline: 'Created Trigger Event',
    update_deadline: 'Updated Deadline',
    delete_deadline: 'Deleted Deadline',
    query_deadlines: 'Queried Deadlines',
    update_case_info: 'Updated Case Info'
  }

  const toolIcons: Record<string, any> = {
    create_deadline: CheckCircle2,
    create_trigger_deadline: Zap,
    update_deadline: CheckCircle2,
    delete_deadline: XCircle,
    query_deadlines: CheckCircle2,
    update_case_info: CheckCircle2
  }

  const toolName = toolNames[action.tool] || action.tool
  const Icon = toolIcons[action.tool] || CheckCircle2

  // Extract details from result
  const getActionDetails = () => {
    if (action.tool === 'create_trigger_deadline' && action.result?.dependent_deadlines) {
      return `Generated ${action.result.dependent_deadlines.length} deadline(s)`
    }
    if (action.tool === 'create_deadline' && action.result?.deadline) {
      return action.result.deadline.title
    }
    if (action.result?.message) {
      return action.result.message
    }
    return null
  }

  const details = getActionDetails()

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all duration-300 ${
        isAnimating ? 'scale-105' : 'scale-100'
      } ${
        isSuccess ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
      }`}
    >
      <div className={`flex-shrink-0 ${isAnimating ? 'animate-pulse' : ''}`}>
        {isSuccess ? (
          <Icon className="w-4 h-4" />
        ) : (
          <XCircle className="w-4 h-4" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-semibold flex items-center gap-2">
          {toolName}
          {action.tool === 'create_trigger_deadline' && (
            <span className="inline-flex items-center px-1.5 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
              <Zap className="w-3 h-3 mr-0.5" />
              Auto
            </span>
          )}
        </div>
        {details && (
          <div className="text-xs opacity-80 mt-0.5 truncate">{details}</div>
        )}
      </div>
    </div>
  )
}

function SuggestionChip({
  onClick,
  text,
  description,
  icon
}: {
  onClick: () => void
  text: string
  description: string
  icon: string
}) {
  return (
    <button
      onClick={onClick}
      className="group px-4 py-4 bg-white border-2 border-gray-200 rounded-xl hover:border-blue-400 hover:bg-gradient-to-br hover:from-blue-50 hover:to-indigo-50 transition-all text-left shadow-sm hover:shadow-md"
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl">{icon}</div>
        <div className="flex-1">
          <div className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
            {text}
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            {description}
          </div>
        </div>
      </div>
    </button>
  )
}
