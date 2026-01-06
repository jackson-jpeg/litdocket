'use client';

import { useState, useEffect } from 'react';
import { X, Calendar, Zap, AlertTriangle, Info } from 'lucide-react';
import apiClient from '@/lib/api-client';

interface TriggerModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  jurisdiction: string;
  courtType: string;
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

export default function TriggerModal({
  isOpen,
  onClose,
  caseId,
  jurisdiction,
  courtType,
  onSuccess
}: TriggerModalProps) {
  const [step, setStep] = useState(1);
  const [templates, setTemplates] = useState<RuleTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<RuleTemplate | null>(null);
  const [triggerDate, setTriggerDate] = useState('');
  const [serviceMethod, setServiceMethod] = useState('email');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchTemplates();
    }
  }, [isOpen, jurisdiction, courtType]);

  const fetchTemplates = async () => {
    try {
      const response = await apiClient.get(
        `/api/v1/triggers/templates?jurisdiction=${jurisdiction}&court_type=${courtType}`
      );
      setTemplates(response.data);
    } catch (err) {
      console.error('Failed to load templates:', err);
      setError('Failed to load rule templates');
    }
  };

  const handleCreate = async () => {
    if (!selectedTemplate || !triggerDate) {
      setError('Please select a template and trigger date');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await apiClient.post('/api/v1/triggers/create', {
        case_id: caseId,
        trigger_type: selectedTemplate.trigger_type,
        trigger_date: triggerDate,
        jurisdiction: jurisdiction || 'florida_state',
        court_type: courtType || 'civil',
        service_method: serviceMethod,
        rule_template_id: selectedTemplate.rule_id,
        notes: notes
      });

      onSuccess();
      handleClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create trigger event');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setStep(1);
    setSelectedTemplate(null);
    setTriggerDate('');
    setServiceMethod('email');
    setNotes('');
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Zap className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-800">Create Trigger Event</h2>
              <p className="text-sm text-slate-600">
                CompuLaw-style: Enter one date, generate all dependent deadlines
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-600" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Step Indicator */}
          <div className="flex items-center justify-center gap-4 mb-8">
            <div className={`flex items-center gap-2 ${step >= 1 ? 'text-purple-600' : 'text-slate-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-purple-600 text-white' : 'bg-slate-200'}`}>
                1
              </div>
              <span className="text-sm font-medium">Select Trigger</span>
            </div>
            <div className="w-12 h-0.5 bg-slate-200" />
            <div className={`flex items-center gap-2 ${step >= 2 ? 'text-purple-600' : 'text-slate-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-purple-600 text-white' : 'bg-slate-200'}`}>
                2
              </div>
              <span className="text-sm font-medium">Set Date</span>
            </div>
            <div className="w-12 h-0.5 bg-slate-200" />
            <div className={`flex items-center gap-2 ${step >= 3 ? 'text-purple-600' : 'text-slate-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 3 ? 'bg-purple-600 text-white' : 'bg-slate-200'}`}>
                3
              </div>
              <span className="text-sm font-medium">Review</span>
            </div>
          </div>

          {/* Step 1: Select Template */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">How Trigger Events Work</p>
                  <p>
                    Select a trigger event (like "Trial Date" or "Complaint Served"), enter the date,
                    and the system will automatically generate all dependent deadlines based on Florida
                    court rules. Magic! ✨
                  </p>
                </div>
              </div>

              <h3 className="font-semibold text-slate-800 mb-3">Available Trigger Events</h3>

              {templates.length === 0 ? (
                <p className="text-center text-slate-500 py-8">No rule templates available for this jurisdiction</p>
              ) : (
                <div className="space-y-3">
                  {templates.map((template) => (
                    <div
                      key={template.rule_id}
                      onClick={() => setSelectedTemplate(template)}
                      className={`
                        border-2 rounded-lg p-4 cursor-pointer transition-all
                        ${
                          selectedTemplate?.rule_id === template.rule_id
                            ? 'border-purple-500 bg-purple-50'
                            : 'border-slate-200 hover:border-purple-300 hover:bg-slate-50'
                        }
                      `}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-semibold text-slate-800 mb-1">{template.name}</h4>
                          <p className="text-sm text-slate-600 mb-2">{template.description}</p>
                          <div className="flex items-center gap-4 text-xs">
                            <span className="px-2 py-1 bg-slate-100 text-slate-700 rounded">
                              {template.citation}
                            </span>
                            <span className="text-slate-500">
                              Generates {template.num_dependent_deadlines} deadline{template.num_dependent_deadlines !== 1 ? 's' : ''}
                            </span>
                          </div>
                        </div>
                        {selectedTemplate?.rule_id === template.rule_id && (
                          <div className="flex-shrink-0 w-6 h-6 bg-purple-600 rounded-full flex items-center justify-center">
                            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 2: Set Date */}
          {step === 2 && selectedTemplate && (
            <div className="space-y-4">
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <p className="text-sm text-purple-800">
                  <span className="font-medium">Selected:</span> {selectedTemplate.name}
                </p>
                <p className="text-xs text-purple-600 mt-1">
                  Will generate {selectedTemplate.num_dependent_deadlines} dependent deadline{selectedTemplate.num_dependent_deadlines !== 1 ? 's' : ''}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Trigger Date *
                </label>
                <input
                  type="date"
                  value={triggerDate}
                  onChange={(e) => setTriggerDate(e.target.value)}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Service Method
                </label>
                <select
                  value={serviceMethod}
                  onChange={(e) => setServiceMethod(e.target.value)}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="email">Email / Electronic Service (+ 0 days)</option>
                  <option value="mail">U.S. Mail (+ 5 days FL / + 3 days Federal)</option>
                  <option value="personal">Personal Service (+ 0 days)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Notes (Optional)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add any notes about this trigger event..."
                  rows={3}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>
          )}

          {/* Step 3: Review */}
          {step === 3 && selectedTemplate && triggerDate && (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-green-800">
                    <p className="font-medium mb-1">Ready to Generate Deadlines</p>
                    <p>
                      This will create {selectedTemplate.num_dependent_deadlines} dependent deadline{selectedTemplate.num_dependent_deadlines !== 1 ? 's' : ''}
                      based on {selectedTemplate.name} rules.
                    </p>
                  </div>
                </div>
              </div>

              <div className="border border-slate-200 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">Trigger Event:</span>
                  <span className="text-sm text-slate-800 font-medium">{selectedTemplate.name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">Trigger Date:</span>
                  <span className="text-sm text-slate-800 font-medium">
                    {new Date(triggerDate).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">Service Method:</span>
                  <span className="text-sm text-slate-800 font-medium capitalize">{serviceMethod}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">Rule Citation:</span>
                  <span className="text-sm text-slate-800 font-medium">{selectedTemplate.citation}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">Deadlines to Generate:</span>
                  <span className="text-sm text-purple-600 font-bold">{selectedTemplate.num_dependent_deadlines}</span>
                </div>
              </div>

              {notes && (
                <div className="border border-slate-200 rounded-lg p-4">
                  <p className="text-sm font-medium text-slate-600 mb-2">Notes:</p>
                  <p className="text-sm text-slate-700">{notes}</p>
                </div>
              )}
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-200">
          <button
            onClick={step === 1 ? handleClose : () => setStep(step - 1)}
            className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            {step === 1 ? 'Cancel' : 'Back'}
          </button>
          <button
            onClick={() => {
              if (step === 3) {
                handleCreate();
              } else if (step === 2 && triggerDate) {
                setStep(3);
              } else if (step === 1 && selectedTemplate) {
                setStep(2);
              }
            }}
            disabled={
              loading ||
              (step === 1 && !selectedTemplate) ||
              (step === 2 && !triggerDate)
            }
            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {loading ? 'Creating...' : step === 3 ? 'Create Trigger' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}
