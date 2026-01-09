'use client';

/**
 * Deadline Calculator - Federal/State Date Computation
 *
 * Sovereign Design System:
 * - Dark terminal aesthetic
 * - Dense data display
 * - Full audit trail
 * - Zero radius
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
  ChevronRight,
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
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => router.push('/tools')}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <Calculator className="w-6 h-6 text-cyan-400" />
              <h1 className="text-2xl font-mono font-bold">DEADLINE CALCULATOR</h1>
              <span className="px-2 py-0.5 bg-emerald-900 text-emerald-400 text-xs font-mono">ACTIVE</span>
            </div>
          </div>
          <p className="text-slate-400 text-sm font-mono">
            Calculate deadlines with federal/state holiday awareness, service day extensions, and full audit trail
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Tree Grid */}
          <div className="space-y-4">
            <div className="bg-slate-900 border border-slate-700">
              <div className="bg-slate-800 border-b border-slate-700 px-4 py-3">
                <span className="font-mono text-sm text-slate-300">JURISDICTION TREE</span>
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
              <div className="bg-cyan-900/30 border border-cyan-800 p-4">
                <p className="text-sm font-mono text-cyan-400">
                  {selection.selectedRuleSets.size} rule sets selected
                  {selection.lockedRuleSets.size > 0 && (
                    <span className="text-slate-400">
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
            <div className="bg-slate-900 border border-slate-700">
              <div className="bg-slate-800 border-b border-slate-700 px-4 py-3 flex items-center gap-2">
                <Calculator className="w-4 h-4 text-cyan-400" />
                <span className="font-mono text-sm text-slate-300">CALCULATE DEADLINE</span>
              </div>
              <div className="p-4 space-y-4">
                {/* Trigger Date */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">
                    Trigger Date
                  </label>
                  <input
                    type="date"
                    value={triggerDate}
                    onChange={(e) => setTriggerDate(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-600 text-white font-mono px-3 py-2 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Days */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">
                    Days (negative = before trigger)
                  </label>
                  <input
                    type="number"
                    value={days}
                    onChange={(e) => setDays(parseInt(e.target.value) || 0)}
                    className="w-full bg-slate-800 border border-slate-600 text-white font-mono px-3 py-2 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Counting Method */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">
                    Counting Method
                  </label>
                  <select
                    value={countingMethod}
                    onChange={(e) => setCountingMethod(e.target.value as CountingMethod)}
                    className="w-full bg-slate-800 border border-slate-600 text-white font-mono px-3 py-2 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="CALENDAR">Calendar Days</option>
                    <option value="BUSINESS">Business Days</option>
                    <option value="COURT">Court Days</option>
                    <option value="RETROGRADE">Retrograde (Before Trigger)</option>
                  </select>
                </div>

                {/* Service Method */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">
                    Service Method
                  </label>
                  <select
                    value={serviceMethod}
                    onChange={(e) => setServiceMethod(e.target.value as ServiceMethod)}
                    className="w-full bg-slate-800 border border-slate-600 text-white font-mono px-3 py-2 focus:outline-none focus:border-cyan-500"
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
                  className="w-full bg-cyan-600 hover:bg-cyan-500 py-3 font-mono font-bold text-white transition-colors flex items-center justify-center gap-2"
                >
                  <Calculator className="w-4 h-4" />
                  CALCULATE DEADLINE
                </button>
              </div>
            </div>

            {/* Calculation Result */}
            {calculationResult && (
              <div className="bg-slate-900 border border-slate-700">
                <div className="bg-emerald-900 border-b border-emerald-800 px-4 py-3 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  <span className="font-mono text-sm text-emerald-300">CALCULATION RESULT</span>
                </div>
                <div className="p-4 space-y-4">
                  {/* Main Result */}
                  <div className="bg-slate-800 p-4 border-l-4 border-cyan-500">
                    <p className="text-xs font-mono text-slate-400 uppercase mb-1">Deadline Date</p>
                    <p className="text-2xl font-mono font-bold text-white">
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
                    <div className="bg-slate-800 p-3">
                      <p className="text-xs font-mono text-slate-500 uppercase">Trigger Date</p>
                      <p className="font-mono text-white">
                        {calculationResult.triggerDate.toLocaleDateString()}
                      </p>
                    </div>
                    <div className="bg-slate-800 p-3">
                      <p className="text-xs font-mono text-slate-500 uppercase">Base Days</p>
                      <p className="font-mono text-white">{calculationResult.baseDays}</p>
                    </div>
                    <div className="bg-slate-800 p-3">
                      <p className="text-xs font-mono text-slate-500 uppercase">Service Days Added</p>
                      <p className="font-mono text-cyan-400">+{calculationResult.serviceDaysAdded}</p>
                    </div>
                    <div className="bg-slate-800 p-3">
                      <p className="text-xs font-mono text-slate-500 uppercase">Counting Method</p>
                      <p className="font-mono text-white">{calculationResult.countingMethod}</p>
                    </div>
                    <div className="bg-slate-800 p-3">
                      <p className="text-xs font-mono text-slate-500 uppercase">Weekends Skipped</p>
                      <p className="font-mono text-amber-400">{calculationResult.weekendsSkipped}</p>
                    </div>
                    <div className="bg-slate-800 p-3">
                      <p className="text-xs font-mono text-slate-500 uppercase">Holidays Skipped</p>
                      <p className="font-mono text-amber-400">{calculationResult.holidaysSkipped}</p>
                    </div>
                  </div>

                  {/* Audit Log */}
                  <details className="bg-slate-800 border border-slate-700">
                    <summary className="px-4 py-2 cursor-pointer text-sm font-mono text-slate-300">
                      AUDIT LOG ({calculationResult.auditLog.length} steps)
                    </summary>
                    <div className="px-4 pb-3 space-y-1">
                      {calculationResult.auditLog.map((entry, idx) => (
                        <div key={idx} className="text-xs font-mono flex gap-2">
                          <span className="text-slate-600">{entry.step}.</span>
                          <span className="text-cyan-500">[{entry.action}]</span>
                          <span className="text-slate-400">{entry.notes}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              </div>
            )}

            {/* Holiday Calendar */}
            <details className="bg-slate-900 border border-slate-700">
              <summary className="bg-slate-800 border-b border-slate-700 px-4 py-3 cursor-pointer flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-400" />
                <span className="font-mono text-sm text-slate-300">
                  FEDERAL HOLIDAYS {new Date().getFullYear()}
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
                      <span className="text-slate-300">{holiday.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4">
            <Calendar className="w-5 h-5 text-cyan-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Holiday Awareness</h3>
            <p className="text-xs text-slate-400">
              Automatically skips federal and state holidays in calculations
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4">
            <Clock className="w-5 h-5 text-amber-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Service Extensions</h3>
            <p className="text-xs text-slate-400">
              Adds correct service days based on Federal vs Florida rules
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4">
            <Info className="w-5 h-5 text-rose-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Full Audit Trail</h3>
            <p className="text-xs text-slate-400">
              Every calculation step logged for professional documentation
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
