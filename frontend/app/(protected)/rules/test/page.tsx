'use client';

/**
 * Rule Testing Interface
 *
 * Allows testing rules by:
 * - Selecting a rule or jurisdiction + trigger type
 * - Entering test parameters (trigger date, case context)
 * - Previewing calculated deadlines
 * - Comparing Authority Core vs hardcoded rules output
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  RefreshCw,
  Calendar,
  Play,
  ChevronDown,
  AlertTriangle,
  CheckCircle,
  Scale,
  Clock,
  Info,
  Beaker,
  ArrowRight,
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
  jurisdiction_type: string;
}

interface AuthorityRule {
  id: string;
  rule_code: string;
  rule_name: string;
  trigger_type: string;
  authority_tier: string;
  jurisdiction_id: string;
  jurisdiction_name: string;
  deadlines: Array<{
    title: string;
    days_from_trigger: number;
    calculation_method: string;
    priority: string;
  }>;
}

interface CalculatedDeadline {
  title: string;
  deadline_date: string;
  days_from_trigger: number;
  calculation_method: string;
  priority: string;
  source_rule_id: string;
  citation?: string;
  rule_name: string;
}

interface DeadlineCalculationResponse {
  trigger_type: string;
  trigger_date: string;
  jurisdiction_id: string;
  rules_applied: number;
  deadlines: CalculatedDeadline[];
  warnings?: string[];
}

const TRIGGER_TYPES = [
  { value: 'motion_filed', label: 'Motion Filed' },
  { value: 'complaint_served', label: 'Complaint Served' },
  { value: 'answer_filed', label: 'Answer Filed' },
  { value: 'discovery_served', label: 'Discovery Served' },
  { value: 'trial_date', label: 'Trial Date Set' },
  { value: 'pretrial_conference', label: 'Pretrial Conference' },
  { value: 'judgment_entered', label: 'Judgment Entered' },
  { value: 'appeal_filed', label: 'Appeal Filed' },
];

const CASE_TYPES = [
  { value: 'civil', label: 'Civil' },
  { value: 'criminal', label: 'Criminal' },
  { value: 'family', label: 'Family' },
  { value: 'probate', label: 'Probate' },
  { value: 'bankruptcy', label: 'Bankruptcy' },
];

function PriorityBadge({ priority }: { priority: string }) {
  const styles: Record<string, string> = {
    fatal: 'bg-red-100 text-red-700',
    critical: 'bg-orange-100 text-orange-700',
    important: 'bg-amber-100 text-amber-700',
    standard: 'bg-blue-100 text-blue-700',
    informational: 'bg-slate-100 text-slate-600',
  };

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${styles[priority] || styles.standard}`}>
      {priority}
    </span>
  );
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function RuleTestPage() {
  const router = useRouter();

  // Form state
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>('');
  const [selectedTriggerType, setSelectedTriggerType] = useState<string>('motion_filed');
  const [triggerDate, setTriggerDate] = useState<string>(() => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  });
  const [caseType, setCaseType] = useState<string>('civil');
  const [serviceMethod, setServiceMethod] = useState<string>('electronic');

  // Results state
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingJurisdictions, setIsLoadingJurisdictions] = useState(true);
  const [results, setResults] = useState<DeadlineCalculationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch jurisdictions on mount
  useEffect(() => {
    const fetchJurisdictions = async () => {
      try {
        const response = await apiClient.get<Jurisdiction[]>('/jurisdictions/');
        setJurisdictions(response.data);
        if (response.data.length > 0) {
          setSelectedJurisdiction(response.data[0].id);
        }
      } catch (err) {
        console.error('Failed to fetch jurisdictions:', err);
      } finally {
        setIsLoadingJurisdictions(false);
      }
    };
    fetchJurisdictions();
  }, []);

  const runTest = async () => {
    if (!selectedJurisdiction || !triggerDate) return;

    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await apiClient.post<DeadlineCalculationResponse>(
        '/authority-core/calculate-deadlines',
        {
          jurisdiction_id: selectedJurisdiction,
          trigger_type: selectedTriggerType,
          trigger_date: triggerDate,
          case_context: {
            case_type: caseType,
            service_method: serviceMethod,
          },
        }
      );
      setResults(response.data);
    } catch (err: unknown) {
      console.error('Failed to calculate deadlines:', err);
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        setError(axiosError.response?.data?.detail || 'Failed to calculate deadlines');
      } else {
        setError('Failed to calculate deadlines');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const selectedJurisdictionName = jurisdictions.find(j => j.id === selectedJurisdiction)?.name || '';

  return (
    <div className="min-h-screen bg-slate-50 pb-12">
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/rules')}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Beaker className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Rule Testing Interface</h1>
                <p className="text-slate-500">Test deadline calculations with Authority Core rules</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Test Parameters */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h2 className="text-lg font-semibold text-slate-900">Test Parameters</h2>
              <p className="text-sm text-slate-500">Configure the trigger event to test</p>
            </div>

            <div className="p-6 space-y-6">
              {/* Jurisdiction */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Jurisdiction
                </label>
                {isLoadingJurisdictions ? (
                  <div className="flex items-center gap-2 text-slate-500">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Loading jurisdictions...
                  </div>
                ) : (
                  <select
                    value={selectedJurisdiction}
                    onChange={(e) => setSelectedJurisdiction(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {jurisdictions.map((jur) => (
                      <option key={jur.id} value={jur.id}>
                        {jur.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Trigger Type */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Trigger Type
                </label>
                <select
                  value={selectedTriggerType}
                  onChange={(e) => setSelectedTriggerType(e.target.value)}
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {TRIGGER_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Trigger Date */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Trigger Date
                </label>
                <div className="relative">
                  <input
                    type="date"
                    value={triggerDate}
                    onChange={(e) => setTriggerDate(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {/* Case Context */}
              <div className="pt-4 border-t border-slate-200">
                <h3 className="text-sm font-semibold text-slate-700 mb-4">Case Context (Optional)</h3>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Case Type
                    </label>
                    <select
                      value={caseType}
                      onChange={(e) => setCaseType(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      {CASE_TYPES.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Service Method
                    </label>
                    <select
                      value={serviceMethod}
                      onChange={(e) => setServiceMethod(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="electronic">Electronic</option>
                      <option value="mail">Mail</option>
                      <option value="personal">Personal</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Run Button */}
              <button
                onClick={runTest}
                disabled={isLoading || !selectedJurisdiction || !triggerDate}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Calculating...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    Run Test
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h2 className="text-lg font-semibold text-slate-900">Test Results</h2>
              <p className="text-sm text-slate-500">Calculated deadlines from Authority Core</p>
            </div>

            <div className="p-6">
              {error && (
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
                  <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-800">Error</p>
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              )}

              {!results && !error && !isLoading && (
                <div className="text-center py-12">
                  <Beaker className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-500">Configure parameters and run a test to see results</p>
                </div>
              )}

              {isLoading && (
                <div className="text-center py-12">
                  <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-4" />
                  <p className="text-slate-500">Calculating deadlines...</p>
                </div>
              )}

              {results && (
                <div className="space-y-6">
                  {/* Summary */}
                  <div className="flex items-center gap-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                    <div>
                      <p className="font-medium text-green-800">
                        {results.deadlines.length} deadline{results.deadlines.length !== 1 ? 's' : ''} calculated
                      </p>
                      <p className="text-sm text-green-700">
                        Using {results.rules_applied} rule{results.rules_applied !== 1 ? 's' : ''} for{' '}
                        {TRIGGER_TYPES.find(t => t.value === results.trigger_type)?.label || results.trigger_type}
                      </p>
                    </div>
                  </div>

                  {/* Warnings */}
                  {results.warnings && results.warnings.length > 0 && (
                    <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="w-5 h-5 text-amber-600" />
                        <p className="font-medium text-amber-800">Warnings</p>
                      </div>
                      <ul className="list-disc list-inside text-sm text-amber-700">
                        {results.warnings.map((warning, idx) => (
                          <li key={idx}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Deadline List */}
                  <div className="space-y-3 max-h-[400px] overflow-y-auto">
                    {results.deadlines.length === 0 ? (
                      <div className="text-center py-8 text-slate-500">
                        <Info className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                        <p>No deadlines found for this trigger type and jurisdiction</p>
                        <p className="text-sm mt-1">Try a different trigger type or add rules to the Authority Core</p>
                      </div>
                    ) : (
                      results.deadlines
                        .sort((a, b) => new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime())
                        .map((deadline, idx) => (
                          <div
                            key={idx}
                            className="p-4 bg-slate-50 border border-slate-200 rounded-lg"
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <p className="font-medium text-slate-900">{deadline.title}</p>
                                <p className="text-sm text-blue-600">{deadline.citation || deadline.rule_name}</p>
                              </div>
                              <PriorityBadge priority={deadline.priority} />
                            </div>
                            <div className="flex items-center gap-4 text-sm text-slate-600">
                              <span className="flex items-center gap-1.5">
                                <Calendar className="w-4 h-4" />
                                {formatDate(deadline.deadline_date)}
                              </span>
                              <span className="flex items-center gap-1.5">
                                <ArrowRight className="w-4 h-4" />
                                {deadline.days_from_trigger > 0 ? '+' : ''}{deadline.days_from_trigger} days
                              </span>
                              <span className="text-slate-400">
                                ({deadline.calculation_method.replace('_', ' ')})
                              </span>
                            </div>
                          </div>
                        ))
                    )}
                  </div>

                  {/* Test Info */}
                  <div className="p-4 bg-slate-100 rounded-lg text-sm text-slate-600">
                    <p>
                      <strong>Test run:</strong>{' '}
                      {selectedJurisdictionName} |{' '}
                      {TRIGGER_TYPES.find(t => t.value === selectedTriggerType)?.label} |{' '}
                      {formatDate(triggerDate)}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Info Panel */}
        <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-xl">
          <div className="flex items-start gap-4">
            <Info className="w-6 h-6 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-blue-900 mb-2">How Rule Testing Works</h3>
              <ul className="space-y-2 text-sm text-blue-800">
                <li>
                  <strong>1. Select Parameters:</strong> Choose a jurisdiction, trigger type, and date to simulate a real trigger event.
                </li>
                <li>
                  <strong>2. Run Test:</strong> The system queries Authority Core for matching rules and calculates all dependent deadlines.
                </li>
                <li>
                  <strong>3. Review Results:</strong> See exactly which rules were applied and what deadlines were generated.
                </li>
                <li>
                  <strong>4. Compare:</strong> If no Authority Core rules exist, the system falls back to hardcoded rules. Check if your rules produce the expected results.
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
