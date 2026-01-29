'use client';

/**
 * Rule Proposals Review Page
 *
 * Attorney review interface for AI-extracted rule proposals.
 * Features:
 * - Filter by status (pending, approved, rejected)
 * - Full proposal review with source comparison
 * - Approve/reject with modifications
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ChevronRight,
  RefreshCw,
  Scale,
  ArrowLeft,
  Edit,
  ExternalLink,
  BookOpen,
  Filter,
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import { RuleProposal, DeadlineSpec } from '@/types';

type FilterStatus = 'all' | 'pending' | 'approved' | 'rejected' | 'needs_revision';

interface ProposalDetailModalProps {
  proposal: RuleProposal;
  onClose: () => void;
  onApprove: (id: string, notes?: string) => void;
  onReject: (id: string, reason: string) => void;
}

function ProposalDetailModal({ proposal, onClose, onApprove, onReject }: ProposalDetailModalProps) {
  const [notes, setNotes] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const ruleData = proposal.proposed_rule_data;

  const handleApprove = async () => {
    setIsSubmitting(true);
    await onApprove(proposal.id, notes || undefined);
    setIsSubmitting(false);
  };

  const handleReject = async () => {
    if (rejectReason.length < 10) return;
    setIsSubmitting(true);
    await onReject(proposal.id, rejectReason);
    setIsSubmitting(false);
  };

  const getConfidenceBadge = (score: number) => {
    if (score >= 0.8) return { label: 'High Confidence', color: 'bg-green-100 text-green-700' };
    if (score >= 0.5) return { label: 'Medium Confidence', color: 'bg-amber-100 text-amber-700' };
    return { label: 'Low Confidence', color: 'bg-red-100 text-red-700' };
  };

  const confidence = getConfidenceBadge(proposal.confidence_score);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{ruleData.rule_name}</h2>
            <p className="text-sm text-slate-500">{ruleData.citation || ruleData.rule_code}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Metadata */}
          <div className="flex items-center gap-4 mb-6">
            <span className={`px-3 py-1 text-sm font-medium rounded-full ${confidence.color}`}>
              {confidence.label}
            </span>
            <span className="px-3 py-1 text-sm font-medium rounded-full bg-slate-100 text-slate-700">
              {ruleData.authority_tier}
            </span>
            <span className="text-sm text-slate-500">
              Trigger: {ruleData.trigger_type}
            </span>
          </div>

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Extracted Rule */}
            <div>
              <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-3">
                Extracted Rule
              </h3>

              <div className="space-y-4">
                {/* Deadlines */}
                <div className="bg-slate-50 rounded-lg p-4">
                  <h4 className="font-medium text-slate-700 mb-3">Deadlines ({ruleData.deadlines.length})</h4>
                  <div className="space-y-2">
                    {ruleData.deadlines.map((deadline: DeadlineSpec, idx: number) => (
                      <div key={idx} className="bg-white rounded-lg p-3 border border-slate-200">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-slate-900">{deadline.title}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            deadline.priority === 'fatal' ? 'bg-red-100 text-red-700' :
                            deadline.priority === 'critical' ? 'bg-amber-100 text-amber-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            {deadline.priority}
                          </span>
                        </div>
                        <div className="text-sm text-slate-600">
                          {deadline.days_from_trigger > 0 ? '+' : ''}{deadline.days_from_trigger} {deadline.calculation_method}
                          {deadline.party_responsible && ` | ${deadline.party_responsible}`}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Conditions */}
                {ruleData.conditions && Object.keys(ruleData.conditions).length > 0 && (
                  <div className="bg-slate-50 rounded-lg p-4">
                    <h4 className="font-medium text-slate-700 mb-2">Conditions</h4>
                    <pre className="text-sm text-slate-600 overflow-x-auto">
                      {JSON.stringify(ruleData.conditions, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Service Extensions */}
                {ruleData.service_extensions && (
                  <div className="bg-slate-50 rounded-lg p-4">
                    <h4 className="font-medium text-slate-700 mb-2">Service Extensions</h4>
                    <div className="flex gap-4 text-sm">
                      <span>Mail: +{ruleData.service_extensions.mail || 0} days</span>
                      <span>Electronic: +{ruleData.service_extensions.electronic || 0} days</span>
                      <span>Personal: +{ruleData.service_extensions.personal || 0} days</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Source Text */}
            <div>
              <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-3">
                Source Text
              </h3>

              {proposal.source_url && (
                <a
                  href={proposal.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 mb-3"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Source
                </a>
              )}

              <div className="bg-slate-50 rounded-lg p-4 h-[300px] overflow-y-auto">
                <p className="text-sm text-slate-700 whitespace-pre-wrap">
                  {proposal.source_text || 'No source text available'}
                </p>
              </div>

              {proposal.extraction_notes && (
                <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-sm text-amber-800">
                    <strong>AI Notes:</strong> {proposal.extraction_notes}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Reviewer Notes */}
          {!showRejectForm && (
            <div className="mt-6">
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Reviewer Notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any notes about this rule..."
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={2}
              />
            </div>
          )}

          {/* Reject Form */}
          {showRejectForm && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <label className="block text-sm font-medium text-red-700 mb-1.5">
                Rejection Reason (minimum 10 characters)
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Explain why this rule should be rejected..."
                className="w-full px-3 py-2.5 bg-white border border-red-200 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                rows={3}
              />
              <div className="flex items-center gap-2 mt-3">
                <button
                  onClick={() => setShowRejectForm(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleReject}
                  disabled={rejectReason.length < 10 || isSubmitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {!showRejectForm && proposal.status === 'pending' && (
          <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-end gap-3">
            <button
              onClick={() => setShowRejectForm(true)}
              className="px-4 py-2.5 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
            >
              <XCircle className="w-4 h-4 inline mr-1.5" />
              Reject
            </button>
            <button
              onClick={handleApprove}
              disabled={isSubmitting}
              className="px-6 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 inline mr-1.5 animate-spin" />
                  Approving...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 inline mr-1.5" />
                  Approve Rule
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function ProposalCard({ proposal, onSelect }: {
  proposal: RuleProposal;
  onSelect: () => void;
}) {
  const statusStyles: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    pending: { bg: 'bg-amber-100', text: 'text-amber-700', icon: <Clock className="w-4 h-4" /> },
    approved: { bg: 'bg-green-100', text: 'text-green-700', icon: <CheckCircle className="w-4 h-4" /> },
    rejected: { bg: 'bg-red-100', text: 'text-red-700', icon: <XCircle className="w-4 h-4" /> },
    needs_revision: { bg: 'bg-blue-100', text: 'text-blue-700', icon: <Edit className="w-4 h-4" /> },
  };

  const style = statusStyles[proposal.status] || statusStyles.pending;
  const ruleData = proposal.proposed_rule_data;

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.5) return 'text-amber-600';
    return 'text-red-600';
  };

  return (
    <div
      onClick={onSelect}
      className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-slate-900 truncate">{ruleData.rule_name}</p>
          <p className="text-sm text-blue-600 truncate">{ruleData.citation || ruleData.rule_code}</p>
        </div>
        <span className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full ${style.bg} ${style.text}`}>
          {style.icon}
          {proposal.status}
        </span>
      </div>

      <div className="flex items-center gap-4 text-sm text-slate-600 mb-3">
        <span className="flex items-center gap-1.5">
          <Scale className="w-4 h-4" />
          {ruleData.authority_tier}
        </span>
        <span className="flex items-center gap-1.5">
          <FileText className="w-4 h-4" />
          {ruleData.deadlines.length} deadlines
        </span>
        <span className={`font-medium ${getConfidenceColor(proposal.confidence_score)}`}>
          {Math.round(proposal.confidence_score * 100)}% confidence
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">
          {proposal.jurisdiction_name || 'Unknown jurisdiction'}
        </span>
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </div>
    </div>
  );
}

export default function ProposalsPage() {
  const router = useRouter();
  const [proposals, setProposals] = useState<RuleProposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('pending');
  const [selectedProposal, setSelectedProposal] = useState<RuleProposal | null>(null);

  const fetchProposals = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = filterStatus === 'all' ? '' : `?status=${filterStatus}`;
      const response = await apiClient.get(`/authority-core/proposals${params}&limit=100`);
      setProposals(response.data);
    } catch (err) {
      console.error('Failed to fetch proposals:', err);
    } finally {
      setIsLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    fetchProposals();
  }, [fetchProposals]);

  const handleApprove = async (id: string, notes?: string) => {
    try {
      await apiClient.post(`/authority-core/proposals/${id}/approve`, {
        notes,
      });
      setSelectedProposal(null);
      fetchProposals();
    } catch (err) {
      console.error('Failed to approve proposal:', err);
    }
  };

  const handleReject = async (id: string, reason: string) => {
    try {
      await apiClient.post(`/authority-core/proposals/${id}/reject`, {
        reason,
      });
      setSelectedProposal(null);
      fetchProposals();
    } catch (err) {
      console.error('Failed to reject proposal:', err);
    }
  };

  const filterOptions: { value: FilterStatus; label: string }[] = [
    { value: 'pending', label: 'Pending' },
    { value: 'approved', label: 'Approved' },
    { value: 'rejected', label: 'Rejected' },
    { value: 'needs_revision', label: 'Needs Revision' },
    { value: 'all', label: 'All' },
  ];

  const pendingCount = proposals.filter((p) => p.status === 'pending').length;

  return (
    <div className="min-h-screen bg-slate-50 pb-12">
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/tools/authority-core')}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Rule Proposals</h1>
              <p className="text-slate-500">Review and approve AI-extracted rules</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium text-slate-700">Filter:</span>
            <div className="flex items-center gap-1">
              {filterOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setFilterStatus(option.value)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                    filterStatus === option.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={fetchProposals}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        ) : proposals.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
            <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No Proposals Found</h3>
            <p className="text-slate-500 mb-6">
              {filterStatus === 'pending'
                ? 'No pending proposals to review. Extract rules from court websites to generate proposals.'
                : `No proposals with status "${filterStatus}".`}
            </p>
            {filterStatus === 'pending' && (
              <button
                onClick={() => router.push('/tools/authority-core')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                <BookOpen className="w-4 h-4" />
                Go to Authority Core
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {proposals.map((proposal) => (
              <ProposalCard
                key={proposal.id}
                proposal={proposal}
                onSelect={() => setSelectedProposal(proposal)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedProposal && (
        <ProposalDetailModal
          proposal={selectedProposal}
          onClose={() => setSelectedProposal(null)}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}
    </div>
  );
}
