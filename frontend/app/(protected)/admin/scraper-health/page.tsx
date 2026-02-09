/**
 * Scraper Health Dashboard
 *
 * Phase 5: Multi-Jurisdiction Scaling - Operations Monitoring
 *
 * Features:
 * - Real-time scraper health status for all jurisdictions
 * - Consecutive failure tracking with auto-disable thresholds
 * - Scraper config editor (JSON)
 * - Test scraper functionality
 * - Health alerts and notifications
 */

'use client';

import React, { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';

interface ScraperHealth {
  jurisdiction_id: string;
  jurisdiction_name: string;
  jurisdiction_code: string;
  status: 'healthy' | 'degraded' | 'failed' | 'disabled';
  last_successful_scrape: string | null;
  last_failed_scrape: string | null;
  consecutive_failures: number;
  total_scrapes: number;
  success_rate: number;
  has_scraper_config: boolean;
  scraper_config?: any;
  auto_sync_enabled: boolean;
  sync_frequency: string;
}

export default function ScraperHealthDashboard() {
  const [health, setHealth] = useState<ScraperHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<ScraperHealth | null>(null);
  const [editingConfig, setEditingConfig] = useState(false);
  const [configText, setConfigText] = useState('');

  useEffect(() => {
    loadHealthData();
    // Poll every 30 seconds
    const interval = setInterval(loadHealthData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadHealthData = async () => {
    try {
      const response = await apiClient.get('/authority-core/scraper-health/report');
      setHealth(response.data.jurisdictions || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load scraper health:', error);
      setLoading(false);
    }
  };

  const testScraper = async (jurisdictionId: string) => {
    try {
      await apiClient.post(`/authority-core/scraper-health/check/${jurisdictionId}`);
      loadHealthData();
    } catch (error) {
      console.error('Scraper test failed:', error);
    }
  };

  const toggleAutoSync = async (jurisdictionId: string, enabled: boolean) => {
    try {
      await apiClient.patch(`/jurisdictions/${jurisdictionId}`, {
        auto_sync_enabled: enabled
      });
      loadHealthData();
    } catch (error) {
      console.error('Failed to toggle auto-sync:', error);
    }
  };

  const saveScraperConfig = async () => {
    if (!selectedJurisdiction) return;

    try {
      const config = JSON.parse(configText);
      await apiClient.patch(`/jurisdictions/${selectedJurisdiction.jurisdiction_id}`, {
        scraper_config: config
      });
      setEditingConfig(false);
      loadHealthData();
    } catch (error) {
      console.error('Failed to save scraper config:', error);
      alert('Invalid JSON or save failed');
    }
  };

  const openConfigEditor = (jurisdiction: ScraperHealth) => {
    setSelectedJurisdiction(jurisdiction);
    setConfigText(JSON.stringify(jurisdiction.scraper_config || {}, null, 2));
    setEditingConfig(true);
  };

  // Calculate overall health
  const healthyCount = health.filter(h => h.status === 'healthy').length;
  const degradedCount = health.filter(h => h.status === 'degraded').length;
  const failedCount = health.filter(h => h.status === 'failed').length;
  const disabledCount = health.filter(h => h.status === 'disabled').length;
  const totalCount = health.length;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-ink">Scraper Health Dashboard</h1>
          <p className="text-gray-600 mt-1">Monitor scraper status and configuration</p>
        </div>

        {/* Health Overview */}
        <div className="grid grid-cols-5 gap-px bg-ink mb-6">
          <div className="bg-white p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">TOTAL</p>
            <p className="text-3xl font-bold text-ink">{totalCount}</p>
            <p className="text-xs text-gray-600 mt-1">Jurisdictions</p>
          </div>
          <div className="bg-green-50 p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">HEALTHY</p>
            <p className="text-3xl font-bold text-green-700">{healthyCount}</p>
            <p className="text-xs text-gray-600 mt-1">{totalCount > 0 ? ((healthyCount / totalCount) * 100).toFixed(0) : 0}%</p>
          </div>
          <div className="bg-yellow-50 p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">DEGRADED</p>
            <p className="text-3xl font-bold text-yellow-700">{degradedCount}</p>
            <p className="text-xs text-gray-600 mt-1">1-2 failures</p>
          </div>
          <div className="bg-red-50 p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">FAILED</p>
            <p className="text-3xl font-bold text-red-700">{failedCount}</p>
            <p className="text-xs text-gray-600 mt-1">≥3 failures</p>
          </div>
          <div className="bg-gray-100 p-4">
            <p className="text-sm font-semibold text-gray-500 mb-1">DISABLED</p>
            <p className="text-3xl font-bold text-gray-700">{disabledCount}</p>
            <p className="text-xs text-gray-600 mt-1">Auto-disabled</p>
          </div>
        </div>

        {/* Scrapers List */}
        <div className="bg-white border-2 border-ink">
          <div className="border-b-2 border-ink bg-gray-50 px-4 py-3 flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-ink">Jurisdiction Scrapers</h2>
              <p className="text-sm text-gray-600 mt-0.5">Real-time health status</p>
            </div>
            <button
              onClick={loadHealthData}
              className="px-3 py-1 text-sm border-2 border-ink bg-white hover:bg-gray-50 font-medium"
            >
              Refresh
            </button>
          </div>

          <div className="divide-y-2 divide-ink">
            {loading ? (
              <div className="p-8 text-center text-gray-600">Loading...</div>
            ) : health.length === 0 ? (
              <div className="p-8 text-center text-gray-600">No jurisdictions configured</div>
            ) : (
              health.map((jurisdiction) => (
                <div key={jurisdiction.jurisdiction_id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <HealthIndicator status={jurisdiction.status} />
                        <div>
                          <h3 className="font-medium text-ink">{jurisdiction.jurisdiction_name}</h3>
                          <p className="text-xs font-mono text-gray-600">{jurisdiction.jurisdiction_code}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-5 gap-4 mt-3 text-sm">
                        <div>
                          <p className="text-xs text-gray-500">CONSECUTIVE FAILURES</p>
                          <p className={`font-semibold ${
                            jurisdiction.consecutive_failures >= 3 ? 'text-red-600' :
                            jurisdiction.consecutive_failures > 0 ? 'text-yellow-600' :
                            'text-green-600'
                          }`}>
                            {jurisdiction.consecutive_failures}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">SUCCESS RATE</p>
                          <p className="font-semibold text-ink">{(jurisdiction.success_rate * 100).toFixed(0)}%</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">TOTAL SCRAPES</p>
                          <p className="font-semibold text-ink">{jurisdiction.total_scrapes}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">LAST SUCCESS</p>
                          <p className="text-xs text-gray-700">
                            {jurisdiction.last_successful_scrape
                              ? new Date(jurisdiction.last_successful_scrape).toLocaleDateString()
                              : 'Never'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">SYNC</p>
                          <p className="text-xs text-gray-700">
                            {jurisdiction.auto_sync_enabled ? jurisdiction.sync_frequency : 'Disabled'}
                          </p>
                        </div>
                      </div>

                      {!jurisdiction.has_scraper_config && (
                        <div className="mt-2 px-3 py-1 bg-yellow-50 border-l-4 border-yellow-500 text-sm text-yellow-900">
                          ⚠️ No scraper configuration found
                        </div>
                      )}
                    </div>

                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => testScraper(jurisdiction.jurisdiction_id)}
                        className="px-3 py-1 text-sm border-2 border-ink bg-white hover:bg-gray-50 font-medium"
                      >
                        Test
                      </button>
                      {jurisdiction.has_scraper_config && (
                        <button
                          onClick={() => openConfigEditor(jurisdiction)}
                          className="px-3 py-1 text-sm border-2 border-gray-300 bg-white hover:bg-gray-50 font-medium"
                        >
                          Edit Config
                        </button>
                      )}
                      <button
                        onClick={() => toggleAutoSync(
                          jurisdiction.jurisdiction_id,
                          !jurisdiction.auto_sync_enabled
                        )}
                        className={`px-3 py-1 text-sm border-2 font-medium ${
                          jurisdiction.auto_sync_enabled
                            ? 'border-red-500 text-red-600 bg-white hover:bg-red-50'
                            : 'border-green-500 text-green-600 bg-white hover:bg-green-50'
                        }`}
                      >
                        {jurisdiction.auto_sync_enabled ? 'Disable' : 'Enable'}
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Config Editor Modal */}
        {editingConfig && selectedJurisdiction && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white border-2 border-ink max-w-4xl w-full max-h-[80vh] flex flex-col">
              <div className="border-b-2 border-ink bg-gray-50 px-4 py-3">
                <h3 className="font-semibold text-ink">Edit Scraper Config</h3>
                <p className="text-sm text-gray-600 mt-0.5">{selectedJurisdiction.jurisdiction_name}</p>
              </div>

              <div className="flex-1 overflow-auto p-4">
                <textarea
                  value={configText}
                  onChange={(e) => setConfigText(e.target.value)}
                  className="w-full h-96 border-2 border-gray-300 p-3 font-mono text-sm"
                  spellCheck={false}
                />
                <p className="text-xs text-gray-600 mt-2">
                  ⚠️ Editing scraper config requires JSON knowledge. Invalid config will break scraping.
                </p>
              </div>

              <div className="border-t-2 border-ink bg-gray-50 px-4 py-3 flex gap-2">
                <button
                  onClick={saveScraperConfig}
                  className="px-4 py-2 border-2 border-ink bg-ink text-white hover:bg-gray-800 font-medium"
                >
                  Save Config
                </button>
                <button
                  onClick={() => setEditingConfig(false)}
                  className="px-4 py-2 border-2 border-gray-300 bg-white hover:bg-gray-50 font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function HealthIndicator({ status }: { status: string }) {
  const colors = {
    healthy: 'bg-green-500',
    degraded: 'bg-yellow-500',
    failed: 'bg-red-500',
    disabled: 'bg-gray-400'
  };

  const labels = {
    healthy: 'Healthy',
    degraded: 'Degraded',
    failed: 'Failed',
    disabled: 'Disabled'
  };

  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 ${colors[status as keyof typeof colors] || colors.disabled}`} />
      <span className="text-sm font-medium text-gray-700">{labels[status as keyof typeof labels] || status}</span>
    </div>
  );
}
