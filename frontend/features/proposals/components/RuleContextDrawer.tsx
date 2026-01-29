'use client';

/**
 * RuleContextDrawer - Slide-out panel showing full research context for a rule proposal
 *
 * Phase 3 of intelligent document recognition - "Glass Box" transparency
 *
 * Shows:
 * - Full AI reasoning
 * - Source documents and citations
 * - Conflict analysis
 * - Edit capabilities
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  Check,
  Edit3,
  AlertTriangle,
  ExternalLink,
  BookOpen,
  Scale,
  Clock,
  ChevronRight,
  Save,
  RefreshCw,
} from 'lucide-react';
import type { RuleProposal, RuleProposalConflict } from '@/types';

interface RuleContextDrawerProps {
  proposal: RuleProposal | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (proposalId: string, notes?: string) => void;
  onReject: (proposalId: string, reason?: string) => void;
  onModify: (proposalId: string, modifications: ModificationValues, notes?: string) => void;
  isProcessing?: boolean;
}

interface ModificationValues {
  proposed_trigger?: string;
  proposed_days?: number;
  proposed_priority?: string;
  proposed_calculation_method?: string;
}

const priorityOptions = [
  { value: 'fatal', label: 'Fatal', description: 'Jurisdictional - missing = case dismissal' },
  { value: 'critical', label: 'Critical', description: 'Court-ordered deadline' },
  { value: 'important', label: 'Important', description: 'Procedural with consequences' },
  { value: 'standard', label: 'Standard', description: 'Best practice deadline' },
  { value: 'informational', label: 'Informational', description: 'Internal reminder only' },
];

const calculationMethods = [
  { value: 'calendar_days', label: 'Calendar Days' },
  { value: 'business_days', label: 'Business Days' },
  { value: 'court_days', label: 'Court Days' },
];

export default function RuleContextDrawer({
  proposal,
  isOpen,
  onClose,
  onApprove,
  onReject,
  onModify,
  isProcessing = false,
}: RuleContextDrawerProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [modifications, setModifications] = useState<ModificationValues>({});
  const [notes, setNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectConfirm, setShowRejectConfirm] = useState(false);

  // Reset state when proposal changes
  useEffect(() => {
    if (proposal) {
      setModifications({
        proposed_trigger: proposal.proposed_trigger,
        proposed_days: proposal.proposed_days,
        proposed_priority: proposal.proposed_priority,
        proposed_calculation_method: proposal.proposed_calculation_method || 'calendar_days',
      });
      setNotes('');
      setIsEditing(false);
      setShowRejectConfirm(false);
      setRejectionReason('');
    }
  }, [proposal]);

  const handleApprove = () => {
    if (!proposal) return;

    if (isEditing) {
      // Modified approval
      onModify(proposal.id, modifications, notes);
    } else {
      // Direct approval
      onApprove(proposal.id, notes);
    }
  };

  const handleReject = () => {
    if (!proposal) return;

    if (showRejectConfirm) {
      onReject(proposal.id, rejectionReason);
      onClose();
    } else {
      setShowRejectConfirm(true);
    }
  };

  const hasConflicts = proposal?.conflicts && proposal.conflicts.length > 0;
  const hasWarnings = proposal?.warnings && proposal.warnings.length > 0;

  // Confidence level styling
  const getConfidenceStyle = (score?: number) => {
    if (!score) return { color: 'text-slate-500', bg: 'bg-slate-200' };
    if (score >= 0.8) return { color: 'text-green-600', bg: 'bg-green-500' };
    if (score >= 0.6) return { color: 'text-yellow-600', bg: 'bg-yellow-500' };
    return { color: 'text-red-600', bg: 'bg-red-500' };
  };

  const confidenceStyle = getConfidenceStyle(proposal?.confidence_score);

  if (!isOpen || !proposal) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/30 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-white shadow-2xl z-50 flex flex-col transform transition-transform">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-amber-50 to-orange-50">
          <div>
            <div className="flex items-center gap-2 text-xs text-amber-600 font-semibold uppercase">
              <Scale className="w-4 h-4" />
              Rule Proposal Review
            </div>
            <h2 className="text-lg font-bold text-slate-800 mt-1">
              {isEditing ? 'Edit Rule Proposal' : 'Review AI Discovery'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Confidence Score */}
          <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
            <div>
              <span className="text-sm font-medium text-slate-700">AI Confidence</span>
              <p className="text-xs text-slate-500">How certain the AI is about this rule</p>
            </div>
            <div className="text-right">
              <div className={`text-2xl font-bold ${confidenceStyle.color}`}>
                {proposal.confidence_score
                  ? `${Math.round(proposal.confidence_score * 100)}%`
                  : 'N/A'}
              </div>
              <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden mt-1">
                <div
                  className={`h-full ${confidenceStyle.bg} transition-all`}
                  style={{ width: `${(proposal.confidence_score || 0) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Rule Details - View/Edit Mode */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-700 uppercase">
                Rule Details
              </h3>
              {!isEditing && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit
                </button>
              )}
            </div>

            {isEditing ? (
              // Edit Mode
              <div className="space-y-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Trigger Event
                  </label>
                  <input
                    type="text"
                    value={modifications.proposed_trigger || ''}
                    onChange={(e) =>
                      setModifications((prev) => ({ ...prev, proposed_trigger: e.target.value }))
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Days
                    </label>
                    <input
                      type="number"
                      value={modifications.proposed_days || 0}
                      onChange={(e) =>
                        setModifications((prev) => ({
                          ...prev,
                          proposed_days: parseInt(e.target.value) || 0,
                        }))
                      }
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      min={0}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Calculation
                    </label>
                    <select
                      value={modifications.proposed_calculation_method || 'calendar_days'}
                      onChange={(e) =>
                        setModifications((prev) => ({
                          ...prev,
                          proposed_calculation_method: e.target.value,
                        }))
                      }
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {calculationMethods.map((method) => (
                        <option key={method.value} value={method.value}>
                          {method.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Priority
                  </label>
                  <select
                    value={modifications.proposed_priority || 'standard'}
                    onChange={(e) =>
                      setModifications((prev) => ({ ...prev, proposed_priority: e.target.value }))
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {priorityOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label} - {option.description}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => setIsEditing(false)}
                  className="text-sm text-slate-600 hover:text-slate-800"
                >
                  Cancel editing
                </button>
              </div>
            ) : (
              // View Mode
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <span className="text-sm text-slate-600">Trigger Event</span>
                  <span className="text-sm font-medium text-slate-800">
                    {proposal.proposed_trigger}
                  </span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <span className="text-sm text-slate-600">Response Time</span>
                  <span className="text-sm font-medium text-slate-800 flex items-center gap-1">
                    <Clock className="w-4 h-4 text-slate-400" />
                    {proposal.proposed_days} days
                  </span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <span className="text-sm text-slate-600">Calculation Method</span>
                  <span className="text-sm font-medium text-slate-800">
                    {(proposal.proposed_calculation_method || 'calendar_days').replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <span className="text-sm text-slate-600">Priority</span>
                  <span
                    className={`text-sm font-medium px-2 py-0.5 rounded ${
                      proposal.proposed_priority === 'fatal'
                        ? 'bg-red-100 text-red-700'
                        : proposal.proposed_priority === 'critical'
                        ? 'bg-orange-100 text-orange-700'
                        : proposal.proposed_priority === 'important'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}
                  >
                    {proposal.proposed_priority}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Citation & Sources */}
          {proposal.citation && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 uppercase mb-3">
                Legal Citation
              </h3>
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <Scale className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div>
                      <p className="font-medium text-blue-800">{proposal.citation}</p>
                      {proposal.source_text && (
                        <blockquote className="mt-2 text-sm text-blue-700 italic border-l-2 border-blue-400 pl-3">
                          "{proposal.source_text}"
                        </blockquote>
                      )}
                    </div>
                  </div>
                  {proposal.citation_url && (
                    <a
                      href={proposal.citation_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 p-1"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* AI Reasoning */}
          {proposal.reasoning && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 uppercase mb-3">
                AI Reasoning
              </h3>
              <div className="p-4 bg-slate-50 rounded-lg">
                <div className="flex items-start gap-3">
                  <BookOpen className="w-5 h-5 text-slate-500 mt-0.5" />
                  <p className="text-sm text-slate-700 italic">"{proposal.reasoning}"</p>
                </div>
              </div>
            </div>
          )}

          {/* Conflicts */}
          {hasConflicts && (
            <div>
              <h3 className="text-sm font-semibold text-red-700 uppercase mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Detected Conflicts
              </h3>
              <div className="space-y-2">
                {proposal.conflicts!.map((conflict, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg ${
                      conflict.severity === 'error'
                        ? 'bg-red-50 border border-red-200'
                        : 'bg-amber-50 border border-amber-200'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <AlertTriangle
                        className={`w-4 h-4 mt-0.5 ${
                          conflict.severity === 'error' ? 'text-red-500' : 'text-amber-500'
                        }`}
                      />
                      <div>
                        <span
                          className={`text-xs font-semibold uppercase ${
                            conflict.severity === 'error' ? 'text-red-600' : 'text-amber-600'
                          }`}
                        >
                          {conflict.type.replace(/_/g, ' ')}
                        </span>
                        <p
                          className={`text-sm mt-1 ${
                            conflict.severity === 'error' ? 'text-red-700' : 'text-amber-700'
                          }`}
                        >
                          {conflict.message}
                        </p>
                        {conflict.existing_days && conflict.proposed_days && (
                          <p className="text-xs mt-1 text-slate-600">
                            Existing: {conflict.existing_days} days | Proposed:{' '}
                            {conflict.proposed_days} days
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {hasWarnings && (
            <div>
              <h3 className="text-sm font-semibold text-amber-700 uppercase mb-3">Warnings</h3>
              <ul className="space-y-2">
                {proposal.warnings!.map((warning, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 p-2 rounded"
                  >
                    <ChevronRight className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Notes */}
          <div>
            <h3 className="text-sm font-semibold text-slate-700 uppercase mb-3">
              Attorney Notes (Optional)
            </h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any notes about your decision..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              rows={3}
            />
          </div>

          {/* Rejection Confirm */}
          {showRejectConfirm && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <h4 className="font-medium text-red-800 mb-2">Confirm Rejection</h4>
              <p className="text-sm text-red-700 mb-3">
                This will dismiss the AI suggestion. You can optionally provide a reason:
              </p>
              <input
                type="text"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Reason for rejection (optional)..."
                className="w-full px-3 py-2 border border-red-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 text-sm"
              />
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="border-t border-slate-200 p-4 bg-slate-50">
          <div className="flex gap-3">
            <button
              onClick={handleApprove}
              disabled={isProcessing}
              className="flex-1 flex items-center justify-center gap-2 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors disabled:opacity-50"
            >
              {isProcessing ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : isEditing ? (
                <Save className="w-5 h-5" />
              ) : (
                <Check className="w-5 h-5" />
              )}
              {isEditing ? 'Save & Approve' : 'Approve Rule'}
            </button>

            <button
              onClick={handleReject}
              disabled={isProcessing}
              className="flex-1 flex items-center justify-center gap-2 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors disabled:opacity-50"
            >
              <X className="w-5 h-5" />
              {showRejectConfirm ? 'Confirm Reject' : 'Reject'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
