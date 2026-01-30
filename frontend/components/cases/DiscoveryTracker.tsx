'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import {
  FileSearch,
  Send,
  Inbox,
  Clock,
  CheckCircle,
  AlertTriangle,
  Plus,
  ChevronDown,
  ChevronUp,
  Calendar,
  FileText,
  Users,
} from 'lucide-react';

interface DiscoveryRequest {
  id: string;
  request_type: string;
  request_number: number | null;
  direction: string;
  from_party: string | null;
  to_party: string | null;
  title: string | null;
  description: string | null;
  items: Array<{ number: number; text: string; status: string }>;
  served_date: string | null;
  response_due_date: string | null;
  response_received_date: string | null;
  status: string;
}

interface DiscoveryTrackerProps {
  caseId: string;
  className?: string;
}

const REQUEST_TYPE_LABELS: Record<string, string> = {
  interrogatories: 'Interrogatories',
  requests_for_production: 'Requests for Production',
  requests_for_admission: 'Requests for Admission',
  subpoena: 'Subpoena',
  deposition_notice: 'Deposition Notice',
  other: 'Other',
};

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: typeof CheckCircle }> = {
  pending: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: Clock },
  served: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Send },
  received: { bg: 'bg-green-100', text: 'text-green-700', icon: Inbox },
  overdue: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertTriangle },
  completed: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
  objected: { bg: 'bg-orange-100', text: 'text-orange-700', icon: AlertTriangle },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.pending;
  const Icon = style.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  );
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function getDaysUntilDue(dueDateStr: string | null): number | null {
  if (!dueDateStr) return null;
  const dueDate = new Date(dueDateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  dueDate.setHours(0, 0, 0, 0);
  return Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export default function DiscoveryTracker({ caseId, className = '' }: DiscoveryTrackerProps) {
  const [requests, setRequests] = useState<DiscoveryRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [expandedRequests, setExpandedRequests] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'outgoing' | 'incoming'>('all');

  useEffect(() => {
    fetchDiscovery();
  }, [caseId]);

  const fetchDiscovery = async () => {
    try {
      const response = await apiClient.get(`/api/v1/case-intelligence/cases/${caseId}/discovery`);
      setRequests(response.data || []);
    } catch (error) {
      console.error('Failed to fetch discovery:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleRequest = (id: string) => {
    setExpandedRequests((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const filteredRequests = requests.filter((r) => {
    if (filter === 'outgoing') return r.direction === 'outgoing';
    if (filter === 'incoming') return r.direction === 'incoming';
    return true;
  });

  const outgoingCount = requests.filter((r) => r.direction === 'outgoing').length;
  const incomingCount = requests.filter((r) => r.direction === 'incoming').length;
  const pendingCount = requests.filter((r) => r.status === 'pending' || r.status === 'served').length;
  const overdueCount = requests.filter((r) => {
    if (!r.response_due_date || r.status === 'completed') return false;
    const days = getDaysUntilDue(r.response_due_date);
    return days !== null && days < 0;
  }).length;

  if (loading) {
    return (
      <div className={`card ${className}`}>
        <div className="flex items-center justify-center py-6">
          <FileSearch className="w-5 h-5 text-slate-400 animate-pulse" />
          <span className="ml-2 text-sm text-slate-500">Loading discovery...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`card overflow-hidden ${className}`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <FileSearch className="w-5 h-5 text-blue-600" />
          <div className="text-left">
            <h3 className="font-semibold text-slate-900">Discovery Tracking</h3>
            <div className="flex items-center gap-3 mt-0.5 text-sm">
              <span className="text-slate-500">{requests.length} requests</span>
              {pendingCount > 0 && (
                <span className="text-yellow-600">{pendingCount} pending</span>
              )}
              {overdueCount > 0 && (
                <span className="text-red-600">{overdueCount} overdue</span>
              )}
            </div>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400" />
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-slate-200">
          {/* Stats Row */}
          <div className="grid grid-cols-4 gap-2 p-4 bg-slate-50">
            <div className="text-center">
              <p className="text-lg font-bold text-slate-900">{outgoingCount}</p>
              <p className="text-xs text-slate-500">Outgoing</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-slate-900">{incomingCount}</p>
              <p className="text-xs text-slate-500">Incoming</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-yellow-600">{pendingCount}</p>
              <p className="text-xs text-slate-500">Pending</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-red-600">{overdueCount}</p>
              <p className="text-xs text-slate-500">Overdue</p>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex border-b border-slate-200">
            {(['all', 'outgoing', 'incoming'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                  filter === f
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {f === 'all' ? 'All' : f === 'outgoing' ? 'Sent' : 'Received'}
              </button>
            ))}
          </div>

          {/* Request List */}
          <div className="max-h-96 overflow-y-auto">
            {filteredRequests.length === 0 ? (
              <div className="text-center py-8">
                <FileSearch className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No discovery requests</p>
                <button className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium">
                  <Plus className="w-4 h-4 inline mr-1" />
                  Add Discovery Request
                </button>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {filteredRequests.map((request) => {
                  const isExpanded = expandedRequests.has(request.id);
                  const daysUntilDue = getDaysUntilDue(request.response_due_date);
                  const isOverdue = daysUntilDue !== null && daysUntilDue < 0;
                  const isDueSoon = daysUntilDue !== null && daysUntilDue >= 0 && daysUntilDue <= 7;

                  return (
                    <div key={request.id} className="bg-white">
                      <button
                        onClick={() => toggleRequest(request.id)}
                        className="w-full px-4 py-3 text-left hover:bg-slate-50 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              {request.direction === 'outgoing' ? (
                                <Send className="w-4 h-4 text-blue-500" />
                              ) : (
                                <Inbox className="w-4 h-4 text-green-500" />
                              )}
                              <span className="font-medium text-slate-900 truncate">
                                {request.title || REQUEST_TYPE_LABELS[request.request_type] || request.request_type}
                              </span>
                              {request.request_number && (
                                <span className="text-xs text-slate-400">#{request.request_number}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                              <span>{REQUEST_TYPE_LABELS[request.request_type] || request.request_type}</span>
                              {request.response_due_date && (
                                <span className={`flex items-center gap-1 ${
                                  isOverdue ? 'text-red-600' : isDueSoon ? 'text-orange-600' : ''
                                }`}>
                                  <Calendar className="w-3 h-3" />
                                  Due {formatDate(request.response_due_date)}
                                  {isOverdue && ` (${Math.abs(daysUntilDue!)} days overdue)`}
                                  {isDueSoon && !isOverdue && ` (${daysUntilDue} days)`}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <StatusBadge status={isOverdue ? 'overdue' : request.status} />
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4 text-slate-400" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-slate-400" />
                            )}
                          </div>
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="px-4 pb-3 bg-slate-50 border-t border-slate-100">
                          <div className="grid grid-cols-2 gap-4 py-3 text-sm">
                            <div>
                              <p className="text-xs text-slate-500">From</p>
                              <p className="text-slate-800">{request.from_party || 'N/A'}</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-500">To</p>
                              <p className="text-slate-800">{request.to_party || 'N/A'}</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-500">Served</p>
                              <p className="text-slate-800">{formatDate(request.served_date)}</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-500">Response Due</p>
                              <p className={`${isOverdue ? 'text-red-600 font-medium' : 'text-slate-800'}`}>
                                {formatDate(request.response_due_date)}
                              </p>
                            </div>
                          </div>

                          {request.description && (
                            <div className="py-2 border-t border-slate-200">
                              <p className="text-xs text-slate-500 mb-1">Description</p>
                              <p className="text-sm text-slate-700">{request.description}</p>
                            </div>
                          )}

                          {request.items && request.items.length > 0 && (
                            <div className="py-2 border-t border-slate-200">
                              <p className="text-xs text-slate-500 mb-2">Items ({request.items.length})</p>
                              <div className="space-y-1">
                                {request.items.slice(0, 5).map((item, idx) => (
                                  <div key={idx} className="flex items-start gap-2 text-sm">
                                    <span className="text-slate-400 font-mono text-xs">
                                      {item.number}.
                                    </span>
                                    <span className="text-slate-700 flex-1">{item.text}</span>
                                    {item.status && (
                                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                                        item.status === 'responded' ? 'bg-green-100 text-green-700' :
                                        item.status === 'objected' ? 'bg-orange-100 text-orange-700' :
                                        'bg-slate-100 text-slate-600'
                                      }`}>
                                        {item.status}
                                      </span>
                                    )}
                                  </div>
                                ))}
                                {request.items.length > 5 && (
                                  <p className="text-xs text-slate-400">
                                    +{request.items.length - 5} more items
                                  </p>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Add Button */}
          <div className="p-3 border-t border-slate-200 bg-slate-50">
            <button className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors">
              <Plus className="w-4 h-4" />
              Add Discovery Request
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
