'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import RuleDependencyGraph from '@/components/authority-core/RuleDependencyGraph';
import apiClient from '@/lib/api-client';

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
}

const TRIGGER_TYPES = [
  { value: '', label: 'All Triggers' },
  { value: 'complaint_served', label: 'Complaint Served' },
  { value: 'answer_filed', label: 'Answer Filed' },
  { value: 'case_filed', label: 'Case Filed' },
  { value: 'discovery_served', label: 'Discovery Served' },
  { value: 'motion_filed', label: 'Motion Filed' },
  { value: 'trial_date', label: 'Trial Date' },
  { value: 'appeal_filed', label: 'Appeal Filed' },
];

export default function RuleVisualizationPage() {
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>('');
  const [selectedTrigger, setSelectedTrigger] = useState<string>('');
  const [showConflictsOnly, setShowConflictsOnly] = useState(false);
  const [selectedRule, setSelectedRule] = useState<string | null>(null);
  const [ruleDetails, setRuleDetails] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const fetchJurisdictions = async () => {
      try {
        const response = await apiClient.get('/api/v1/jurisdictions');
        setJurisdictions(response.data || []);
      } catch (error) {
        console.error('Failed to fetch jurisdictions:', error);
      }
    };
    fetchJurisdictions();
  }, []);

  useEffect(() => {
    const fetchRuleDetails = async () => {
      if (!selectedRule) {
        setRuleDetails(null);
        return;
      }
      try {
        const response = await apiClient.get(`/api/v1/authority-core/rules/${selectedRule}`);
        setRuleDetails(response.data);
      } catch (error) {
        console.error('Failed to fetch rule details:', error);
      }
    };
    fetchRuleDetails();
  }, [selectedRule]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Rule Dependency Graph</h1>
              <p className="text-sm text-gray-600 mt-1">
                Visualize relationships, conflicts, and tier hierarchy between rules
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/rules/database"
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                ← Back to Rules Database
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Jurisdiction
              </label>
              <select
                value={selectedJurisdiction}
                onChange={(e) => setSelectedJurisdiction(e.target.value)}
                className="block w-48 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Jurisdictions</option>
                {jurisdictions.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Trigger Type
              </label>
              <select
                value={selectedTrigger}
                onChange={(e) => setSelectedTrigger(e.target.value)}
                className="block w-48 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {TRIGGER_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={showConflictsOnly}
                  onChange={(e) => setShowConflictsOnly(e.target.checked)}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                Show conflicts only
              </label>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex gap-4">
          {/* Graph */}
          <div className="flex-1 bg-white rounded-lg shadow overflow-hidden">
            <RuleDependencyGraph
              jurisdictionId={selectedJurisdiction || undefined}
              triggerType={selectedTrigger || undefined}
              showConflictsOnly={showConflictsOnly}
              onNodeClick={setSelectedRule}
              height="calc(100vh - 280px)"
            />
          </div>

          {/* Rule details panel */}
          {selectedRule && ruleDetails && (
            <div className="w-80 bg-white rounded-lg shadow p-4 h-fit max-h-[calc(100vh-280px)] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">Rule Details</h3>
                <button
                  onClick={() => setSelectedRule(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4 text-sm">
                <div>
                  <label className="text-xs text-gray-500 uppercase">Rule Code</label>
                  <p className="font-mono text-gray-900">{(ruleDetails as Record<string, unknown>).rule_code as string}</p>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase">Name</label>
                  <p className="text-gray-900">{(ruleDetails as Record<string, unknown>).rule_name as string}</p>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase">Citation</label>
                  <p className="text-gray-700">{(ruleDetails as Record<string, unknown>).citation as string || 'N/A'}</p>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase">Trigger Type</label>
                  <p className="text-gray-700">{((ruleDetails as Record<string, unknown>).trigger_type as string || '').replace(/_/g, ' ')}</p>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase">Deadlines</label>
                  <ul className="mt-1 space-y-1">
                    {((ruleDetails as Record<string, unknown>).deadlines as Array<Record<string, unknown>> || []).map((dl: Record<string, unknown>, i: number) => (
                      <li key={i} className="text-gray-700 bg-gray-50 px-2 py-1 rounded">
                        {dl.title as string}: <span className="font-medium">{dl.days_from_trigger as number} days</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-4 border-t">
                  <Link
                    href={`/rules/database?rule=${selectedRule}`}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    View full details →
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
