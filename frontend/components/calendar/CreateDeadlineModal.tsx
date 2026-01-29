'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Calendar, Plus, AlertCircle, Scale, ChevronDown, ChevronUp } from 'lucide-react';
import { CaseInfo, CreateDeadlineData } from '@/hooks/useCalendarDeadlines';
import RuleSelector from '@/components/authority-core/RuleSelector';
import type { AuthorityRule } from '@/types';

interface CreateDeadlineModalProps {
  isOpen: boolean;
  initialDate: Date | null;
  cases: CaseInfo[];
  onClose: () => void;
  onCreate: (data: CreateDeadlineData) => Promise<any>;
}

export default function CreateDeadlineModal({
  isOpen,
  initialDate,
  cases,
  onClose,
  onCreate,
}: CreateDeadlineModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [caseId, setCaseId] = useState('');
  const [priority, setPriority] = useState('standard');
  const [deadlineType, setDeadlineType] = useState('');
  const [deadlineDate, setDeadlineDate] = useState('');
  const [partyRole, setPartyRole] = useState('');
  const [applicableRule, setApplicableRule] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [showRuleSelector, setShowRuleSelector] = useState(false);
  const [selectedRule, setSelectedRule] = useState<AuthorityRule | null>(null);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setTitle('');
      setDescription('');
      setCaseId(cases.length === 1 ? cases[0].id : '');
      setPriority('standard');
      setDeadlineType('');
      setPartyRole('');
      setApplicableRule('');
      setError('');
      setShowRuleSelector(false);
      setSelectedRule(null);

      if (initialDate) {
        setDeadlineDate(initialDate.toISOString().split('T')[0]);
      } else {
        setDeadlineDate(new Date().toISOString().split('T')[0]);
      }
    }
  }, [isOpen, initialDate, cases]);

  const handleRuleSelect = (rule: AuthorityRule) => {
    setSelectedRule(rule);
    setShowRuleSelector(false);
    setApplicableRule(rule.citation || rule.rule_code);
    // Auto-fill title if empty and rule has deadlines
    if (!title.trim() && rule.deadlines?.[0]?.title) {
      setTitle(rule.deadlines[0].title);
    }
  };

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    if (!caseId) {
      setError('Please select a case');
      return;
    }
    if (!deadlineDate) {
      setError('Deadline date is required');
      return;
    }

    setCreating(true);
    try {
      const data: CreateDeadlineData & { source_rule_id?: string; rule_citation?: string } = {
        case_id: caseId,
        title: title.trim(),
        deadline_date: deadlineDate,
        description: description.trim() || undefined,
        priority,
        deadline_type: deadlineType || undefined,
        party_role: partyRole.trim() || undefined,
        applicable_rule: applicableRule.trim() || undefined,
        // Authority Core fields
        source_rule_id: selectedRule?.id || undefined,
        rule_citation: selectedRule?.source_text || undefined,
      };

      const result = await onCreate(data);
      if (result) {
        onClose();
      } else {
        setError('Failed to create deadline. Please try again.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create deadline');
    } finally {
      setCreating(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-slate-800">New Deadline</h2>
            </div>
            <button
              onClick={onClose}
              disabled={creating}
              className="p-1 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4 overflow-y-auto max-h-[70vh]">
          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Case Selection */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Case <span className="text-red-500">*</span>
            </label>
            <select
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            >
              <option value="">Select a case...</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.case_number} - {c.title}
                </option>
              ))}
            </select>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., File Motion for Summary Judgment"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
              maxLength={500}
            />
          </div>

          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Deadline Date <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type="date"
                value={deadlineDate}
                onChange={(e) => setDeadlineDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="informational">Informational</option>
              <option value="standard">Standard</option>
              <option value="important">Important</option>
              <option value="critical">Critical</option>
              <option value="fatal">Fatal (Case-dispositive)</option>
            </select>
          </div>

          {/* Deadline Type */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
            <select
              value={deadlineType}
              onChange={(e) => setDeadlineType(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select type...</option>
              <option value="filing">Filing</option>
              <option value="response">Response</option>
              <option value="hearing">Hearing</option>
              <option value="discovery">Discovery</option>
              <option value="deposition">Deposition</option>
              <option value="trial">Trial</option>
              <option value="appeal">Appeal</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Additional details about this deadline..."
              rows={3}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            />
          </div>

          {/* Party Role */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Responsible Party</label>
            <input
              type="text"
              value={partyRole}
              onChange={(e) => setPartyRole(e.target.value)}
              placeholder="e.g., Plaintiff, Defendant, All Parties"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Applicable Rule */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Applicable Rule</label>

            {/* Selected Rule Display */}
            {selectedRule ? (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg mb-2">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-900">{selectedRule.rule_name}</p>
                    <p className="text-xs text-blue-700">{selectedRule.citation || selectedRule.rule_code}</p>
                    <span className={`inline-flex mt-1 px-2 py-0.5 text-xs font-medium rounded-full ${
                      selectedRule.authority_tier === 'federal' ? 'bg-purple-100 text-purple-700' :
                      selectedRule.authority_tier === 'state' ? 'bg-blue-100 text-blue-700' :
                      selectedRule.authority_tier === 'local' ? 'bg-green-100 text-green-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {selectedRule.authority_tier}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedRule(null);
                      setApplicableRule('');
                    }}
                    className="p-1 text-blue-400 hover:text-blue-600 rounded"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <input
                type="text"
                value={applicableRule}
                onChange={(e) => setApplicableRule(e.target.value)}
                placeholder="e.g., Fla. R. Civ. P. 1.140(a)"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            )}

            {/* Rule Selector Toggle */}
            <button
              type="button"
              onClick={() => setShowRuleSelector(!showRuleSelector)}
              className="flex items-center gap-2 mt-2 text-sm text-blue-600 hover:text-blue-700 transition-colors"
            >
              <Scale className="w-4 h-4" />
              <span>{selectedRule ? 'Change rule' : 'Select from database'}</span>
              {showRuleSelector ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {/* Rule Selector Component */}
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
        </form>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={creating}
            className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={creating || !title.trim() || !caseId || !deadlineDate}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus className="w-4 h-4" />
            <span className="font-medium">{creating ? 'Creating...' : 'Create Deadline'}</span>
          </button>
        </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
