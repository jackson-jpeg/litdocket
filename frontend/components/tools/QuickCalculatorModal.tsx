'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Calculator,
  Calendar,
  Scale,
  AlertTriangle,
  Loader2,
  Info,
  ChevronDown,
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface QuickCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface TriggerTypeOption {
  value: string;
  name: string;
  friendly_name: string;
  description: string;
  category: string;
  generates_approx: number;
}

interface PreviewDeadline {
  title: string;
  description: string | null;
  deadline_date: string | null;
  priority: string;
  rule_citation: string | null;
  calculation_basis: string | null;
  party_role: string | null;
  action_required: string | null;
  source: string;
}

interface PreviewResponse {
  success: boolean;
  trigger_type: string;
  trigger_date: string;
  deadlines: PreviewDeadline[];
  source: string;
  authority_core_enabled: boolean;
}

const JURISDICTIONS = [
  { value: 'florida_state', label: 'Florida State' },
  { value: 'federal', label: 'Federal' },
  { value: 'california_state', label: 'California State' },
  { value: 'new_york_state', label: 'New York State' },
  { value: 'texas_state', label: 'Texas State' },
];

const COURT_TYPES = [
  { value: 'civil', label: 'Civil' },
  { value: 'criminal', label: 'Criminal' },
  { value: 'appellate', label: 'Appellate' },
  { value: 'family', label: 'Family' },
  { value: 'probate', label: 'Probate' },
];

const SERVICE_METHODS = [
  { value: 'email', label: 'E-Service (Email)' },
  { value: 'personal', label: 'Personal Service' },
  { value: 'mail', label: 'Mail Service' },
  { value: 'publication', label: 'Service by Publication' },
];

const priorityColors: Record<string, string> = {
  fatal: 'bg-red-100 text-red-700 border-red-200',
  critical: 'bg-orange-100 text-orange-700 border-orange-200',
  important: 'bg-amber-100 text-amber-700 border-amber-200',
  standard: 'bg-blue-100 text-blue-700 border-blue-200',
  informational: 'bg-slate-100 text-slate-600 border-slate-200',
};

export default function QuickCalculatorModal({ isOpen, onClose }: QuickCalculatorModalProps) {
  // Form state
  const [jurisdiction, setJurisdiction] = useState('florida_state');
  const [courtType, setCourtType] = useState('civil');
  const [triggerType, setTriggerType] = useState('');
  const [triggerDate, setTriggerDate] = useState('');
  const [serviceMethod, setServiceMethod] = useState('email');

  // Data state
  const [triggerTypes, setTriggerTypes] = useState<TriggerTypeOption[]>([]);
  const [loadingTypes, setLoadingTypes] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [results, setResults] = useState<PreviewDeadline[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch trigger types on mount
  useEffect(() => {
    if (!isOpen) return;

    const fetchTriggerTypes = async () => {
      setLoadingTypes(true);
      try {
        const response = await apiClient.get('/api/v1/triggers/types');
        if (response.data.trigger_types) {
          setTriggerTypes(response.data.trigger_types);
          // Set default trigger type
          if (response.data.trigger_types.length > 0 && !triggerType) {
            setTriggerType(response.data.trigger_types[0].value);
          }
        }
      } catch (err) {
        console.error('Failed to fetch trigger types:', err);
        setError('Failed to load trigger types');
      } finally {
        setLoadingTypes(false);
      }
    };

    fetchTriggerTypes();
  }, [isOpen]);

  // Set default date to today
  useEffect(() => {
    if (isOpen && !triggerDate) {
      const today = new Date().toISOString().split('T')[0];
      setTriggerDate(today);
    }
  }, [isOpen, triggerDate]);

  // Reset state on close
  useEffect(() => {
    if (!isOpen) {
      setResults(null);
      setError(null);
    }
  }, [isOpen]);

  const handleCalculate = async () => {
    if (!triggerType || !triggerDate) {
      setError('Please select a trigger type and date');
      return;
    }

    setCalculating(true);
    setError(null);
    setResults(null);

    try {
      const response = await apiClient.post<PreviewResponse>('/api/v1/triggers/preview', {
        trigger_type: triggerType,
        trigger_date: triggerDate,
        jurisdiction,
        court_type: courtType,
        service_method: serviceMethod,
      });

      if (response.data.success) {
        setResults(response.data.deadlines);
      } else {
        setError('Failed to calculate deadlines');
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Failed to calculate deadlines');
    } finally {
      setCalculating(false);
    }
  };

  const selectedTriggerInfo = triggerTypes.find((t) => t.value === triggerType);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <Calculator className="w-5 h-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-slate-900">Quick Deadline Calculator</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-slate-600 rounded"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {/* Preview Notice */}
            <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg mb-4">
              <Info className="w-4 h-4 text-blue-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-blue-800">Preview Only</p>
                <p className="text-xs text-blue-700 mt-0.5">
                  Deadlines are calculated for preview. Create a case to save them.
                </p>
              </div>
            </div>

            {/* Form */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {/* Jurisdiction */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Jurisdiction
                </label>
                <div className="relative">
                  <select
                    value={jurisdiction}
                    onChange={(e) => setJurisdiction(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {JURISDICTIONS.map((j) => (
                      <option key={j.value} value={j.value}>
                        {j.label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {/* Court Type */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Court Type
                </label>
                <div className="relative">
                  <select
                    value={courtType}
                    onChange={(e) => setCourtType(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {COURT_TYPES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {/* Trigger Type */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Trigger Event
                </label>
                <div className="relative">
                  {loadingTypes ? (
                    <div className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                      <span className="text-slate-500 text-sm">Loading...</span>
                    </div>
                  ) : (
                    <select
                      value={triggerType}
                      onChange={(e) => setTriggerType(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {triggerTypes.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.friendly_name}
                        </option>
                      ))}
                    </select>
                  )}
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
                {selectedTriggerInfo && (
                  <p className="text-xs text-slate-500 mt-1">
                    {selectedTriggerInfo.description}
                  </p>
                )}
              </div>

              {/* Trigger Date */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Trigger Date
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="date"
                    value={triggerDate}
                    onChange={(e) => setTriggerDate(e.target.value)}
                    className="w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Service Method */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Service Method
                </label>
                <div className="relative">
                  <select
                    value={serviceMethod}
                    onChange={(e) => setServiceMethod(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {SERVICE_METHODS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Calculate Button */}
            <button
              onClick={handleCalculate}
              disabled={calculating || !triggerType || !triggerDate}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {calculating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Calculating...
                </>
              ) : (
                <>
                  <Scale className="w-4 h-4" />
                  Calculate Deadlines
                </>
              )}
            </button>

            {/* Error Display */}
            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Results */}
            {results && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-900">
                    Calculated Deadlines
                  </h3>
                  <span className="text-sm text-slate-500">
                    {results.length} deadline{results.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {results.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <Calendar className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                    <p className="font-medium">No Deadlines Found</p>
                    <p className="text-sm mt-1">
                      No rules apply for this trigger type and jurisdiction combination.
                    </p>
                  </div>
                ) : (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 border-b border-slate-200">
                        <tr>
                          <th className="text-left px-4 py-3 font-medium text-slate-600">
                            Deadline
                          </th>
                          <th className="text-left px-4 py-3 font-medium text-slate-600">
                            Date
                          </th>
                          <th className="text-left px-4 py-3 font-medium text-slate-600">
                            Priority
                          </th>
                          <th className="text-left px-4 py-3 font-medium text-slate-600">
                            Rule
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.map((deadline, idx) => (
                          <tr
                            key={idx}
                            className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                          >
                            <td className="px-4 py-3">
                              <p className="font-medium text-slate-900">{deadline.title}</p>
                              {deadline.action_required && (
                                <p className="text-xs text-slate-500 mt-0.5">
                                  {deadline.action_required}
                                </p>
                              )}
                            </td>
                            <td className="px-4 py-3 text-slate-600">
                              {deadline.deadline_date
                                ? new Date(deadline.deadline_date).toLocaleDateString('en-US', {
                                    month: 'short',
                                    day: 'numeric',
                                    year: 'numeric',
                                  })
                                : '-'}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-block px-2 py-0.5 text-xs font-medium rounded border ${
                                  priorityColors[deadline.priority] || priorityColors.standard
                                }`}
                              >
                                {deadline.priority?.toUpperCase() || 'STANDARD'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-slate-500 text-xs">
                              {deadline.rule_citation || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-2 p-4 border-t border-slate-200 bg-slate-50">
            <button
              onClick={onClose}
              className="px-4 py-2 text-slate-600 hover:text-slate-800 font-medium"
            >
              Close
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
