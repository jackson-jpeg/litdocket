'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/api-client';

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
}

interface HarvestSchedule {
  id: string;
  name: string;
  url: string;
  jurisdiction_id: string;
  jurisdiction_name: string | null;
  frequency: string;
  is_active: boolean;
  last_checked_at: string | null;
  next_run_at: string | null;
  total_checks: number;
  changes_detected: number;
  rules_harvested: number;
  error_count: number;
}

interface ScheduleRun {
  id: string;
  status: string;
  content_changed: boolean;
  rules_found: number;
  proposals_created: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export default function ScheduledHarvestingPage() {
  const [schedules, setSchedules] = useState<HarvestSchedule[]>([]);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<string | null>(null);
  const [scheduleRuns, setScheduleRuns] = useState<ScheduleRun[]>([]);
  const [runningSchedule, setRunningSchedule] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    url: '',
    name: '',
    jurisdiction_id: '',
    frequency: 'weekly',
    day_of_week: 1,
    day_of_month: 1,
    use_extended_thinking: true,
    auto_approve_high_confidence: false,
  });

  useEffect(() => {
    fetchSchedules();
    fetchJurisdictions();
  }, []);

  useEffect(() => {
    if (selectedSchedule) {
      fetchScheduleRuns(selectedSchedule);
    }
  }, [selectedSchedule]);

  const fetchSchedules = async () => {
    try {
      const response = await apiClient.get('/api/v1/authority-core/schedules');
      setSchedules(response.data || []);
    } catch (error) {
      console.error('Failed to fetch schedules:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchJurisdictions = async () => {
    try {
      const response = await apiClient.get('/api/v1/jurisdictions');
      setJurisdictions(response.data || []);
    } catch (error) {
      console.error('Failed to fetch jurisdictions:', error);
    }
  };

  const fetchScheduleRuns = async (scheduleId: string) => {
    try {
      const response = await apiClient.get(`/api/v1/authority-core/schedules/${scheduleId}/runs`);
      setScheduleRuns(response.data || []);
    } catch (error) {
      console.error('Failed to fetch schedule runs:', error);
    }
  };

  const createSchedule = async () => {
    try {
      const params = new URLSearchParams({
        url: formData.url,
        jurisdiction_id: formData.jurisdiction_id,
        frequency: formData.frequency,
        name: formData.name,
        use_extended_thinking: formData.use_extended_thinking.toString(),
        auto_approve_high_confidence: formData.auto_approve_high_confidence.toString(),
      });

      if (formData.frequency === 'weekly') {
        params.append('day_of_week', formData.day_of_week.toString());
      } else if (formData.frequency === 'monthly') {
        params.append('day_of_month', formData.day_of_month.toString());
      }

      await apiClient.post(`/api/v1/authority-core/schedules?${params}`);
      setShowCreateModal(false);
      fetchSchedules();
      setFormData({
        url: '',
        name: '',
        jurisdiction_id: '',
        frequency: 'weekly',
        day_of_week: 1,
        day_of_month: 1,
        use_extended_thinking: true,
        auto_approve_high_confidence: false,
      });
    } catch (error) {
      console.error('Failed to create schedule:', error);
    }
  };

  const toggleSchedule = async (scheduleId: string, isActive: boolean) => {
    try {
      await apiClient.put(`/api/v1/authority-core/schedules/${scheduleId}?is_active=${!isActive}`);
      fetchSchedules();
    } catch (error) {
      console.error('Failed to toggle schedule:', error);
    }
  };

  const deleteSchedule = async (scheduleId: string) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;

    try {
      await apiClient.delete(`/api/v1/authority-core/schedules/${scheduleId}`);
      fetchSchedules();
      if (selectedSchedule === scheduleId) {
        setSelectedSchedule(null);
      }
    } catch (error) {
      console.error('Failed to delete schedule:', error);
    }
  };

  const runScheduleNow = async (scheduleId: string) => {
    setRunningSchedule(scheduleId);
    try {
      await apiClient.post(`/api/v1/authority-core/schedules/${scheduleId}/run`);
      fetchSchedules();
      if (selectedSchedule === scheduleId) {
        fetchScheduleRuns(scheduleId);
      }
    } catch (error) {
      console.error('Failed to run schedule:', error);
    } finally {
      setRunningSchedule(null);
    }
  };

  const DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Scheduled Harvesting</h1>
              <p className="text-sm text-gray-600 mt-1">
                Automatically monitor court websites for rule updates
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/tools/authority-core"
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                ← Back to Authority Core
              </Link>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                + New Schedule
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex gap-6">
          {/* Schedules List */}
          <div className="flex-1">
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b">
                <h2 className="font-semibold text-gray-900">Active Schedules</h2>
              </div>

              {schedules.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  No schedules created yet. Create one to start monitoring court rules.
                </div>
              ) : (
                <div className="divide-y">
                  {schedules.map((schedule) => (
                    <div
                      key={schedule.id}
                      className={`p-4 hover:bg-gray-50 cursor-pointer ${
                        selectedSchedule === schedule.id ? 'bg-blue-50' : ''
                      }`}
                      onClick={() => setSelectedSchedule(schedule.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium text-gray-900">{schedule.name}</h3>
                            <span
                              className={`px-2 py-0.5 text-xs rounded-full ${
                                schedule.is_active
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-gray-100 text-gray-600'
                              }`}
                            >
                              {schedule.is_active ? 'Active' : 'Paused'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-500 truncate mt-1">{schedule.url}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                            <span>{schedule.jurisdiction_name || 'No jurisdiction'}</span>
                            <span className="capitalize">{schedule.frequency}</span>
                            <span>{schedule.total_checks} checks</span>
                            <span>{schedule.rules_harvested} rules found</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 ml-4">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              runScheduleNow(schedule.id);
                            }}
                            disabled={runningSchedule === schedule.id}
                            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
                          >
                            {runningSchedule === schedule.id ? 'Running...' : 'Run Now'}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleSchedule(schedule.id, schedule.is_active);
                            }}
                            className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                          >
                            {schedule.is_active ? 'Pause' : 'Resume'}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteSchedule(schedule.id);
                            }}
                            className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                          >
                            Delete
                          </button>
                        </div>
                      </div>

                      {schedule.error_count > 0 && (
                        <div className="mt-2 text-xs text-red-600">
                          {schedule.error_count} errors encountered
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Run History Panel */}
          {selectedSchedule && (
            <div className="w-96 bg-white rounded-lg shadow">
              <div className="p-4 border-b">
                <h2 className="font-semibold text-gray-900">Run History</h2>
              </div>

              {scheduleRuns.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  No runs yet
                </div>
              ) : (
                <div className="max-h-96 overflow-y-auto divide-y">
                  {scheduleRuns.map((run) => (
                    <div key={run.id} className="p-3">
                      <div className="flex items-center justify-between">
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full ${
                            run.status === 'completed'
                              ? 'bg-green-100 text-green-800'
                              : run.status === 'failed'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {run.status}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(run.started_at).toLocaleString()}
                        </span>
                      </div>

                      {run.status === 'completed' && (
                        <div className="mt-2 text-xs text-gray-600">
                          {run.content_changed ? (
                            <span className="text-blue-600">Content changed</span>
                          ) : (
                            <span>No changes</span>
                          )}
                          {run.rules_found > 0 && (
                            <span className="ml-2">
                              • {run.rules_found} rules found, {run.proposals_created} proposals
                            </span>
                          )}
                        </div>
                      )}

                      {run.error_message && (
                        <div className="mt-2 text-xs text-red-600 truncate">
                          {run.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Create Harvest Schedule</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  URL to Monitor
                </label>
                <input
                  type="url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  placeholder="https://www.law.cornell.edu/rules/frcp/rule_12"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Schedule Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="FRCP Rule 12 Monitor"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Jurisdiction
                </label>
                <select
                  value={formData.jurisdiction_id}
                  onChange={(e) => setFormData({ ...formData, jurisdiction_id: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                >
                  <option value="">Select jurisdiction...</option>
                  {jurisdictions.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Frequency
                </label>
                <select
                  value={formData.frequency}
                  onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>

              {formData.frequency === 'weekly' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Day of Week
                  </label>
                  <select
                    value={formData.day_of_week}
                    onChange={(e) =>
                      setFormData({ ...formData, day_of_week: parseInt(e.target.value) })
                    }
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    {DAYS_OF_WEEK.map((day, i) => (
                      <option key={i} value={i}>
                        {day}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {formData.frequency === 'monthly' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Day of Month
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="28"
                    value={formData.day_of_month}
                    onChange={(e) =>
                      setFormData({ ...formData, day_of_month: parseInt(e.target.value) })
                    }
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              )}

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formData.use_extended_thinking}
                    onChange={(e) =>
                      setFormData({ ...formData, use_extended_thinking: e.target.checked })
                    }
                  />
                  Use extended thinking
                </label>

                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formData.auto_approve_high_confidence}
                    onChange={(e) =>
                      setFormData({ ...formData, auto_approve_high_confidence: e.target.checked })
                    }
                  />
                  Auto-approve high confidence
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={createSchedule}
                disabled={!formData.url || !formData.jurisdiction_id}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Create Schedule
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
