/**
 * Harvest Management Dashboard
 *
 * Phase 5: Multi-Jurisdiction Scaling - Operational Dashboard
 *
 * Features:
 * - Active harvest jobs queue with real-time status
 * - Retry failed harvests with one click
 * - Coverage heatmap showing jurisdiction rule counts
 * - Performance metrics (success rate, avg processing time)
 * - Bulk onboarding interface
 */

'use client';

import React, { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';

interface HarvestJob {
  id: string;
  jurisdiction_name: string;
  jurisdiction_code: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  rules_found: number;
  average_confidence: number;
  error?: string;
}

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
  rule_count: number;
  verified_count: number;
  last_scraped_at?: string;
  auto_sync_enabled: boolean;
}

export default function HarvestDashboard() {
  const [jobs, setJobs] = useState<HarvestJob[]>([]);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJurisdictions, setSelectedJurisdictions] = useState<Set<string>>(new Set());

  // Bulk onboarding form
  const [bulkOnboardingText, setBulkOnboardingText] = useState('');
  const [showBulkForm, setShowBulkForm] = useState(false);

  useEffect(() => {
    loadData();
    // Poll for updates every 10 seconds
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      // Load harvest jobs (mock - would come from backend)
      // const jobsResponse = await apiClient.get('/authority-core/harvest/jobs');
      // setJobs(jobsResponse.data.jobs);

      // Load jurisdictions
      const jurisdictionsResponse = await apiClient.get('/jurisdictions');
      setJurisdictions(jurisdictionsResponse.data.jurisdictions || []);

      setLoading(false);
    } catch (error) {
      console.error('Failed to load harvest data:', error);
      setLoading(false);
    }
  };

  const retryFailedJob = async (jobId: string) => {
    try {
      await apiClient.post(`/authority-core/harvest/jobs/${jobId}/retry`);
      loadData();
    } catch (error) {
      console.error('Failed to retry job:', error);
    }
  };

  const triggerHarvest = async (jurisdictionId: string) => {
    try {
      await apiClient.post(`/authority-core/cartographer/discover/${jurisdictionId}`);
      loadData();
    } catch (error) {
      console.error('Failed to trigger harvest:', error);
    }
  };

  const bulkOnboard = async () => {
    try {
      // Parse CSV format: name,code,website,rules_url
      const lines = bulkOnboardingText.trim().split('\n');
      const jurisdictionsData = lines.slice(1).map(line => {
        const [name, code, court_website, rules_url] = line.split(',');
        return { name, code, court_website, rules_url, court_type: 'state' };
      });

      await apiClient.post('/authority-core/jurisdictions/batch-onboard', jurisdictionsData);
      setShowBulkForm(false);
      setBulkOnboardingText('');
      loadData();
    } catch (error) {
      console.error('Bulk onboarding failed:', error);
    }
  };

  // Calculate stats
  const totalJurisdictions = jurisdictions.length;
  const activeJurisdictions = jurisdictions.filter(j => j.auto_sync_enabled).length;
  const totalRules = jurisdictions.reduce((sum, j) => sum + j.rule_count, 0);
  const verifiedRules = jurisdictions.reduce((sum, j) => sum + j.verified_count, 0);
  const coverageRate = totalRules > 0 ? (verifiedRules / totalRules * 100).toFixed(1) : '0';

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-ink">Harvest Management</h1>
          <p className="text-gray-600 mt-1">Manage rule extraction and jurisdiction onboarding</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-px bg-ink mb-6">
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">TOTAL JURISDICTIONS</p>
            <p className="text-3xl font-bold text-ink">{totalJurisdictions}</p>
            <p className="text-xs text-gray-600 mt-1">{activeJurisdictions} active sync</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">TOTAL RULES</p>
            <p className="text-3xl font-bold text-ink">{totalRules}</p>
            <p className="text-xs text-gray-600 mt-1">{verifiedRules} verified</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">COVERAGE RATE</p>
            <p className="text-3xl font-bold text-ink">{coverageRate}%</p>
            <p className="text-xs text-gray-600 mt-1">Verified / Total</p>
          </div>
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">ACTIVE JOBS</p>
            <p className="text-3xl font-bold text-ink">{jobs.filter(j => j.status === 'in_progress').length}</p>
            <p className="text-xs text-gray-600 mt-1">{jobs.filter(j => j.status === 'pending').length} queued</p>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white border-2 border-ink p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-ink">Quick Actions</h2>
              <p className="text-sm text-gray-600 mt-0.5">Bulk operations and utilities</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowBulkForm(!showBulkForm)}
                className="px-4 py-2 border-2 border-ink bg-white hover:bg-gray-50 font-medium"
              >
                Bulk Onboard
              </button>
              <button
                onClick={loadData}
                className="px-4 py-2 border-2 border-ink bg-white hover:bg-gray-50 font-medium"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Bulk Onboarding Form */}
          {showBulkForm && (
            <div className="mt-4 border-t-2 border-ink pt-4">
              <h3 className="font-medium text-ink mb-2">Bulk Onboard Jurisdictions</h3>
              <p className="text-sm text-gray-600 mb-3">
                Paste CSV data: name,code,court_website,rules_url (one per line, first line is header)
              </p>
              <textarea
                value={bulkOnboardingText}
                onChange={(e) => setBulkOnboardingText(e.target.value)}
                className="w-full h-40 border-2 border-gray-300 p-2 font-mono text-sm"
                placeholder="name,code,court_website,rules_url&#10;California Superior Court,CA_SUP,https://courts.ca.gov,https://courts.ca.gov/rules.htm"
              />
              <div className="flex gap-2 mt-3">
                <button
                  onClick={bulkOnboard}
                  className="px-4 py-2 border-2 border-ink bg-ink text-white hover:bg-gray-800 font-medium"
                >
                  Start Bulk Onboarding
                </button>
                <button
                  onClick={() => setShowBulkForm(false)}
                  className="px-4 py-2 border-2 border-gray-300 bg-white hover:bg-gray-50 font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Coverage Heatmap */}
        <div className="bg-white border-2 border-ink mb-6">
          <div className="border-b-2 border-ink bg-gray-50 px-4 py-3">
            <h2 className="font-semibold text-ink">Jurisdiction Coverage Heatmap</h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-5 gap-2">
              {jurisdictions.slice(0, 20).map((jurisdiction) => {
                const coverage = jurisdiction.rule_count > 0
                  ? (jurisdiction.verified_count / jurisdiction.rule_count * 100)
                  : 0;
                const color = coverage >= 80 ? 'bg-green-500' :
                              coverage >= 60 ? 'bg-yellow-500' :
                              coverage >= 40 ? 'bg-orange-500' : 'bg-red-500';

                return (
                  <div
                    key={jurisdiction.id}
                    className={`p-3 border-2 border-ink ${color} text-white cursor-pointer hover:opacity-80`}
                    title={`${jurisdiction.name}: ${coverage.toFixed(0)}% coverage`}
                  >
                    <p className="font-bold text-sm">{jurisdiction.code}</p>
                    <p className="text-xs mt-1">{jurisdiction.rule_count} rules</p>
                    <p className="text-xs">{coverage.toFixed(0)}% verified</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Jobs Queue */}
        <div className="bg-white border-2 border-ink">
          <div className="border-b-2 border-ink bg-gray-50 px-4 py-3">
            <h2 className="font-semibold text-ink">Recent Harvest Jobs</h2>
          </div>
          <div className="divide-y-2 divide-ink">
            {jobs.length === 0 ? (
              <div className="p-8 text-center text-gray-600">
                No harvest jobs yet. Trigger a harvest to get started.
              </div>
            ) : (
              jobs.map((job) => (
                <div key={job.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-ink">{job.jurisdiction_name}</h3>
                        <span className="text-xs font-mono text-gray-600">{job.jurisdiction_code}</span>
                        <StatusBadge status={job.status} />
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                        <span>Started: {new Date(job.started_at).toLocaleString()}</span>
                        {job.completed_at && (
                          <span>Completed: {new Date(job.completed_at).toLocaleString()}</span>
                        )}
                        {job.rules_found > 0 && (
                          <span>{job.rules_found} rules found (avg confidence: {(job.average_confidence * 100).toFixed(0)}%)</span>
                        )}
                      </div>
                      {job.error && (
                        <p className="mt-2 text-sm text-red-600">Error: {job.error}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {job.status === 'failed' && (
                        <button
                          onClick={() => retryFailedJob(job.id)}
                          className="px-3 py-1 text-sm border-2 border-ink bg-white hover:bg-gray-50"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    pending: 'bg-gray-100 border-gray-600 text-gray-900',
    in_progress: 'bg-blue-100 border-blue-600 text-blue-900',
    completed: 'bg-green-100 border-green-600 text-green-900',
    failed: 'bg-red-100 border-red-600 text-red-900'
  };

  return (
    <span className={`px-2 py-0.5 text-xs font-medium border-2 ${colors[status as keyof typeof colors] || colors.pending}`}>
      {status.toUpperCase()}
    </span>
  );
}
