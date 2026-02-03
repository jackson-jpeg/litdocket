'use client';

/**
 * UnifiedAddEventModal - Single entry point for adding events
 *
 * Combines three modes:
 * 1. Quick Add - Manual deadline with optional rule citation
 * 2. Apply Rule - Search Authority Core database and apply single rule
 * 3. Rule Chain - Apply rule template to generate full deadline chain
 *
 * Replaces: SimpleDeadlineModal + AddTriggerModal + duplicate UI
 */

import { useState, useEffect, useMemo } from 'react';
import {
  X,
  Calendar,
  Zap,
  Scale,
  ChevronRight,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Gavel,
  Clock,
  Info,
  Plus,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';
import { deadlineEvents } from '@/lib/eventBus';
import RuleSelector from '@/components/authority-core/RuleSelector';
import type { AuthorityRule } from '@/types';
import type { AddEventTab } from '@/hooks/useCasePageModals';

interface UnifiedAddEventModalProps {
  isOpen: boolean;
  caseId: string;
  jurisdiction: string;
  courtType: string;
  onClose: () => void;
  onSuccess: () => void;
  initialTab?: AddEventTab;
}

interface RuleTemplate {
  rule_id: string;
  name: string;
  description: string;
  jurisdiction: string;
  court_type: string;
  trigger_type: string;
  citation: string;
  num_dependent_deadlines: number;
}

// Priority options for quick add
const PRIORITY_OPTIONS = [
  { value: 'fatal', label: 'Fatal', color: 'text-red-600', description: 'Jurisdictional - missing = dismissal' },
  { value: 'critical', label: 'Critical', color: 'text-orange-600', description: 'Court-ordered deadlines' },
  { value: 'important', label: 'Important', color: 'text-amber-600', description: 'Procedural with consequences' },
  { value: 'standard', label: 'Standard', color: 'text-blue-600', description: 'Best practice deadlines' },
  { value: 'informational', label: 'Informational', color: 'text-slate-500', description: 'Internal reminders' },
];

// Trigger type icons and labels
const TRIGGER_TYPE_ICONS: Record<string, React.ReactNode> = {
  trial_date: <Gavel className="w-5 h-5" />,
  complaint_served: <FileText className="w-5 h-5" />,
  motion_filed: <Scale className="w-5 h-5" />,
  order_entered: <FileText className="w-5 h-5" />,
  hearing_scheduled: <Calendar className="w-5 h-5" />,
  discovery_commenced: <FileText className="w-5 h-5" />,
  case_filed: <FileText className="w-5 h-5" />,
  appeal_filed: <Scale className="w-5 h-5" />,
  pretrial_conference: <Calendar className="w-5 h-5" />,
};

const TRIGGER_TYPE_LABELS: Record<string, string> = {
  trial_date: 'Trial Date',
  complaint_served: 'Complaint Served',
  motion_filed: 'Motion Filed/Served',
  order_entered: 'Order/Judgment Entered',
  hearing_scheduled: 'Hearing Scheduled',
  discovery_commenced: 'Discovery Served',
  case_filed: 'Case Filed',
  appeal_filed: 'Appeal Filed',
  pretrial_conference: 'Pretrial Conference',
  discovery_deadline: 'Discovery Cutoff',
};

export default function UnifiedAddEventModal({
  isOpen,
  caseId,
  jurisdiction,
  courtType,
  onClose,
  onSuccess,
  initialTab = 'quick',
}: UnifiedAddEventModalProps) {
  const { showSuccess, showError } = useToast();

  // Tab state
  const [activeTab, setActiveTab] = useState<AddEventTab>(initialTab);

  // Quick Add state
  const [quickTitle, setQuickTitle] = useState('');
  const [quickDate, setQuickDate] = useState('');
  const [quickPriority, setQuickPriority] = useState('standard');
  const [quickDescription, setQuickDescription] = useState('');
  const [quickRule, setQuickRule] = useState<AuthorityRule | null>(null);
  const [showQuickRuleSelector, setShowQuickRuleSelector] = useState(false);
  const [quickSubmitting, setQuickSubmitting] = useState(false);

  // Apply Rule state
  const [selectedRule, setSelectedRule] = useState<AuthorityRule | null>(null);
  const [ruleDate, setRuleDate] = useState('');
  const [ruleSubmitting, setRuleSubmitting] = useState(false);

  // Trigger state
  const [triggerStep, setTriggerStep] = useState<'select' | 'configure' | 'preview'>('select');
  const [templates, setTemplates] = useState<RuleTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<RuleTemplate | null>(null);
  const [triggerDate, setTriggerDate] = useState('');
  const [serviceMethod, setServiceMethod] = useState<'email' | 'mail' | 'personal'>('email');
  const [triggerNotes, setTriggerNotes] = useState('');
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [triggerCreating, setTriggerCreating] = useState(false);

  // Reset state when modal closes or tab changes
  useEffect(() => {
    if (!isOpen) {
      setActiveTab(initialTab);
      resetQuickAdd();
      resetApplyRule();
      resetTrigger();
    }
  }, [isOpen, initialTab]);

  // Fetch templates when trigger tab is active
  useEffect(() => {
    if (isOpen && activeTab === 'trigger' && templates.length === 0) {
      fetchTemplates();
    }
  }, [isOpen, activeTab]);

  const fetchTemplates = async () => {
    setTemplatesLoading(true);
    try {
      const response = await apiClient.get('/api/v1/triggers/templates', {
        params: { jurisdiction, court_type: courtType },
      });
      setTemplates(response.data);
    } catch (err) {
      console.error('Failed to fetch templates:', err);
      showError('Failed to load rule templates');
    } finally {
      setTemplatesLoading(false);
    }
  };

  // Reset functions
  const resetQuickAdd = () => {
    setQuickTitle('');
    setQuickDate('');
    setQuickPriority('standard');
    setQuickDescription('');
    setQuickRule(null);
    setShowQuickRuleSelector(false);
    setQuickSubmitting(false);
  };

  const resetApplyRule = () => {
    setSelectedRule(null);
    setRuleDate('');
    setRuleSubmitting(false);
  };

  const resetTrigger = () => {
    setTriggerStep('select');
    setSelectedTemplate(null);
    setTriggerDate('');
    setServiceMethod('email');
    setTriggerNotes('');
    setTriggerCreating(false);
  };

  // Group templates by trigger type
  const groupedTemplates = useMemo(() => {
    const groups: Record<string, RuleTemplate[]> = {};
    templates.forEach(template => {
      const type = template.trigger_type;
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type].push(template);
    });
    return groups;
  }, [templates]);

  // Handle Quick Add submit
  const handleQuickSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!quickTitle.trim() || !quickDate) {
      showError('Please enter a title and date');
      return;
    }

    setQuickSubmitting(true);

    try {
      await apiClient.post('/api/v1/deadlines', {
        case_id: caseId,
        title: quickTitle.trim(),
        deadline_date: quickDate,
        priority: quickPriority,
        description: quickDescription.trim() || undefined,
        deadline_type: 'manual',
        party_role: 'both',
        action_required: 'Manual deadline',
        status: 'pending',
        applicable_rule: quickRule?.citation || quickRule?.rule_code || undefined,
        rule_citation: quickRule?.source_text || undefined,
        source_rule_id: quickRule?.id || undefined,
      });

      showSuccess('Deadline created successfully');
      deadlineEvents.created({ id: 'new', case_id: caseId });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      console.error('Failed to create deadline:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to create deadline';
      showError(errorMessage);
    } finally {
      setQuickSubmitting(false);
    }
  };

  // Handle Apply Rule submit
  const handleRuleSubmit = async () => {
    if (!selectedRule || !ruleDate) {
      showError('Please select a rule and enter a date');
      return;
    }

    setRuleSubmitting(true);

    try {
      // Create deadline(s) from rule
      const firstDeadline = selectedRule.deadlines[0];
      if (!firstDeadline) {
        showError('Selected rule has no deadline specifications');
        return;
      }

      // Calculate the deadline date based on rule
      const baseDate = new Date(ruleDate);
      const deadlineDate = new Date(baseDate);
      deadlineDate.setDate(deadlineDate.getDate() + firstDeadline.days_from_trigger);

      await apiClient.post('/api/v1/deadlines', {
        case_id: caseId,
        title: firstDeadline.title,
        deadline_date: deadlineDate.toISOString().split('T')[0],
        priority: firstDeadline.priority || 'standard',
        description: firstDeadline.description || undefined,
        deadline_type: 'calculated',
        party_role: firstDeadline.party_responsible || 'both',
        action_required: firstDeadline.title,
        status: 'pending',
        applicable_rule: selectedRule.citation || selectedRule.rule_code,
        rule_citation: selectedRule.source_text || undefined,
        source_rule_id: selectedRule.id,
        trigger_date: ruleDate,
        trigger_event: selectedRule.trigger_type,
        calculation_basis: `${firstDeadline.days_from_trigger} ${firstDeadline.calculation_method} from ${selectedRule.trigger_type}`,
        is_calculated: true,
      });

      showSuccess(`Deadline created from ${selectedRule.rule_name}`);
      deadlineEvents.created({ id: 'new', case_id: caseId });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      console.error('Failed to create deadline from rule:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to create deadline from rule';
      showError(errorMessage);
    } finally {
      setRuleSubmitting(false);
    }
  };

  // Handle Trigger create
  const handleTriggerCreate = async () => {
    if (!selectedTemplate || !triggerDate) return;

    setTriggerCreating(true);
    try {
      const response = await apiClient.post('/api/v1/triggers/create', {
        case_id: caseId,
        trigger_type: selectedTemplate.trigger_type,
        trigger_date: triggerDate,
        jurisdiction,
        court_type: courtType,
        service_method: serviceMethod,
        rule_template_id: selectedTemplate.rule_id,
        notes: triggerNotes || undefined,
      });

      const { dependent_deadlines_created } = response.data;
      showSuccess(`Rule applied - ${dependent_deadlines_created} deadlines created`);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      console.error('Failed to create trigger:', err);
      const errorDetail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      showError(errorDetail || 'Failed to apply rule');
    } finally {
      setTriggerCreating(false);
    }
  };

  const handleClose = () => {
    if (!quickSubmitting && !ruleSubmitting && !triggerCreating) {
      onClose();
    }
  };

  if (!isOpen) return null;

  const isSubmitting = quickSubmitting || ruleSubmitting || triggerCreating;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Plus className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-800">Add Event</h2>
                <p className="text-sm text-slate-600">
                  Create a deadline or apply a rule
                </p>
              </div>
            </div>
            <button
              onClick={handleClose}
              disabled={isSubmitting}
              className="p-1.5 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>

          {/* Tab Navigation */}
          <div className="flex border border-slate-200 rounded-lg bg-white p-1">
            <button
              onClick={() => setActiveTab('quick')}
              disabled={isSubmitting}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'quick'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Calendar className="w-4 h-4" />
              Quick Add
            </button>
            <button
              onClick={() => setActiveTab('rule')}
              disabled={isSubmitting}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'rule'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Scale className="w-4 h-4" />
              Apply Rule
            </button>
            <button
              onClick={() => setActiveTab('trigger')}
              disabled={isSubmitting}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'trigger'
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Zap className="w-4 h-4" />
              Rule Chain
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Quick Add Tab */}
          {activeTab === 'quick' && (
            <form onSubmit={handleQuickSubmit} className="space-y-5">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Deadline Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={quickTitle}
                  onChange={(e) => setQuickTitle(e.target.value)}
                  placeholder="e.g., File Motion to Compel"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                  autoFocus
                  disabled={quickSubmitting}
                />
              </div>

              {/* Date */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Due Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={quickDate}
                  onChange={(e) => setQuickDate(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                  disabled={quickSubmitting}
                />
              </div>

              {/* Priority */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Priority
                </label>
                <select
                  value={quickPriority}
                  onChange={(e) => setQuickPriority(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  disabled={quickSubmitting}
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
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Description (optional)
                </label>
                <textarea
                  value={quickDescription}
                  onChange={(e) => setQuickDescription(e.target.value)}
                  placeholder="Add any notes or details..."
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                  disabled={quickSubmitting}
                />
              </div>

              {/* Rule Selector (collapsed by default) */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowQuickRuleSelector(!showQuickRuleSelector)}
                  disabled={quickSubmitting}
                  className="flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-blue-600 transition-colors"
                >
                  <Scale className="w-4 h-4" />
                  <span>Attach Rule Citation (optional)</span>
                  {showQuickRuleSelector ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {quickRule && !showQuickRuleSelector && (
                  <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-blue-900">{quickRule.rule_name}</p>
                        <p className="text-xs text-blue-700">{quickRule.citation || quickRule.rule_code}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setQuickRule(null)}
                        className="p-1 text-blue-400 hover:text-blue-600 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}

                {showQuickRuleSelector && (
                  <div className="mt-2">
                    <RuleSelector
                      onSelect={(rule) => {
                        setQuickRule(rule);
                        setShowQuickRuleSelector(false);
                        if (!quickTitle.trim() && rule.deadlines?.[0]?.title) {
                          setQuickTitle(rule.deadlines[0].title);
                        }
                      }}
                      onCancel={() => setShowQuickRuleSelector(false)}
                      selectedRuleId={quickRule?.id}
                    />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
                <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-blue-700">
                  This creates a manual deadline. For automatic deadline chains based on court rules, use the &quot;Rule Chain&quot; tab.
                </p>
              </div>
            </form>
          )}

          {/* Apply Rule Tab */}
          {activeTab === 'rule' && (
            <div className="space-y-5">
              {/* Rule Selector */}
              {!selectedRule ? (
                <RuleSelector
                  jurisdictionId={jurisdiction}
                  onSelect={setSelectedRule}
                />
              ) : (
                <>
                  {/* Selected Rule */}
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-blue-900">{selectedRule.rule_name}</p>
                        <p className="text-sm text-blue-700">{selectedRule.citation || selectedRule.rule_code}</p>
                        <p className="text-sm text-blue-600 mt-1">
                          {selectedRule.deadlines.length} deadline(s) defined
                        </p>
                      </div>
                      <button
                        onClick={() => setSelectedRule(null)}
                        className="p-1 text-blue-400 hover:text-blue-600 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Base Date */}
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
                      Base Date (for calculation) <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="date"
                      value={ruleDate}
                      onChange={(e) => setRuleDate(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      required
                      disabled={ruleSubmitting}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      The deadline will be calculated from this date per the rule
                    </p>
                  </div>

                  {/* Deadline Preview */}
                  {selectedRule.deadlines.length > 0 && ruleDate && (
                    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                      <h4 className="text-sm font-medium text-slate-700 mb-2">
                        Deadline Preview
                      </h4>
                      <div className="space-y-2">
                        {selectedRule.deadlines.slice(0, 1).map((deadline, idx) => {
                          const baseDate = new Date(ruleDate);
                          const deadlineDate = new Date(baseDate);
                          deadlineDate.setDate(deadlineDate.getDate() + deadline.days_from_trigger);

                          return (
                            <div
                              key={idx}
                              className="flex items-center justify-between bg-white rounded-lg p-3 border border-slate-200"
                            >
                              <div>
                                <p className="font-medium text-slate-800">{deadline.title}</p>
                                <p className="text-sm text-slate-500">
                                  {deadline.days_from_trigger > 0 ? '+' : ''}{deadline.days_from_trigger} {deadline.calculation_method}
                                </p>
                              </div>
                              <div className="text-right">
                                <p className="font-medium text-slate-800">
                                  {deadlineDate.toLocaleDateString()}
                                </p>
                                <span className={`text-xs px-2 py-0.5 rounded-full ${
                                  deadline.priority === 'fatal' ? 'bg-red-100 text-red-700' :
                                  deadline.priority === 'critical' ? 'bg-orange-100 text-orange-700' :
                                  deadline.priority === 'important' ? 'bg-amber-100 text-amber-700' :
                                  deadline.priority === 'standard' ? 'bg-blue-100 text-blue-700' :
                                  'bg-slate-100 text-slate-600'
                                }`}>
                                  {deadline.priority}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* From Trigger Tab */}
          {activeTab === 'trigger' && (
            <div className="space-y-4">
              {/* Step 1: Select Template */}
              {triggerStep === 'select' && (
                <>
                  {templatesLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
                    </div>
                  ) : Object.keys(groupedTemplates).length === 0 ? (
                    <div className="text-center py-12">
                      <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-3" />
                      <p className="text-slate-600">
                        No rule templates available for {jurisdiction.replace('_', ' ')} {courtType}
                      </p>
                    </div>
                  ) : (
                    Object.entries(groupedTemplates).map(([triggerType, typeTemplates]) => (
                      <div key={triggerType}>
                        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                          {TRIGGER_TYPE_ICONS[triggerType] || <Clock className="w-4 h-4" />}
                          {TRIGGER_TYPE_LABELS[triggerType] || triggerType}
                        </h3>
                        <div className="space-y-2">
                          {typeTemplates.map((template) => (
                            <button
                              key={template.rule_id}
                              onClick={() => {
                                setSelectedTemplate(template);
                                setTriggerStep('configure');
                              }}
                              className="w-full p-4 border border-slate-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors text-left group"
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <div className="font-medium text-slate-800 group-hover:text-purple-700">
                                    {template.name}
                                  </div>
                                  <div className="text-sm text-slate-500 mt-0.5">
                                    {template.description}
                                  </div>
                                  <div className="text-xs text-slate-400 mt-1">
                                    {template.citation}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="px-2 py-1 bg-purple-100 text-purple-700 text-sm font-medium rounded-full">
                                    {template.num_dependent_deadlines} deadlines
                                  </span>
                                  <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-purple-500" />
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </>
              )}

              {/* Step 2: Configure */}
              {triggerStep === 'configure' && selectedTemplate && (
                <div className="space-y-6">
                  {/* Template Summary */}
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-purple-100 rounded-lg">
                        {TRIGGER_TYPE_ICONS[selectedTemplate.trigger_type] || <Zap className="w-5 h-5 text-purple-600" />}
                      </div>
                      <div>
                        <div className="font-medium text-slate-800">{selectedTemplate.name}</div>
                        <div className="text-sm text-slate-500">{selectedTemplate.citation}</div>
                        <div className="text-sm text-purple-600 mt-1">
                          Will generate {selectedTemplate.num_dependent_deadlines} deadlines
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Event Date */}
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Event Date <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="date"
                      value={triggerDate}
                      onChange={(e) => setTriggerDate(e.target.value)}
                      className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      All dependent deadlines will be calculated from this date
                    </p>
                  </div>

                  {/* Service Method */}
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Service Method
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { value: 'email', label: 'Email/E-Filing', desc: 'No extra days' },
                        { value: 'mail', label: 'Mail', desc: jurisdiction === 'federal' ? '+3 days' : '+5 days' },
                        { value: 'personal', label: 'Personal/Hand', desc: 'No extra days' },
                      ].map((method) => (
                        <button
                          key={method.value}
                          type="button"
                          onClick={() => setServiceMethod(method.value as 'email' | 'mail' | 'personal')}
                          className={`p-3 border rounded-lg text-left transition-colors ${
                            serviceMethod === method.value
                              ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-200'
                              : 'border-slate-200 hover:border-slate-300'
                          }`}
                        >
                          <div className="font-medium text-sm text-slate-800">{method.label}</div>
                          <div className="text-xs text-slate-500">{method.desc}</div>
                        </button>
                      ))}
                    </div>
                    <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                      <Info className="w-3 h-3" />
                      {jurisdiction === 'federal'
                        ? 'FRCP 6(d): Mail/electronic service adds 3 days'
                        : 'Fla. R. Jud. Admin. 2.514(b): Mail adds 5 days; email adds 0 days'}
                    </p>
                  </div>

                  {/* Notes */}
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Notes (Optional)
                    </label>
                    <textarea
                      value={triggerNotes}
                      onChange={(e) => setTriggerNotes(e.target.value)}
                      placeholder="Add any notes about this event..."
                      rows={3}
                      className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
                    />
                  </div>
                </div>
              )}

              {/* Step 3: Preview */}
              {triggerStep === 'preview' && selectedTemplate && (
                <div className="space-y-4">
                  {/* Summary */}
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center gap-2 text-green-700">
                      <CheckCircle2 className="w-5 h-5" />
                      <span className="font-medium">
                        Ready to create {selectedTemplate.num_dependent_deadlines} deadlines
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-green-600">
                      Event: {TRIGGER_TYPE_LABELS[selectedTemplate.trigger_type]} on{' '}
                      {new Date(triggerDate).toLocaleDateString('en-US', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </div>
                  </div>

                  {/* What happens next */}
                  <div className="space-y-3">
                    <h4 className="font-medium text-slate-700">What happens next:</h4>
                    <ul className="space-y-2 text-sm text-slate-600">
                      <li className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span>
                          <strong>{selectedTemplate.num_dependent_deadlines} deadlines</strong> will be
                          created automatically based on {selectedTemplate.citation}
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span>
                          Each deadline includes <strong>full rule citations</strong> and calculation
                          basis for legal defensibility
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span>
                          <strong>Weekend/holiday adjustments</strong> applied automatically per
                          {jurisdiction === 'federal' ? ' FRCP 6(a)' : ' Fla. R. Jud. Admin. 2.514(a)'}
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span>
                          If you change the event date later, all <strong>dependent deadlines
                          automatically recalculate</strong>
                        </span>
                      </li>
                    </ul>
                  </div>

                  {/* Service method note */}
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
                    <div className="font-medium text-blue-800">Service Method: {serviceMethod}</div>
                    <div className="text-blue-600 mt-1">
                      {serviceMethod === 'mail'
                        ? jurisdiction === 'federal'
                          ? 'Response deadlines will include +3 days per FRCP 6(d)'
                          : 'Response deadlines will include +5 days per Fla. R. Jud. Admin. 2.514(b)'
                        : 'No additional service days added'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          {activeTab === 'quick' && (
            <>
              <button
                onClick={handleClose}
                disabled={quickSubmitting}
                className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleQuickSubmit}
                disabled={quickSubmitting || !quickTitle.trim() || !quickDate}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {quickSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Calendar className="w-4 h-4" />
                    Create Deadline
                  </>
                )}
              </button>
            </>
          )}

          {activeTab === 'rule' && (
            <>
              <button
                onClick={() => {
                  if (selectedRule) {
                    setSelectedRule(null);
                  } else {
                    handleClose();
                  }
                }}
                disabled={ruleSubmitting}
                className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
              >
                {selectedRule ? 'Back' : 'Cancel'}
              </button>
              {selectedRule && (
                <button
                  onClick={handleRuleSubmit}
                  disabled={ruleSubmitting || !ruleDate}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {ruleSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Scale className="w-4 h-4" />
                      Apply Rule
                    </>
                  )}
                </button>
              )}
            </>
          )}

          {activeTab === 'trigger' && (
            <>
              <button
                onClick={() => {
                  if (triggerStep === 'configure') setTriggerStep('select');
                  else if (triggerStep === 'preview') setTriggerStep('configure');
                  else handleClose();
                }}
                disabled={triggerCreating}
                className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
              >
                {triggerStep === 'select' ? 'Cancel' : 'Back'}
              </button>

              {triggerStep === 'select' && (
                <div className="text-sm text-slate-500">
                  Select a rule to continue
                </div>
              )}

              {triggerStep === 'configure' && (
                <button
                  onClick={() => setTriggerStep('preview')}
                  disabled={!triggerDate}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  Preview Deadlines
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}

              {triggerStep === 'preview' && (
                <button
                  onClick={handleTriggerCreate}
                  disabled={triggerCreating}
                  className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {triggerCreating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4" />
                      Create {selectedTemplate?.num_dependent_deadlines} Deadlines
                    </>
                  )}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
