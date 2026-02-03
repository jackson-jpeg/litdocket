'use client';

/**
 * SimpleDeadlineModal - Quick deadline creation
 *
 * A streamlined modal for adding simple deadlines without the full wizard.
 * Only asks for: Title, Date, Priority (optional), Description (optional)
 * Optionally apply an Authority Core rule for proper citation tracking.
 */

import { useState } from 'react';
import { X, Calendar, AlertCircle, Scale, ChevronDown, ChevronUp } from 'lucide-react';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';
import { deadlineEvents } from '@/lib/eventBus';
import RuleSelector from '@/components/authority-core/RuleSelector';
import type { AuthorityRule } from '@/types';

interface SimpleDeadlineModalProps {
  caseId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const PRIORITY_OPTIONS = [
  { value: 'fatal', label: 'Fatal', color: 'text-red-600' },
  { value: 'critical', label: 'Critical', color: 'text-orange-600' },
  { value: 'important', label: 'Important', color: 'text-amber-600' },
  { value: 'standard', label: 'Standard', color: 'text-blue-600' },
  { value: 'informational', label: 'Informational', color: 'text-slate-500' },
];

export default function SimpleDeadlineModal({
  caseId,
  isOpen,
  onClose,
  onSuccess,
}: SimpleDeadlineModalProps) {
  const [title, setTitle] = useState('');
  const [date, setDate] = useState('');
  const [priority, setPriority] = useState('standard');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRuleSelector, setShowRuleSelector] = useState(false);
  const [selectedRule, setSelectedRule] = useState<AuthorityRule | null>(null);

  const { showSuccess, showError } = useToast();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title.trim() || !date) {
      showError('Please enter a title and date');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await apiClient.post('/api/v1/deadlines', {
        case_id: caseId,
        title: title.trim(),
        deadline_date: date,
        priority,
        description: description.trim() || undefined,
        deadline_type: 'manual',
        party_role: 'both',
        action_required: 'Manual deadline',
        status: 'pending',
        // Authority Core fields
        applicable_rule: selectedRule?.citation || selectedRule?.rule_code || undefined,
        rule_citation: selectedRule?.source_text || undefined,
        source_rule_id: selectedRule?.id || undefined,
      });

      showSuccess('Deadline created successfully');
      deadlineEvents.created({ id: response.data?.id || response.data?.data?.id || 'new', case_id: caseId });

      // Reset form
      setTitle('');
      setDate('');
      setPriority('standard');
      setDescription('');
      setSelectedRule(null);
      setShowRuleSelector(false);

      onSuccess?.();
      onClose();
    } catch (err: any) {
      console.error('Failed to create deadline:', err);
      showError(err.response?.data?.detail || 'Failed to create deadline');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setTitle('');
      setDate('');
      setPriority('standard');
      setDescription('');
      setSelectedRule(null);
      setShowRuleSelector(false);
      onClose();
    }
  };

  const handleRuleSelect = (rule: AuthorityRule) => {
    setSelectedRule(rule);
    setShowRuleSelector(false);
    // Optionally auto-fill title if empty
    if (!title.trim() && rule.deadlines?.[0]?.title) {
      setTitle(rule.deadlines[0].title);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Quick Add Deadline</h2>
              <p className="text-sm text-slate-500">Simple deadline creation</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Title */}
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-slate-700 mb-1.5">
              Deadline Title <span className="text-red-500">*</span>
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., File Motion to Compel"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
              autoFocus
              disabled={isSubmitting}
            />
          </div>

          {/* Date */}
          <div>
            <label htmlFor="date" className="block text-sm font-medium text-slate-700 mb-1.5">
              Due Date <span className="text-red-500">*</span>
            </label>
            <input
              id="date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
              disabled={isSubmitting}
            />
          </div>

          {/* Priority */}
          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-slate-700 mb-1.5">
              Priority
            </label>
            <select
              id="priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isSubmitting}
            >
              {PRIORITY_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-slate-700 mb-1.5">
              Description (optional)
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add any notes or details..."
              rows={3}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              disabled={isSubmitting}
            />
          </div>

          {/* Authority Core Rule */}
          <div>
            <button
              type="button"
              onClick={() => setShowRuleSelector(!showRuleSelector)}
              disabled={isSubmitting}
              className="flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-blue-600 transition-colors"
            >
              <Scale className="w-4 h-4" />
              <span>Apply Rule from Database</span>
              {showRuleSelector ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>

            {selectedRule && !showRuleSelector && (
              <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-900">{selectedRule.rule_name}</p>
                    <p className="text-xs text-blue-700">{selectedRule.citation || selectedRule.rule_code}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedRule(null)}
                    className="p-1 text-blue-400 hover:text-blue-600 rounded"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {showRuleSelector && (
              <div className="mt-2">
                <RuleSelector
                  onSelect={handleRuleSelect}
                  onCancel={() => setShowRuleSelector(false)}
                  selectedRuleId={selectedRule?.id}
                />
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
            <AlertCircle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700">
              This will create a manual deadline that won't auto-update. For deadline chains, use Add Event instead.
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !title.trim() || !date}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating...' : 'Create Deadline'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
