'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  X,
  Calendar,
  Zap,
  ChevronRight,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Scale,
  FileText,
  Gavel,
  Clock,
  Info,
} from 'lucide-react';
import axios from 'axios';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';

interface AddTriggerModalProps {
  isOpen: boolean;
  caseId: string;
  jurisdiction: string; // "florida_state" | "federal"
  courtType: string; // "civil" | "criminal" | "appellate"
  onClose: () => void;
  onSuccess: () => void;
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

interface PreviewDeadline {
  title: string;
  deadline_date: string;
  priority: string;
  rule_citation: string;
  days_from_trigger: number;
}

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

const PRIORITY_COLORS: Record<string, string> = {
  fatal: 'text-fatal bg-fatal/10 border border-fatal',
  critical: 'text-critical bg-critical/10 border border-critical',
  important: 'text-important bg-important/10 border border-important',
  standard: 'text-steel bg-steel/10 border border-steel',
  informational: 'text-ink-secondary bg-surface border border-ink/20',
};

export default function AddTriggerModal({
  isOpen,
  caseId,
  jurisdiction,
  courtType,
  onClose,
  onSuccess,
}: AddTriggerModalProps) {
  const { showSuccess, showError } = useToast();

  // State
  const [step, setStep] = useState<'select' | 'configure' | 'preview'>('select');
  const [templates, setTemplates] = useState<RuleTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<RuleTemplate | null>(null);
  const [triggerDate, setTriggerDate] = useState('');
  const [serviceMethod, setServiceMethod] = useState<'email' | 'mail' | 'personal'>('email');
  const [notes, setNotes] = useState('');
  const [previewDeadlines, setPreviewDeadlines] = useState<PreviewDeadline[]>([]);
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  // Fetch available templates
  useEffect(() => {
    if (!isOpen) return;

    const fetchTemplates = async () => {
      setLoading(true);
      try {
        const response = await apiClient.get('/api/v1/triggers/templates', {
          params: { jurisdiction, court_type: courtType },
        });
        setTemplates(response.data);
      } catch (err) {
        console.error('Failed to fetch templates:', err);
        showError('Failed to load trigger templates');
      } finally {
        setLoading(false);
      }
    };

    fetchTemplates();
  }, [isOpen, jurisdiction, courtType, showError]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setStep('select');
      setSelectedTemplate(null);
      setTriggerDate('');
      setServiceMethod('email');
      setNotes('');
      setPreviewDeadlines([]);
    }
  }, [isOpen]);

  // Generate preview when date changes
  useEffect(() => {
    if (!selectedTemplate || !triggerDate || step !== 'preview') return;

    const fetchPreview = async () => {
      setPreviewLoading(true);
      try {
        // Calculate preview locally based on template
        const triggerDateObj = new Date(triggerDate);
        const preview: PreviewDeadline[] = [];

        // For now, generate a simple preview based on the template info
        // In a real implementation, this would call the backend
        // We'll show a placeholder with the number of deadlines
        setPreviewDeadlines([]);
      } catch (err) {
        console.error('Failed to generate preview:', err);
      } finally {
        setPreviewLoading(false);
      }
    };

    fetchPreview();
  }, [selectedTemplate, triggerDate, serviceMethod, step]);

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

  // Handle template selection
  const handleSelectTemplate = (template: RuleTemplate) => {
    setSelectedTemplate(template);
    setStep('configure');
  };

  // Handle create trigger
  const handleCreate = async () => {
    if (!selectedTemplate || !triggerDate) return;

    setCreating(true);
    try {
      const response = await apiClient.post('/api/v1/triggers/create', {
        case_id: caseId,
        trigger_type: selectedTemplate.trigger_type,
        trigger_date: triggerDate,
        jurisdiction,
        court_type: courtType,
        service_method: serviceMethod,
        rule_template_id: selectedTemplate.rule_id,
        notes: notes || undefined,
      });

      const { dependent_deadlines_created } = response.data;
      showSuccess(`Created trigger with ${dependent_deadlines_created} deadlines`);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : err instanceof Error ? err.message : 'Failed to create trigger';
      showError(message);
    } finally {
      setCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-ink/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-paper border-2 border-ink shadow-modal max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-ink bg-surface">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-steel border border-ink">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-heading font-semibold text-ink">
                  {step === 'select' && 'Add Event'}
                  {step === 'configure' && `Configure: ${selectedTemplate?.name}`}
                  {step === 'preview' && 'Preview Deadlines'}
                </h2>
                <p className="text-sm text-ink-secondary">
                  {step === 'select' && 'Select an event type to auto-generate deadlines'}
                  {step === 'configure' && 'Set the date and service method'}
                  {step === 'preview' && `${selectedTemplate?.num_dependent_deadlines} deadlines will be created`}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              disabled={creating}
              className="p-1.5 hover:bg-surface transition-transform hover:translate-x-0.5"
            >
              <X className="w-5 h-5 text-ink-muted" />
            </button>
          </div>

          {/* Step Indicator */}
          <div className="flex items-center gap-2 mt-4">
            {['select', 'configure', 'preview'].map((s, i) => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-8 h-8 flex items-center justify-center text-sm font-mono font-medium border ${
                    step === s
                      ? 'bg-steel text-white border-ink'
                      : i < ['select', 'configure', 'preview'].indexOf(step)
                      ? 'bg-steel/20 text-steel border-steel'
                      : 'bg-surface text-ink-muted border-ink/20'
                  }`}
                >
                  {i + 1}
                </div>
                {i < 2 && (
                  <ChevronRight className="w-4 h-4 text-ink-muted mx-1" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Step 1: Select Template */}
          {step === 'select' && (
            <div className="space-y-4">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <span className="font-mono text-ink-secondary">LOADING<span className="animate-pulse">_</span></span>
                </div>
              ) : Object.keys(groupedTemplates).length === 0 ? (
                <div className="text-center py-12">
                  <AlertTriangle className="w-12 h-12 text-important mx-auto mb-3" />
                  <p className="text-ink-secondary">
                    No trigger templates available for {jurisdiction.replace('_', ' ')} {courtType}
                  </p>
                </div>
              ) : (
                Object.entries(groupedTemplates).map(([triggerType, templates]) => (
                  <div key={triggerType}>
                    <h3 className="text-sm font-mono font-semibold text-ink-secondary uppercase tracking-wide mb-2 flex items-center gap-2">
                      {TRIGGER_TYPE_ICONS[triggerType] || <Clock className="w-4 h-4" />}
                      {TRIGGER_TYPE_LABELS[triggerType] || triggerType}
                    </h3>
                    <div className="space-y-2">
                      {templates.map((template) => (
                        <button
                          key={template.rule_id}
                          onClick={() => handleSelectTemplate(template)}
                          className="w-full p-4 border border-ink/20 hover:border-steel hover:bg-surface transition-transform hover:translate-x-0.5 text-left group"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="font-medium text-ink group-hover:text-steel">
                                {template.name}
                              </div>
                              <div className="text-sm text-ink-secondary mt-0.5">
                                {template.description}
                              </div>
                              <div className="text-xs font-mono text-ink-muted mt-1">
                                {template.citation}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-1 bg-steel/10 text-steel text-sm font-mono font-medium border border-steel">
                                {template.num_dependent_deadlines} deadlines
                              </span>
                              <ChevronRight className="w-5 h-5 text-ink-muted group-hover:text-steel" />
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Step 2: Configure */}
          {step === 'configure' && selectedTemplate && (
            <div className="space-y-6">
              {/* Template Summary */}
              <div className="p-4 bg-surface border border-ink/20">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-steel/10 border border-steel">
                    {TRIGGER_TYPE_ICONS[selectedTemplate.trigger_type] || <Zap className="w-5 h-5 text-steel" />}
                  </div>
                  <div>
                    <div className="font-medium text-ink">{selectedTemplate.name}</div>
                    <div className="text-sm font-mono text-ink-secondary">{selectedTemplate.citation}</div>
                    <div className="text-sm font-mono text-steel mt-1">
                      Will generate {selectedTemplate.num_dependent_deadlines} deadlines
                    </div>
                  </div>
                </div>
              </div>

              {/* Trigger Date */}
              <div>
                <label className="block text-sm font-mono font-medium text-ink uppercase tracking-wide mb-2">
                  Trigger Date *
                </label>
                <input
                  type="date"
                  value={triggerDate}
                  onChange={(e) => setTriggerDate(e.target.value)}
                  className="w-full px-4 py-2.5 border border-ink/20 bg-paper focus:outline-none focus:border-ink font-mono"
                />
                <p className="text-xs text-ink-secondary mt-1">
                  All dependent deadlines will be calculated from this date
                </p>
              </div>

              {/* Service Method */}
              <div>
                <label className="block text-sm font-mono font-medium text-ink uppercase tracking-wide mb-2">
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
                      onClick={() => setServiceMethod(method.value as any)}
                      className={`p-3 border text-left transition-transform hover:translate-x-0.5 ${
                        serviceMethod === method.value
                          ? 'border-steel bg-steel/10 border-2'
                          : 'border-ink/20 hover:border-ink/40'
                      }`}
                    >
                      <div className="font-medium text-sm text-ink">{method.label}</div>
                      <div className="text-xs font-mono text-ink-secondary">{method.desc}</div>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-ink-secondary mt-2 flex items-center gap-1 font-mono">
                  <Info className="w-3 h-3" />
                  {jurisdiction === 'federal'
                    ? 'FRCP 6(d): Mail/electronic service adds 3 days'
                    : 'Fla. R. Jud. Admin. 2.514(b): Mail adds 5 days; email adds 0 days (since 2019)'}
                </p>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-mono font-medium text-ink uppercase tracking-wide mb-2">
                  Notes (Optional)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add any notes about this trigger event..."
                  rows={3}
                  className="w-full px-4 py-2.5 border border-ink/20 bg-paper focus:outline-none focus:border-ink resize-none"
                />
              </div>
            </div>
          )}

          {/* Step 3: Preview */}
          {step === 'preview' && selectedTemplate && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="p-4 bg-status-success/10 border border-status-success">
                <div className="flex items-center gap-2 text-status-success">
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="font-medium">
                    Ready to create {selectedTemplate.num_dependent_deadlines} deadlines
                  </span>
                </div>
                <div className="mt-2 text-sm font-mono text-ink-secondary">
                  Trigger: {TRIGGER_TYPE_LABELS[selectedTemplate.trigger_type]} on{' '}
                  {new Date(triggerDate).toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </div>
              </div>

              {/* Info about what will happen */}
              <div className="space-y-3">
                <h4 className="font-mono font-medium text-ink uppercase tracking-wide">What happens next:</h4>
                <ul className="space-y-2 text-sm text-ink-secondary">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-status-success mt-0.5 flex-shrink-0" />
                    <span>
                      <strong className="text-ink">{selectedTemplate.num_dependent_deadlines} deadlines</strong> will be
                      created automatically based on <span className="font-mono">{selectedTemplate.citation}</span>
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-status-success mt-0.5 flex-shrink-0" />
                    <span>
                      Each deadline includes <strong className="text-ink">full rule citations</strong> and calculation
                      basis for legal defensibility
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-status-success mt-0.5 flex-shrink-0" />
                    <span>
                      <strong className="text-ink">Weekend/holiday adjustments</strong> applied automatically per
                      <span className="font-mono">{jurisdiction === 'federal' ? ' FRCP 6(a)' : ' Fla. R. Jud. Admin. 2.514(a)'}</span>
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-status-success mt-0.5 flex-shrink-0" />
                    <span>
                      If you change the trigger date later, all <strong className="text-ink">dependent deadlines
                      automatically recalculate</strong>
                    </span>
                  </li>
                </ul>
              </div>

              {/* Service method note */}
              <div className="p-3 bg-steel/10 border border-steel/30 text-sm">
                <div className="font-mono font-medium text-ink">Service Method: {serviceMethod}</div>
                <div className="text-ink-secondary mt-1 font-mono">
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

        {/* Footer */}
        <div className="p-4 border-t border-ink bg-surface flex items-center justify-between">
          <button
            onClick={() => {
              if (step === 'configure') setStep('select');
              else if (step === 'preview') setStep('configure');
              else onClose();
            }}
            disabled={creating}
            className="btn-secondary"
          >
            {step === 'select' ? 'Cancel' : 'Back'}
          </button>

          {step === 'select' ? (
            <div className="text-sm font-mono text-ink-muted">
              Select an event type to continue
            </div>
          ) : step === 'configure' ? (
            <button
              onClick={() => setStep('preview')}
              disabled={!triggerDate}
              className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Preview Deadlines
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleCreate}
              disabled={creating}
              className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? (
                <>
                  <span className="font-mono">CREATING<span className="animate-pulse">_</span></span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Create {selectedTemplate?.num_dependent_deadlines} Deadlines
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
