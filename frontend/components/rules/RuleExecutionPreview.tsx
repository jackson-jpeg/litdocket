'use client';

import { useState } from 'react';
import { useRules } from '@/hooks/useRules';
import {
  Play,
  CheckCircle,
  AlertCircle,
  Calendar,
  Clock
} from 'lucide-react';

interface RuleExecutionPreviewProps {
  ruleTemplateId: string;
  caseId: string;
}

export default function RuleExecutionPreview({
  ruleTemplateId,
  caseId
}: RuleExecutionPreviewProps) {
  const { executeRule, loading } = useRules();
  const [result, setResult] = useState<any>(null);
  const [triggerData, setTriggerData] = useState({
    trial_date: '',
    trial_type: 'jury',
    service_method: 'personal'
  });

  const handlePreview = async () => {
    const response = await executeRule({
      rule_template_id: ruleTemplateId,
      case_id: caseId,
      trigger_data: triggerData,
      dry_run: true // Preview mode - don't save
    });

    if (response) {
      setResult(response);
    }
  };

  const priorityColors = {
    FATAL: 'bg-red-100 text-red-800 border-red-200',
    CRITICAL: 'bg-orange-100 text-orange-800 border-orange-200',
    IMPORTANT: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    STANDARD: 'bg-blue-100 text-blue-800 border-blue-200',
    INFORMATIONAL: 'bg-gray-100 text-gray-800 border-gray-200'
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">
        Test Rule Execution
      </h3>

      {/* Input Form */}
      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Trial Date *
          </label>
          <input
            type="date"
            value={triggerData.trial_date}
            onChange={(e) => setTriggerData({ ...triggerData, trial_date: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Trial Type
            </label>
            <select
              value={triggerData.trial_type}
              onChange={(e) => setTriggerData({ ...triggerData, trial_type: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="jury">Jury Trial</option>
              <option value="bench">Bench Trial</option>
              <option value="summary_judgment">Summary Judgment Hearing</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Service Method
            </label>
            <select
              value={triggerData.service_method}
              onChange={(e) => setTriggerData({ ...triggerData, service_method: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="personal">Personal Service</option>
              <option value="mail">Mail Service</option>
              <option value="email">Email Service</option>
            </select>
          </div>
        </div>

        <button
          onClick={handlePreview}
          disabled={loading || !triggerData.trial_date}
          className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
              Generating Preview...
            </>
          ) : (
            <>
              <Play className="h-5 w-5" />
              Preview Deadlines
            </>
          )}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="border-t border-gray-200 pt-6">
          {/* Summary */}
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 mb-6 border border-green-200">
            <div className="flex items-start gap-3">
              <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-green-900">
                  Success - {result.deadlines_created} deadlines generated
                </h4>
                <p className="text-sm text-green-700 mt-1">
                  Executed in {result.execution_time_ms}ms • Version {result.rule_version}
                </p>
              </div>
            </div>
          </div>

          {/* Errors */}
          {result.errors && result.errors.length > 0 && (
            <div className="bg-red-50 rounded-lg p-4 mb-6 border border-red-200">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-red-900">Errors</h4>
                  <ul className="text-sm text-red-700 mt-2 space-y-1">
                    {result.errors.map((error: string, idx: number) => (
                      <li key={idx}>• {error}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Deadlines List */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">
              Generated Deadlines ({result.deadlines.length})
            </h4>

            <div className="space-y-3">
              {result.deadlines.map((deadline: any, idx: number) => (
                <div
                  key={deadline.id}
                  className={`border rounded-lg p-4 ${priorityColors[deadline.priority as keyof typeof priorityColors]}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h5 className="font-semibold mb-1">{deadline.title}</h5>
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {deadline.deadline_date ? (
                            new Date(deadline.deadline_date).toLocaleDateString('en-US', {
                              weekday: 'short',
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric'
                            })
                          ) : (
                            'No date'
                          )}
                        </div>
                        <span className="px-2 py-0.5 bg-white/50 rounded font-medium">
                          {deadline.priority}
                        </span>
                      </div>
                      {deadline.rule_citation && (
                        <p className="text-xs mt-2 italic opacity-75">
                          {deadline.rule_citation}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex gap-4">
            <button className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium">
              Save These Deadlines
            </button>
            <button
              onClick={() => setResult(null)}
              className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <div className="text-center py-8 text-gray-500 text-sm border-t border-gray-200 pt-6">
          <Clock className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p>Enter trigger data and click Preview to see generated deadlines</p>
        </div>
      )}
    </div>
  );
}
