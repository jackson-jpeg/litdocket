'use client';

/**
 * Deadline Calculator - Federal/State Date Computation
 *
 * Gold Standard Design System (matching Dashboard):
 * - Light slate background
 * - White cards with shadows
 * - Rounded corners
 * - Uppercase tracking headers
 */

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { SovereignTreeGrid, SelectionState } from '@/components/sovereign';
import {
  SovereignCalculator,
  calculateFederalDeadline,
  CountingMethod,
  ServiceMethod,
} from '@/lib/sovereign-calculator';
import {
  Calculator,
  ArrowLeft,
  Calendar,
  Clock,
  CheckCircle,
  Info,
} from 'lucide-react';

export default function DeadlineCalculatorPage() {
  const router = useRouter();

  // Selection state from tree grid
  const [selection, setSelection] = useState<SelectionState | null>(null);

  // Calculator state
  const [triggerDate, setTriggerDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [days, setDays] = useState<number>(21);
  const [countingMethod, setCountingMethod] = useState<CountingMethod>('CALENDAR');
  const [serviceMethod, setServiceMethod] = useState<ServiceMethod>('PERSONAL');
  const [calculationResult, setCalculationResult] = useState<ReturnType<
    typeof calculateFederalDeadline
  > | null>(null);

  // Handle selection change from tree grid
  const handleSelectionChange = (newSelection: SelectionState) => {
    setSelection(newSelection);
  };

  // Calculate deadline
  const handleCalculate = () => {
    const trigger = new Date(triggerDate);
    const result = calculateFederalDeadline(
      trigger,
      days,
      countingMethod,
      serviceMethod
    );
    setCalculationResult(result);
  };

  // Get holiday list
  const calculator = new SovereignCalculator({ year: new Date().getFullYear() });
  const holidays = calculator.getHolidays();

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => router.push('/tools')}
              className="text-slate-400 hover:text-slate-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <Calculator className="w-5 h-5 text-blue-600" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900">Deadline Calculator</h1>
              <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-mono rounded-full border border-green-200">
                ACTIVE
              </span>
            </div>
          </div>
          <p className="text-slate-500 text-sm">
            Calculate deadlines with federal/state holiday awareness, service day extensions, and full audit trail
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Tree Grid */}
          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
                <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Jurisdiction Tree</span>
                <p className="text-xs text-slate-500 mt-1">Select court to see applicable rule sets</p>
              </div>
              <div className="p-4 max-h-[500px] overflow-y-auto">
                <SovereignTreeGrid
                  onSelectionChange={handleSelectionChange}
                  showRuleDetails={true}
                />
              </div>
            </div>

            {/* Selection Summary */}
            {selection && selection.selectedRuleSets.size > 0 && (
              <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                <p className="text-sm font-medium text-blue-700">
                  {selection.selectedRuleSets.size} rule sets selected
                  {selection.lockedRuleSets.size > 0 && (
                    <span className="text-blue-600 font-normal">
                      {' '}(including {selection.lockedRuleSets.size} dependencies)
                    </span>
                  )}
                </p>
              </div>
            )}
          </div>

          {/* Right: Calculator */}
          <div className="space-y-4">
            {/* Calculator Form */}
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="bg-slate-100 border-b border-slate-200 px-4 py-3 flex items-center gap-2">
                <Calculator className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Calculate Deadline</span>
              </div>
              <div className="p-4 space-y-4">
                {/* Trigger Date */}
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    Trigger Date
                  </label>
                  <input
                    type="date"
                    value={triggerDate}
                    onChange={(e) => setTriggerDate(e.target.value)}
                    className="w-full bg-white border border-slate-300 text-slate-900 font-mono px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                {/* Days */}
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    Days (negative = before trigger)
                  </label>
                  <input
                    type="number"
                    value={days}
                    onChange={(e) => setDays(parseInt(e.target.value) || 0)}
                    className="w-full bg-white border border-slate-300 text-slate-900 font-mono px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                {/* Counting Method */}
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    Counting Method
                  </label>
                  <select
                    value={countingMethod}
                    onChange={(e) => setCountingMethod(e.target.value as CountingMethod)}
                    className="w-full bg-white border border-slate-300 text-slate-900 font-mono px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="CALENDAR">Calendar Days</option>
                    <option value="BUSINESS">Business Days</option>
                    <option value="COURT">Court Days</option>
                    <option value="RETROGRADE">Retrograde (Before Trigger)</option>
                  </select>
                </div>

                {/* Service Method */}
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    Service Method
                  </label>
                  <select
                    value={serviceMethod}
                    onChange={(e) => setServiceMethod(e.target.value as ServiceMethod)}
                    className="w-full bg-white border border-slate-300 text-slate-900 font-mono px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="PERSONAL">Personal Service (0 days)</option>
                    <option value="CERTIFIED_MAIL">Certified Mail (+3 days Federal, +5 FL)</option>
                    <option value="FIRST_CLASS_MAIL">First Class Mail (+3 days Federal, +5 FL)</option>
                    <option value="ELECTRONIC">Electronic (+3 days Federal, 0 FL)</option>
                  </select>
                </div>

                {/* Calculate Button */}
                <button
                  onClick={handleCalculate}
                  className="w-full bg-slate-900 hover:bg-slate-800 py-3 font-semibold text-white transition-colors flex items-center justify-center gap-2 rounded-lg"
                >
                  <Calculator className="w-4 h-4" />
                  Calculate Deadline
                </button>
              </div>
            </div>

            {/* Calculation Result */}
            {calculationResult && (
              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="bg-green-50 border-b border-green-200 px-4 py-3 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-xs font-bold text-green-700 uppercase tracking-wider">Calculation Result</span>
                </div>
                <div className="p-4 space-y-4">
                  {/* Main Result */}
                  <div className="bg-blue-50 p-4 border-l-4 border-blue-500 rounded-r-lg">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Deadline Date</p>
                    <p className="text-2xl font-bold text-slate-900">
                      {calculationResult.deadlineDate.toLocaleDateString('en-US', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </p>
                  </div>

                  {/* Details Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-50 p-3 rounded-lg">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">Trigger Date</p>
                      <p className="font-mono text-slate-900">
                        {calculationResult.triggerDate.toLocaleDateString()}
                      </p>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-lg">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">Base Days</p>
                      <p className="font-mono text-slate-900">{calculationResult.baseDays}</p>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-lg">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">Service Days Added</p>
                      <p className="font-mono text-blue-600">+{calculationResult.serviceDaysAdded}</p>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-lg">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">Counting Method</p>
                      <p className="font-mono text-slate-900">{calculationResult.countingMethod}</p>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-lg">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">Weekends Skipped</p>
                      <p className="font-mono text-amber-600">{calculationResult.weekendsSkipped}</p>
                    </div>
                    <div className="bg-slate-50 p-3 rounded-lg">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">Holidays Skipped</p>
                      <p className="font-mono text-amber-600">{calculationResult.holidaysSkipped}</p>
                    </div>
                  </div>

                  {/* Audit Log */}
                  <details className="bg-slate-50 border border-slate-200 rounded-lg">
                    <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-slate-700">
                      Audit Log ({calculationResult.auditLog.length} steps)
                    </summary>
                    <div className="px-4 pb-3 space-y-1 border-t border-slate-200 mt-2 pt-3">
                      {calculationResult.auditLog.map((entry, idx) => (
                        <div key={idx} className="text-xs font-mono flex gap-2">
                          <span className="text-slate-400">{entry.step}.</span>
                          <span className="text-blue-600">[{entry.action}]</span>
                          <span className="text-slate-600">{entry.notes}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              </div>
            )}

            {/* Holiday Calendar */}
            <details className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <summary className="bg-slate-100 border-b border-slate-200 px-4 py-3 cursor-pointer flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-500" />
                <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                  Federal Holidays {new Date().getFullYear()}
                </span>
              </summary>
              <div className="p-4 max-h-64 overflow-y-auto">
                <div className="space-y-2">
                  {holidays.map((holiday, idx) => (
                    <div key={idx} className="flex items-center gap-4 text-sm">
                      <span className="font-mono text-slate-500 w-20">
                        {holiday.date.toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                      <span className="text-slate-700">{holiday.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-3">
              <Calendar className="w-5 h-5 text-blue-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Holiday Awareness</h3>
            <p className="text-xs text-slate-500">
              Automatically skips federal and state holidays in calculations
            </p>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center mb-3">
              <Clock className="w-5 h-5 text-amber-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Service Extensions</h3>
            <p className="text-xs text-slate-500">
              Adds correct service days based on Federal vs Florida rules
            </p>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center mb-3">
              <Info className="w-5 h-5 text-red-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Full Audit Trail</h3>
            <p className="text-xs text-slate-500">
              Every calculation step logged for professional documentation
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
