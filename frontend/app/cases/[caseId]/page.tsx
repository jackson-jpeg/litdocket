'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState, useRef } from 'react';
import { Scale, FileText, Calendar, MessageSquare, ArrowLeft, Loader2, Upload } from 'lucide-react';
import Link from 'next/link';
import apiClient from '@/lib/api-client';

interface CaseData {
  id: string;
  case_number: string;
  title: string;
  court?: string;
  judge?: string;
  jurisdiction?: string;
  district?: string;
  case_type?: string;
  filing_date?: string;
  parties?: Array<{ name: string; role: string }>;
  metadata?: any;
  created_at: string;
}

interface Document {
  id: string;
  file_name: string;
  document_type?: string;
  filing_date?: string;
  ai_summary?: string;
  created_at: string;
}

interface Deadline {
  id: string;
  title: string;
  description: string;
  deadline_date?: string;
  deadline_type: string;
  priority: string;
  status: string;
  party_role?: string;
  action_required?: string;
  applicable_rule?: string;
  calculation_basis?: string;
  is_estimated: boolean;
  source_document?: string;
  created_at: string;
}

interface CaseSummary {
  overview: string;
  current_status: string;
  key_documents: string[];
  critical_deadlines: string[];
  timeline: string[];
  action_items: string[];
  last_updated: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  context_rules?: string[];
  tokens_used?: number;
}

interface ChatAction {
  action: string;
  success: boolean;
  deadline_title?: string;
  deadline_date?: string;
  error?: string;
}

export default function CaseRoomPage() {
  const params = useParams();
  const caseId = params.caseId as string;
  const [caseData, setCaseData] = useState<CaseData | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCaseData();
    fetchDocuments();
    fetchDeadlines();
    fetchCaseSummary();
    fetchChatHistory();
  }, [caseId]);

  const fetchCaseData = async () => {
    try {
      const response = await apiClient.get(`/api/v1/cases/${caseId}`);
      setCaseData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load case data');
    } finally {
      setLoading(false);
    }
  };

  const fetchDocuments = async () => {
    try {
      const response = await apiClient.get(`/api/v1/cases/${caseId}/documents`);
      setDocuments(response.data);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const fetchDeadlines = async () => {
    try {
      const response = await apiClient.get(`/api/v1/deadlines/case/${caseId}`);
      setDeadlines(response.data);
    } catch (err) {
      console.error('Failed to load deadlines:', err);
    }
  };

  const fetchCaseSummary = async () => {
    try {
      const response = await apiClient.get(`/api/v1/cases/${caseId}/summary`);
      setCaseSummary(response.data);
    } catch (err) {
      console.error('Failed to load case summary:', err);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const response = await apiClient.get(`/api/v1/chat/case/${caseId}/history`);
      setChatMessages(response.data);
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || sendingMessage) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setSendingMessage(true);

    // Optimistically add user message
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

      // Add assistant response
      const assistantMsg: ChatMessage = {
        id: response.data.message_id,
        role: 'assistant',
        content: response.data.response,
        created_at: new Date().toISOString(),
        context_rules: response.data.citations,
        tokens_used: response.data.tokens_used
      };

      setChatMessages(prev => [...prev, assistantMsg]);

      // If actions were taken, refresh deadlines and summary
      if (response.data.actions_taken && response.data.actions_taken.length > 0) {
        fetchDeadlines();
        fetchCaseSummary();
      }

    } catch (err: any) {
      console.error('Failed to send message:', err);
      // Add error message
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Loading case room...</p>
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
            <div className="flex items-center gap-3">
              <Scale className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-slate-800">Florida Legal Docketing Assistant</h1>
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
        {/* Success Banner */}
        <div className="mb-8 bg-green-50 border border-green-200 rounded-xl p-6">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-green-900 mb-2">
                🎉 Document Uploaded & Analyzed!
              </h2>
              <p className="text-green-700 mb-2">
                Claude AI has analyzed your document and extracted case information. The file is securely stored in Firebase.
              </p>
              <div className="text-sm text-green-600 space-y-1">
                <div>
                  <strong>{documents.length}</strong> document{documents.length !== 1 ? 's' : ''} in this case
                </div>
                {deadlines.length > 0 && (
                  <div>
                    <strong>{deadlines.length}</strong> deadline{deadlines.length !== 1 ? 's' : ''} auto-extracted using Jackson's methodology
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

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

          {/* Title */}
          {caseData.title && caseData.title !== caseData.case_number && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <label className="text-sm font-medium text-slate-500 uppercase tracking-wide">Title</label>
              <p className="text-base text-slate-900 mt-1">{caseData.title}</p>
            </div>
          )}

          {/* Parties */}
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

        {/* Auto-Updating Case Summary */}
        {caseSummary && (
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl shadow-sm border-2 border-blue-200 p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-blue-900">📋 Case Summary</h2>
              <span className="text-xs text-blue-600">
                Auto-updated {new Date(caseSummary.last_updated).toLocaleString()}
              </span>
            </div>

            {/* Overview */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Overview</h3>
              <p className="text-slate-700">{caseSummary.overview}</p>
            </div>

            {/* Current Status */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Current Status</h3>
              <p className="text-slate-700">{caseSummary.current_status}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Key Documents */}
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

              {/* Critical Deadlines */}
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

              {/* Action Items */}
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

              {/* Timeline */}
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

        {/* 3-Panel Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Panel A: Documents */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-1">
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
                  <div key={doc.id} className="border border-slate-200 rounded-lg p-4 hover:bg-slate-50 transition-colors">
                    <div className="flex items-start gap-3">
                      <FileText className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-900 truncate">{doc.file_name}</p>
                        {doc.document_type && (
                          <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded">
                            {doc.document_type}
                          </span>
                        )}
                        {doc.ai_summary && (
                          <p className="text-xs text-slate-600 mt-2 line-clamp-2">{doc.ai_summary}</p>
                        )}
                        <p className="text-xs text-slate-400 mt-2">
                          {new Date(doc.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit'
                          })}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Panel B: Deadlines */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-1">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Calendar className="w-6 h-6 text-green-600" />
                <h3 className="text-lg font-semibold text-slate-800">Deadlines</h3>
              </div>
              <span className="text-sm font-medium text-slate-500">{deadlines.length}</span>
            </div>

            {deadlines.length === 0 ? (
              <div className="text-center py-12">
                <Calendar className="w-16 h-16 text-slate-200 mx-auto mb-4" />
                <p className="text-sm text-slate-600 mb-2">No deadlines yet</p>
                <p className="text-xs text-slate-500 max-w-xs mx-auto">
                  Upload documents to auto-extract deadlines using Jackson's methodology
                </p>
              </div>
            ) : (
              <div className="space-y-4 max-h-[600px] overflow-y-auto">
                {deadlines.map((deadline) => (
                  <div
                    key={deadline.id}
                    className={`border-l-4 ${
                      deadline.priority === 'high'
                        ? 'border-red-500 bg-red-50'
                        : deadline.priority === 'medium'
                        ? 'border-yellow-500 bg-yellow-50'
                        : 'border-blue-500 bg-blue-50'
                    } rounded-r-lg p-4`}
                  >
                    {/* Line 1: Date and Action */}
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        {deadline.deadline_date ? (
                          <p className="text-sm font-bold text-slate-900">
                            {new Date(deadline.deadline_date).toLocaleDateString('en-US', {
                              month: '2-digit',
                              day: '2-digit',
                              year: 'numeric'
                            })}
                          </p>
                        ) : (
                          <p className="text-sm font-bold text-slate-500">TBD</p>
                        )}
                        <p className="text-sm font-medium text-slate-800 mt-1">
                          {deadline.title}
                        </p>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          deadline.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : deadline.status === 'cancelled'
                            ? 'bg-gray-100 text-gray-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {deadline.status}
                      </span>
                    </div>

                    {/* Line 2 & 3: Calculation and Source (from description) */}
                    {deadline.description && (
                      <div className="text-xs text-slate-600 mt-2 whitespace-pre-line">
                        {deadline.description}
                      </div>
                    )}

                    {/* Additional metadata */}
                    {deadline.applicable_rule && (
                      <div className="mt-2 pt-2 border-t border-slate-200">
                        <p className="text-xs text-slate-500">
                          <span className="font-medium">Rule:</span> {deadline.applicable_rule}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Panel C: AI Chat */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 lg:col-span-1 flex flex-col" style={{ height: '650px' }}>
            {/* Chat Header */}
            <div className="flex items-center gap-3 p-6 border-b border-slate-200">
              <MessageSquare className="w-6 h-6 text-purple-600" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-slate-800">AI Docketing Assistant</h3>
                <p className="text-xs text-slate-500">Ask questions • Create deadlines • Get guidance</p>
              </div>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {chatMessages.length === 0 ? (
                <div className="text-center py-12">
                  <MessageSquare className="w-16 h-16 text-purple-200 mx-auto mb-4" />
                  <p className="text-sm text-slate-600 mb-4 font-medium">Start a conversation</p>
                  <div className="text-xs text-slate-500 space-y-2 max-w-xs mx-auto text-left">
                    <p className="flex items-start gap-2">
                      <span className="text-purple-600">•</span>
                      <span>"What deadlines do I have this week?"</span>
                    </p>
                    <p className="flex items-start gap-2">
                      <span className="text-purple-600">•</span>
                      <span>"Add deadline: answer due in 20 days"</span>
                    </p>
                    <p className="flex items-start gap-2">
                      <span className="text-purple-600">•</span>
                      <span>"What's the rule for responses to motions?"</span>
                    </p>
                    <p className="flex items-start gap-2">
                      <span className="text-purple-600">•</span>
                      <span>"Summarize this case"</span>
                    </p>
                  </div>
                </div>
              ) : (
                chatMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg p-4 ${
                        msg.role === 'user'
                          ? 'bg-purple-600 text-white'
                          : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      {msg.context_rules && msg.context_rules.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-300">
                          <p className="text-xs font-semibold mb-1">Rule Citations:</p>
                          <div className="flex flex-wrap gap-1">
                            {msg.context_rules.map((rule, idx) => (
                              <span
                                key={idx}
                                className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded"
                              >
                                {rule}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      <p className="text-xs opacity-70 mt-2">
                        {new Date(msg.created_at).toLocaleTimeString('en-US', {
                          hour: 'numeric',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </div>
                ))
              )}
              {sendingMessage && (
                <div className="flex justify-start">
                  <div className="bg-slate-100 rounded-lg p-4">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
                      <span className="text-sm text-slate-600">AI is thinking...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div className="p-4 border-t border-slate-200">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendChatMessage();
                    }
                  }}
                  placeholder="Ask a question or give a command..."
                  className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
                  disabled={sendingMessage}
                />
                <button
                  onClick={sendChatMessage}
                  disabled={!chatInput.trim() || sendingMessage}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {sendingMessage ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span className="text-sm font-medium">Send</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Debug Info (Remove later) */}
        <div className="mt-8 bg-slate-50 border border-slate-200 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">✅ System Status</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="font-medium text-slate-600">Case ID:</span>
              <span className="ml-2 font-mono text-slate-800">{caseData.id}</span>
            </div>
            <div>
              <span className="font-medium text-slate-600">Created:</span>
              <span className="ml-2 text-slate-800">
                {new Date(caseData.created_at).toLocaleString()}
              </span>
            </div>
            <div>
              <span className="font-medium text-slate-600">Backend:</span>
              <span className="ml-2 text-green-600">✓ Connected</span>
            </div>
            <div>
              <span className="font-medium text-slate-600">Firebase:</span>
              <span className="ml-2 text-green-600">✓ Active</span>
            </div>
          </div>
          <a
            href="https://console.firebase.google.com/project/florida-docket-assist/storage"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-4 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            View Files in Firebase Storage →
          </a>
        </div>
      </main>
    </div>
  );
}
