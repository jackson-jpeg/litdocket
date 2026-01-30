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
  fatal: 'text-red-700 bg-red-100',
  critical: 'text-orange-700 bg-orange-100',
  important: 'text-amber-700 bg-amber-100',
  standard: 'text-blue-700 bg-blue-100',
  informational: 'text-slate-600 bg-slate-100',
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
    } catch (err: any) {
      showError(err.response?.data?.detail || 'Failed to create trigger');
    } finally {
      setCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-gradient-to-r from-purple-50 to-blue-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Zap className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-800">
                  {step === 'select' && 'Add Event'}
                  {step === 'configure' && `Configure: ${selectedTemplate?.name}`}
                  {step === 'preview' && 'Preview Deadlines'}
                </h2>
                <p className="text-sm text-slate-600">
                  {step === 'select' && 'Select an event type to auto-generate deadlines'}
                  {step === 'configure' && 'Set the date and service method'}
                  {step === 'preview' && `${selectedTemplate?.num_dependent_deadlines} deadlines will be created`}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              disabled={creating}
              className="p-1.5 rounded-lg hover:bg-slate-200 transition-colors"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>

          {/* Step Indicator */}
          <div className="flex items-center gap-2 mt-4">
            {['select', 'configure', 'preview'].map((s, i) => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    step === s
                      ? 'bg-purple-600 text-white'
                      : i < ['select', 'configure', 'preview'].indexOf(step)
                      ? 'bg-purple-200 text-purple-700'
                      : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {i + 1}
                </div>
                {i < 2 && (
                  <ChevronRight className="w-4 h-4 text-slate-400 mx-1" />
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
                  <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
                </div>
              ) : Object.keys(groupedTemplates).length === 0 ? (
                <div className="text-center py-12">
                  <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-3" />
                  <p className="text-slate-600">
                    No trigger templates available for {jurisdiction.replace('_', ' ')} {courtType}
                  </p>
                </div>
              ) : (
                Object.entries(groupedTemplates).map(([triggerType, templates]) => (
                  <div key={triggerType}>
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                      {TRIGGER_TYPE_ICONS[triggerType] || <Clock className="w-4 h-4" />}
                      {TRIGGER_TYPE_LABELS[triggerType] || triggerType}
                    </h3>
                    <div className="space-y-2">
                      {templates.map((template) => (
                        <button
                          key={template.rule_id}
                          onClick={() => handleSelectTemplate(template)}
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
            </div>
          )}

          {/* Step 2: Configure */}
          {step === 'configure' && selectedTemplate && (
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

              {/* Trigger Date */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Trigger Date *
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
                      onClick={() => setServiceMethod(method.value as any)}
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
                    : 'Fla. R. Jud. Admin. 2.514(b): Mail adds 5 days; email adds 0 days (since 2019)'}
                </p>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Notes (Optional)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add any notes about this trigger event..."
                  rows={3}
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
                />
              </div>
            </div>
          )}

          {/* Step 3: Preview */}
          {step === 'preview' && selectedTemplate && (
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
                      If you change the trigger date later, all <strong>dependent deadlines
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

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <button
            onClick={() => {
              if (step === 'configure') setStep('select');
              else if (step === 'preview') setStep('configure');
              else onClose();
            }}
            disabled={creating}
            className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
          >
            {step === 'select' ? 'Cancel' : 'Back'}
          </button>

          {step === 'select' ? (
            <div className="text-sm text-slate-500">
              Select an event type to continue
            </div>
          ) : step === 'configure' ? (
            <button
              onClick={() => setStep('preview')}
              disabled={!triggerDate}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              Preview Deadlines
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleCreate}
              disabled={creating}
              className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {creating ? (
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
        </div>
      </div>
    </div>
  );
}
