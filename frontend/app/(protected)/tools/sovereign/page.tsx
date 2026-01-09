'use client';

/**
 * Sovereign Graph Engine Demo Page
 *
 * Full demonstration of the jurisdictional knowledge graph system:
 * - Jurisdiction tree navigation
 * - Rule set selection with cascading dependencies
 * - Date calculator with holiday awareness
 */

import React, { useState } from 'react';
import { SovereignTreeGrid, SelectionState } from '@/components/sovereign';
import {
  SovereignCalculator,
  calculateFederalDeadline,
  CountingMethod,
  ServiceMethod,
} from '@/lib/sovereign-calculator';

export default function SovereignDemoPage() {
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
    <div className="sovereign-demo">
      <div className="demo-header">
        <h1 className="font-serif text-2xl mb-2">Sovereign Graph Engine</h1>
        <p className="text-ink-secondary text-sm">
          "Graph Theory, Not Code Lists" - The jurisdictional knowledge graph for
          legal deadline management.
        </p>
      </div>

      {/* Main Grid */}
      <div className="demo-grid">
        {/* Left Column: Tree Grid */}
        <div className="tree-section">
          <div className="section-header">
            <h2 className="font-serif">Jurisdiction Navigator</h2>
            <p className="text-xs text-ink-muted">
              Select a court to see applicable rule sets
            </p>
          </div>
          <div className="tree-container">
            <SovereignTreeGrid
              onSelectionChange={handleSelectionChange}
              showRuleDetails={true}
            />
          </div>
        </div>

        {/* Right Column: Calculator */}
        <div className="calculator-section">
          <div className="section-header">
            <h2 className="font-serif">Deadline Calculator</h2>
            <p className="text-xs text-ink-muted">
              Calculate deadlines with holiday awareness
            </p>
          </div>

          <div className="calculator-form panel">
            <div className="panel-header">Calculate Deadline</div>
            <div className="panel-body">
              {/* Trigger Date */}
              <div className="form-group">
                <label className="form-label">Trigger Date</label>
                <input
                  type="date"
                  value={triggerDate}
                  onChange={(e) => setTriggerDate(e.target.value)}
                  className="input"
                />
              </div>

              {/* Days */}
              <div className="form-group">
                <label className="form-label">
                  Days (negative = before trigger)
                </label>
                <input
                  type="number"
                  value={days}
                  onChange={(e) => setDays(parseInt(e.target.value) || 0)}
                  className="input"
                />
              </div>

              {/* Counting Method */}
              <div className="form-group">
                <label className="form-label">Counting Method</label>
                <select
                  value={countingMethod}
                  onChange={(e) =>
                    setCountingMethod(e.target.value as CountingMethod)
                  }
                  className="input"
                >
                  <option value="CALENDAR">Calendar Days</option>
                  <option value="BUSINESS">Business Days</option>
                  <option value="COURT">Court Days</option>
                  <option value="RETROGRADE">Retrograde (Before Trigger)</option>
                </select>
              </div>

              {/* Service Method */}
              <div className="form-group">
                <label className="form-label">Service Method</label>
                <select
                  value={serviceMethod}
                  onChange={(e) =>
                    setServiceMethod(e.target.value as ServiceMethod)
                  }
                  className="input"
                >
                  <option value="PERSONAL">Personal Service (0 days)</option>
                  <option value="CERTIFIED_MAIL">
                    Certified Mail (+3 days Federal, +5 FL)
                  </option>
                  <option value="FIRST_CLASS_MAIL">
                    First Class Mail (+3 days Federal, +5 FL)
                  </option>
                  <option value="ELECTRONIC">Electronic (+3 days Federal, 0 FL)</option>
                </select>
              </div>

              {/* Calculate Button */}
              <button
                onClick={handleCalculate}
                className="btn btn-primary btn-raised w-full mt-4"
              >
                Calculate Deadline
              </button>
            </div>
          </div>

          {/* Calculation Result */}
          {calculationResult && (
            <div className="result-panel panel mt-4">
              <div className="panel-header">
                <span className="font-mono">CALCULATION RESULT</span>
              </div>
              <div className="panel-body">
                {/* Deadline */}
                <div className="result-row highlight">
                  <span className="result-label">DEADLINE DATE:</span>
                  <span className="result-value font-mono text-lg">
                    {calculationResult.deadlineDate.toLocaleDateString('en-US', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </span>
                </div>

                {/* Details */}
                <div className="result-details">
                  <div className="result-row">
                    <span className="result-label">Trigger Date:</span>
                    <span className="result-value font-mono">
                      {calculationResult.triggerDate.toLocaleDateString()}
                    </span>
                  </div>
                  <div className="result-row">
                    <span className="result-label">Base Days:</span>
                    <span className="result-value font-mono">
                      {calculationResult.baseDays}
                    </span>
                  </div>
                  <div className="result-row">
                    <span className="result-label">Service Days Added:</span>
                    <span className="result-value font-mono">
                      +{calculationResult.serviceDaysAdded}
                    </span>
                  </div>
                  <div className="result-row">
                    <span className="result-label">Weekends Skipped:</span>
                    <span className="result-value font-mono">
                      {calculationResult.weekendsSkipped}
                    </span>
                  </div>
                  <div className="result-row">
                    <span className="result-label">Holidays Skipped:</span>
                    <span className="result-value font-mono">
                      {calculationResult.holidaysSkipped}
                    </span>
                  </div>
                  <div className="result-row">
                    <span className="result-label">Counting Method:</span>
                    <span className="result-value font-mono">
                      {calculationResult.countingMethod}
                    </span>
                  </div>
                </div>

                {/* Audit Log */}
                <div className="audit-log">
                  <div className="audit-header">AUDIT LOG</div>
                  {calculationResult.auditLog.map((entry, idx) => (
                    <div key={idx} className="audit-entry">
                      <span className="audit-step">{entry.step}.</span>
                      <span className="audit-action">[{entry.action}]</span>
                      <span className="audit-notes">{entry.notes}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Holiday Calendar */}
          <div className="holiday-panel panel mt-4">
            <div className="panel-header">
              <span>Federal Holidays {new Date().getFullYear()}</span>
            </div>
            <div className="panel-body">
              <div className="holiday-list">
                {holidays.map((holiday, idx) => (
                  <div key={idx} className="holiday-item">
                    <span className="holiday-date font-mono">
                      {holiday.date.toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                    <span className="holiday-name">{holiday.name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Selection Summary */}
      {selection && selection.selectedRuleSets.size > 0 && (
        <div className="selection-summary panel mt-4">
          <div className="panel-header">Selection Summary</div>
          <div className="panel-body">
            <p className="text-sm">
              <strong>{selection.selectedRuleSets.size}</strong> rule sets selected
              (including <strong>{selection.lockedRuleSets.size}</strong> dependencies)
            </p>
          </div>
        </div>
      )}

      {/* Styles */}
      <style jsx>{`
        .sovereign-demo {
          padding: 0;
          max-width: 100%;
        }

        .demo-header {
          margin-bottom: 20px;
          padding-bottom: 16px;
          border-bottom: 2px solid var(--grid-line);
        }

        .demo-grid {
          display: grid;
          grid-template-columns: 1fr 400px;
          gap: 20px;
          height: calc(100vh - 200px);
          min-height: 600px;
        }

        .tree-section {
          display: flex;
          flex-direction: column;
          min-width: 0;
        }

        .calculator-section {
          display: flex;
          flex-direction: column;
          overflow-y: auto;
        }

        .section-header {
          margin-bottom: 12px;
        }

        .section-header h2 {
          font-size: 16px;
          margin-bottom: 4px;
        }

        .tree-container {
          flex: 1;
          min-height: 0;
        }

        .form-group {
          margin-bottom: 12px;
        }

        .form-label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          margin-bottom: 4px;
          color: var(--ink-secondary);
        }

        .result-panel .panel-header {
          background-color: var(--navy);
          color: white;
        }

        .result-row {
          display: flex;
          justify-content: space-between;
          padding: 6px 0;
          border-bottom: 1px solid var(--grid-line);
        }

        .result-row.highlight {
          background-color: #EEF2FF;
          padding: 12px;
          margin: -16px -16px 12px -16px;
          border-bottom: 2px solid var(--navy);
        }

        .result-label {
          font-size: 11px;
          color: var(--ink-secondary);
          text-transform: uppercase;
        }

        .result-value {
          font-weight: 600;
        }

        .result-details {
          margin-top: 12px;
        }

        .audit-log {
          margin-top: 16px;
          padding-top: 12px;
          border-top: 1px solid var(--grid-line);
        }

        .audit-header {
          font-size: 10px;
          font-weight: 600;
          color: var(--ink-muted);
          margin-bottom: 8px;
        }

        .audit-entry {
          font-size: 11px;
          font-family: 'JetBrains Mono', monospace;
          padding: 2px 0;
          color: var(--ink-secondary);
        }

        .audit-step {
          color: var(--ink-muted);
          margin-right: 4px;
        }

        .audit-action {
          color: var(--navy);
          margin-right: 8px;
        }

        .holiday-list {
          max-height: 200px;
          overflow-y: auto;
        }

        .holiday-item {
          display: flex;
          gap: 12px;
          padding: 4px 0;
          font-size: 12px;
          border-bottom: 1px dotted var(--grid-line);
        }

        .holiday-date {
          width: 60px;
          color: var(--ink-muted);
        }

        .selection-summary {
          background-color: #EEF2FF;
        }

        @media (max-width: 1024px) {
          .demo-grid {
            grid-template-columns: 1fr;
            height: auto;
          }

          .tree-container {
            height: 400px;
          }
        }
      `}</style>
    </div>
  );
}
