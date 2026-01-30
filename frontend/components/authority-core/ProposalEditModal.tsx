'use client';

/**
 * ProposalEditModal Component
 *
 * Allows editing rule proposals before approval.
 * Features:
 * - Edit rule name, citation, trigger type
 * - Add/remove/edit deadline specifications
 * - Adjust conditions and service extensions
 * - Preview changes before approval
 */

import { useState, useCallback } from 'react';
import {
  X,
  Plus,
  Trash2,
  Save,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Calendar,
  Clock,
  Scale,
} from 'lucide-react';
import { RuleProposal, DeadlineSpec, ServiceExtensions, RuleConditions } from '@/types';

interface ProposalEditModalProps {
  proposal: RuleProposal;
  onClose: () => void;
  onSave: (proposalId: string, modifications: ProposedRuleData) => Promise<void>;
}

interface ProposedRuleData {
  rule_code: string;
  rule_name: string;
  trigger_type: string;
  authority_tier: 'federal' | 'state' | 'local' | 'standing_order' | 'firm';
  citation?: string;
  deadlines: DeadlineSpec[];
  conditions?: RuleConditions;
  service_extensions?: ServiceExtensions;
}

const AUTHORITY_TIERS = [
  { value: 'federal', label: 'Federal' },
  { value: 'state', label: 'State' },
  { value: 'local', label: 'Local' },
  { value: 'standing_order', label: 'Standing Order' },
  { value: 'firm', label: 'Firm' },
];

const TRIGGER_TYPES = [
  { value: 'motion_filed', label: 'Motion Filed' },
  { value: 'complaint_served', label: 'Complaint Served' },
  { value: 'answer_filed', label: 'Answer Filed' },
  { value: 'discovery_served', label: 'Discovery Served' },
  { value: 'trial_date', label: 'Trial Date Set' },
  { value: 'pretrial_conference', label: 'Pretrial Conference' },
  { value: 'judgment_entered', label: 'Judgment Entered' },
  { value: 'appeal_filed', label: 'Appeal Filed' },
  { value: 'custom', label: 'Custom' },
];

const CALCULATION_METHODS = [
  { value: 'calendar_days', label: 'Calendar Days' },
  { value: 'business_days', label: 'Business Days' },
  { value: 'court_days', label: 'Court Days' },
];

const PRIORITIES = [
  { value: 'informational', label: 'Informational', color: 'bg-slate-100 text-slate-600' },
  { value: 'standard', label: 'Standard', color: 'bg-blue-100 text-blue-700' },
  { value: 'important', label: 'Important', color: 'bg-amber-100 text-amber-700' },
  { value: 'critical', label: 'Critical', color: 'bg-orange-100 text-orange-700' },
  { value: 'fatal', label: 'Fatal', color: 'bg-red-100 text-red-700' },
];

const PARTIES = [
  { value: 'plaintiff', label: 'Plaintiff' },
  { value: 'defendant', label: 'Defendant' },
  { value: 'both', label: 'Both Parties' },
  { value: 'court', label: 'Court' },
  { value: 'opposing', label: 'Opposing Party' },
];

function DeadlineEditor({
  deadline,
  index,
  onChange,
  onRemove,
}: {
  deadline: DeadlineSpec;
  index: number;
  onChange: (index: number, deadline: DeadlineSpec) => void;
  onRemove: (index: number) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const updateField = <K extends keyof DeadlineSpec>(field: K, value: DeadlineSpec[K]) => {
    onChange(index, { ...deadline, [field]: value });
  };

  const priorityStyle = PRIORITIES.find(p => p.value === deadline.priority)?.color || 'bg-slate-100';

  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
      {/* Collapsed Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="w-6 h-6 flex items-center justify-center bg-slate-100 text-slate-600 text-xs font-medium rounded">
            {index + 1}
          </span>
          <div>
            <p className="font-medium text-slate-900 text-sm">{deadline.title || 'Untitled Deadline'}</p>
            <p className="text-xs text-slate-500">
              {deadline.days_from_trigger > 0 ? '+' : ''}{deadline.days_from_trigger} {deadline.calculation_method}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${priorityStyle}`}>
            {deadline.priority}
          </span>
          {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </div>

      {/* Expanded Form */}
      {isExpanded && (
        <div className="p-4 border-t border-slate-200 bg-slate-50 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Deadline Title</label>
            <input
              type="text"
              value={deadline.title}
              onChange={(e) => updateField('title', e.target.value)}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="e.g., Response to Motion Due"
            />
          </div>

          {/* Days and Method Row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Days from Trigger</label>
              <input
                type="number"
                value={deadline.days_from_trigger}
                onChange={(e) => updateField('days_from_trigger', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Calculation Method</label>
              <select
                value={deadline.calculation_method}
                onChange={(e) => updateField('calculation_method', e.target.value as DeadlineSpec['calculation_method'])}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {CALCULATION_METHODS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Priority and Party Row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Priority</label>
              <select
                value={deadline.priority}
                onChange={(e) => updateField('priority', e.target.value as DeadlineSpec['priority'])}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {PRIORITIES.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Party Responsible</label>
              <select
                value={deadline.party_responsible || ''}
                onChange={(e) => updateField('party_responsible', e.target.value || undefined)}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Not specified</option>
                {PARTIES.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Description (optional)</label>
            <textarea
              value={deadline.description || ''}
              onChange={(e) => updateField('description', e.target.value || undefined)}
              rows={2}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              placeholder="Additional notes about this deadline..."
            />
          </div>

          {/* Remove Button */}
          <button
            onClick={() => onRemove(index)}
            className="flex items-center gap-1.5 text-sm text-red-600 hover:text-red-700 font-medium"
          >
            <Trash2 className="w-4 h-4" />
            Remove Deadline
          </button>
        </div>
      )}
    </div>
  );
}

export default function ProposalEditModal({ proposal, onClose, onSave }: ProposalEditModalProps) {
  const originalData = proposal.proposed_rule_data;

  const [ruleData, setRuleData] = useState<ProposedRuleData>({
    rule_code: originalData.rule_code,
    rule_name: originalData.rule_name,
    trigger_type: originalData.trigger_type,
    authority_tier: originalData.authority_tier as ProposedRuleData['authority_tier'],
    citation: originalData.citation,
    deadlines: [...originalData.deadlines],
    conditions: originalData.conditions ? { ...originalData.conditions } : undefined,
    service_extensions: originalData.service_extensions ? { ...originalData.service_extensions } : { mail: 3, electronic: 0, personal: 0 },
  });

  const [isSaving, setIsSaving] = useState(false);
  const [showConditions, setShowConditions] = useState(false);

  const updateDeadline = useCallback((index: number, deadline: DeadlineSpec) => {
    setRuleData(prev => ({
      ...prev,
      deadlines: prev.deadlines.map((d, i) => i === index ? deadline : d),
    }));
  }, []);

  const removeDeadline = useCallback((index: number) => {
    setRuleData(prev => ({
      ...prev,
      deadlines: prev.deadlines.filter((_, i) => i !== index),
    }));
  }, []);

  const addDeadline = useCallback(() => {
    const newDeadline: DeadlineSpec = {
      title: 'New Deadline',
      days_from_trigger: 14,
      calculation_method: 'calendar_days',
      priority: 'standard',
    };
    setRuleData(prev => ({
      ...prev,
      deadlines: [...prev.deadlines, newDeadline],
    }));
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(proposal.id, ruleData);
      onClose();
    } catch (err) {
      console.error('Failed to save modifications:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = JSON.stringify(ruleData) !== JSON.stringify({
    rule_code: originalData.rule_code,
    rule_name: originalData.rule_name,
    trigger_type: originalData.trigger_type,
    authority_tier: originalData.authority_tier,
    citation: originalData.citation,
    deadlines: originalData.deadlines,
    conditions: originalData.conditions,
    service_extensions: originalData.service_extensions || { mail: 3, electronic: 0, personal: 0 },
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-50 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-white border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Edit Proposal</h2>
            <p className="text-sm text-slate-500">Modify the rule before approval</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Basic Info */}
          <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">Rule Information</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Rule Code</label>
                <input
                  type="text"
                  value={ruleData.rule_code}
                  onChange={(e) => setRuleData(prev => ({ ...prev, rule_code: e.target.value }))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Citation</label>
                <input
                  type="text"
                  value={ruleData.citation || ''}
                  onChange={(e) => setRuleData(prev => ({ ...prev, citation: e.target.value || undefined }))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., S.D. Fla. L.R. 7.1(a)"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Rule Name</label>
              <input
                type="text"
                value={ruleData.rule_name}
                onChange={(e) => setRuleData(prev => ({ ...prev, rule_name: e.target.value }))}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Trigger Type</label>
                <select
                  value={ruleData.trigger_type}
                  onChange={(e) => setRuleData(prev => ({ ...prev, trigger_type: e.target.value }))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {TRIGGER_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Authority Tier</label>
                <select
                  value={ruleData.authority_tier}
                  onChange={(e) => setRuleData(prev => ({ ...prev, authority_tier: e.target.value as ProposedRuleData['authority_tier'] }))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {AUTHORITY_TIERS.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Deadlines */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">
                Deadlines ({ruleData.deadlines.length})
              </h3>
              <button
                onClick={addDeadline}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Deadline
              </button>
            </div>

            <div className="space-y-3">
              {ruleData.deadlines.map((deadline, index) => (
                <DeadlineEditor
                  key={index}
                  deadline={deadline}
                  index={index}
                  onChange={updateDeadline}
                  onRemove={removeDeadline}
                />
              ))}

              {ruleData.deadlines.length === 0 && (
                <div className="text-center py-8 text-slate-500 text-sm">
                  No deadlines defined. Click "Add Deadline" to create one.
                </div>
              )}
            </div>
          </div>

          {/* Service Extensions */}
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wide mb-4">
              Service Extensions
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Mail (+days)</label>
                <input
                  type="number"
                  value={ruleData.service_extensions?.mail || 0}
                  onChange={(e) => setRuleData(prev => ({
                    ...prev,
                    service_extensions: { ...prev.service_extensions!, mail: parseInt(e.target.value) || 0 }
                  }))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Electronic (+days)</label>
                <input
                  type="number"
                  value={ruleData.service_extensions?.electronic || 0}
                  onChange={(e) => setRuleData(prev => ({
                    ...prev,
                    service_extensions: { ...prev.service_extensions!, electronic: parseInt(e.target.value) || 0 }
                  }))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Personal (+days)</label>
                <input
                  type="number"
                  value={ruleData.service_extensions?.personal || 0}
                  onChange={(e) => setRuleData(prev => ({
                    ...prev,
                    service_extensions: { ...prev.service_extensions!, personal: parseInt(e.target.value) || 0 }
                  }))}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>

          {/* Warning for Changes */}
          {hasChanges && (
            <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-800">Unsaved Changes</p>
                <p className="text-sm text-amber-700">
                  You have made modifications to this proposal. Click "Save & Approve" to apply your changes.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-white border-t border-slate-200 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || ruleData.deadlines.length === 0}
            className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? (
              <>
                <Clock className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save & Approve
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
