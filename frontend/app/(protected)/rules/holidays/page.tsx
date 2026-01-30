'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api-client';

interface Jurisdiction {
  id: string;
  name: string;
  code: string;
}

interface CourtHoliday {
  id: string;
  name: string;
  date: string;
  is_observed: boolean;
  actual_date: string | null;
  holiday_type: string;
  court_closed: boolean;
}

interface BusinessDayCheck {
  date: string;
  is_business_day: boolean;
  is_weekend: boolean;
  holiday: { name: string; type: string } | null;
}

export default function CourtHolidaysPage() {
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>('');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [holidays, setHolidays] = useState<CourtHoliday[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [checkDate, setCheckDate] = useState('');
  const [checkResult, setCheckResult] = useState<BusinessDayCheck | null>(null);

  // Add holiday form
  const [newHoliday, setNewHoliday] = useState({
    name: '',
    date: '',
    holiday_type: 'custom',
    court_closed: true,
  });

  useEffect(() => {
    fetchJurisdictions();
  }, []);

  useEffect(() => {
    if (selectedJurisdiction) {
      fetchHolidays();
    }
  }, [selectedJurisdiction, selectedYear]);

  const fetchJurisdictions = async () => {
    try {
      const response = await apiClient.get('/api/v1/jurisdictions');
      setJurisdictions(response.data || []);
      if (response.data?.length > 0) {
        setSelectedJurisdiction(response.data[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch jurisdictions:', error);
    }
  };

  const fetchHolidays = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(
        `/api/v1/authority-core/holidays?jurisdiction_id=${selectedJurisdiction}&year=${selectedYear}`
      );
      setHolidays(response.data?.holidays || []);
    } catch (error) {
      console.error('Failed to fetch holidays:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateHolidays = async () => {
    setGenerating(true);
    try {
      await apiClient.post(
        `/api/v1/authority-core/holidays/generate?jurisdiction_id=${selectedJurisdiction}&year=${selectedYear}`
      );
      fetchHolidays();
    } catch (error) {
      console.error('Failed to generate holidays:', error);
    } finally {
      setGenerating(false);
    }
  };

  const addHoliday = async () => {
    try {
      await apiClient.post(
        `/api/v1/authority-core/holidays?jurisdiction_id=${selectedJurisdiction}&name=${encodeURIComponent(newHoliday.name)}&holiday_date=${newHoliday.date}&holiday_type=${newHoliday.holiday_type}&court_closed=${newHoliday.court_closed}`
      );
      setShowAddModal(false);
      setNewHoliday({ name: '', date: '', holiday_type: 'custom', court_closed: true });
      fetchHolidays();
    } catch (error) {
      console.error('Failed to add holiday:', error);
    }
  };

  const deleteHoliday = async (holidayId: string) => {
    if (!confirm('Are you sure you want to delete this holiday?')) return;

    try {
      await apiClient.delete(`/api/v1/authority-core/holidays/${holidayId}`);
      fetchHolidays();
    } catch (error) {
      console.error('Failed to delete holiday:', error);
    }
  };

  const checkBusinessDay = async () => {
    if (!checkDate || !selectedJurisdiction) return;

    try {
      const response = await apiClient.get(
        `/api/v1/authority-core/holidays/check?jurisdiction_id=${selectedJurisdiction}&check_date=${checkDate}`
      );
      setCheckResult(response.data);
    } catch (error) {
      console.error('Failed to check business day:', error);
    }
  };

  const YEARS = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() + i - 1);

  const HOLIDAY_TYPES = [
    { value: 'federal', label: 'Federal', color: 'bg-blue-100 text-blue-800' },
    { value: 'state', label: 'State', color: 'bg-green-100 text-green-800' },
    { value: 'local', label: 'Local', color: 'bg-purple-100 text-purple-800' },
    { value: 'court_specific', label: 'Court Specific', color: 'bg-orange-100 text-orange-800' },
    { value: 'custom', label: 'Custom', color: 'bg-gray-100 text-gray-800' },
  ];

  const getTypeStyle = (type: string) => {
    return HOLIDAY_TYPES.find((t) => t.value === type)?.color || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Court Holiday Calendar</h1>
              <p className="text-sm text-gray-600 mt-1">
                Manage court holidays for accurate business day calculations
              </p>
            </div>
            <Link
              href="/tools/authority-core"
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              ← Back to Authority Core
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Controls */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Jurisdiction</label>
              <select
                value={selectedJurisdiction}
                onChange={(e) => setSelectedJurisdiction(e.target.value)}
                className="block w-64 px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                {jurisdictions.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Year</label>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                className="block w-32 px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                {YEARS.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2 ml-auto">
              <button
                onClick={generateHolidays}
                disabled={generating || !selectedJurisdiction}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {generating ? 'Generating...' : 'Generate Federal Holidays'}
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                + Add Holiday
              </button>
            </div>
          </div>
        </div>

        <div className="flex gap-6">
          {/* Holidays List */}
          <div className="flex-1 bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="font-semibold text-gray-900">
                {selectedYear} Holidays ({holidays.length})
              </h2>
            </div>

            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              </div>
            ) : holidays.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No holidays found. Click &quot;Generate Federal Holidays&quot; to add standard federal
                holidays.
              </div>
            ) : (
              <div className="divide-y">
                {holidays.map((holiday) => (
                  <div key={holiday.id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-gray-900">{holiday.name}</h3>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${getTypeStyle(holiday.holiday_type)}`}>
                            {holiday.holiday_type}
                          </span>
                          {holiday.is_observed && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800">
                              Observed
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          {new Date(holiday.date + 'T00:00:00').toLocaleDateString('en-US', {
                            weekday: 'long',
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                          })}
                          {holiday.actual_date && (
                            <span className="text-gray-400 ml-2">
                              (Actual: {new Date(holiday.actual_date + 'T00:00:00').toLocaleDateString()})
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full ${
                            holiday.court_closed
                              ? 'bg-red-100 text-red-800'
                              : 'bg-green-100 text-green-800'
                          }`}
                        >
                          {holiday.court_closed ? 'Court Closed' : 'Court Open'}
                        </span>
                        <button
                          onClick={() => deleteHoliday(holiday.id)}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Business Day Checker */}
          <div className="w-80">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="font-semibold text-gray-900 mb-4">Business Day Checker</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Date to Check</label>
                  <input
                    type="date"
                    value={checkDate}
                    onChange={(e) => setCheckDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>

                <button
                  onClick={checkBusinessDay}
                  disabled={!checkDate || !selectedJurisdiction}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  Check Date
                </button>

                {checkResult && (
                  <div className="mt-4 p-4 rounded-lg bg-gray-50">
                    <div className="flex items-center gap-2 mb-2">
                      <div
                        className={`w-4 h-4 rounded-full ${
                          checkResult.is_business_day ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      ></div>
                      <span className="font-medium">
                        {checkResult.is_business_day ? 'Business Day' : 'Not a Business Day'}
                      </span>
                    </div>

                    <div className="text-sm text-gray-600">
                      {new Date(checkResult.date + 'T00:00:00').toLocaleDateString('en-US', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </div>

                    {checkResult.is_weekend && (
                      <div className="text-sm text-orange-600 mt-2">Weekend</div>
                    )}

                    {checkResult.holiday && (
                      <div className="text-sm text-red-600 mt-2">
                        Holiday: {checkResult.holiday.name} ({checkResult.holiday.type})
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Quick Stats */}
            <div className="bg-white rounded-lg shadow p-4 mt-4">
              <h3 className="font-semibold text-gray-900 mb-3">Quick Stats</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Holidays:</span>
                  <span className="font-medium">{holidays.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Federal:</span>
                  <span className="font-medium">
                    {holidays.filter((h) => h.holiday_type === 'federal').length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">State:</span>
                  <span className="font-medium">
                    {holidays.filter((h) => h.holiday_type === 'state').length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Custom:</span>
                  <span className="font-medium">
                    {holidays.filter((h) => h.holiday_type === 'custom').length}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add Holiday Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-semibold mb-4">Add Court Holiday</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Holiday Name</label>
                <input
                  type="text"
                  value={newHoliday.name}
                  onChange={(e) => setNewHoliday({ ...newHoliday, name: e.target.value })}
                  placeholder="e.g., Court Closure Day"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                <input
                  type="date"
                  value={newHoliday.date}
                  onChange={(e) => setNewHoliday({ ...newHoliday, date: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Holiday Type</label>
                <select
                  value={newHoliday.holiday_type}
                  onChange={(e) => setNewHoliday({ ...newHoliday, holiday_type: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                >
                  {HOLIDAY_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newHoliday.court_closed}
                  onChange={(e) => setNewHoliday({ ...newHoliday, court_closed: e.target.checked })}
                />
                Court is closed on this day
              </label>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={addHoliday}
                disabled={!newHoliday.name || !newHoliday.date}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Add Holiday
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
