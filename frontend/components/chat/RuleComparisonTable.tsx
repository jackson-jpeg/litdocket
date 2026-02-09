/**
 * RuleComparisonTable - Side-by-side jurisdiction comparison
 *
 * Phase 4: Chat Integration Component
 *
 * Displays rules from multiple jurisdictions in a comparison table format,
 * highlighting differences in:
 * - Deadline timings
 * - Service extensions
 * - Calculation methods
 * - Authority tiers
 *
 * Follows Paper & Steel design system: gap-px grid technique, zero border-radius
 */

import React, { useState } from 'react';
import { ConfidenceScore } from './ConfidenceBadge';

interface RuleDeadline {
  title: string;
  days_from_trigger: number;
  calculation_method: string;
  priority: string;
}

interface ComparisonRule {
  rule_id: string;
  rule_name: string;
  rule_code: string;
  citation: string;
  deadline_count: number;
  deadlines: RuleDeadline[];
  service_extensions: Record<string, number>;
}

interface JurisdictionComparison {
  jurisdiction_id: string;
  jurisdiction_name: string;
  rule_count: number;
  rules: ComparisonRule[];
}

interface RuleComparisonTableProps {
  comparison: JurisdictionComparison[];
  triggerType: string;
  className?: string;
}

export function RuleComparisonTable({
  comparison,
  triggerType,
  className = ''
}: RuleComparisonTableProps) {
  const [selectedDeadline, setSelectedDeadline] = useState<string | null>(null);

  // Get all unique deadline titles across all jurisdictions
  const getAllDeadlineTitles = (): string[] => {
    const titles = new Set<string>();
    comparison.forEach(jurisdiction => {
      jurisdiction.rules.forEach(rule => {
        rule.deadlines.forEach(deadline => {
          titles.add(deadline.title);
        });
      });
    });
    return Array.from(titles).sort();
  };

  const deadlineTitles = getAllDeadlineTitles();

  // Find deadline in a jurisdiction's rules
  const findDeadline = (jurisdiction: JurisdictionComparison, title: string) => {
    for (const rule of jurisdiction.rules) {
      const deadline = rule.deadlines.find(d => d.title === title);
      if (deadline) {
        return { deadline, rule };
      }
    }
    return null;
  };

  // Calculate differences
  const getDeadlineDiff = (
    deadline1: { days: number } | null,
    deadline2: { days: number } | null
  ): string => {
    if (!deadline1 || !deadline2) return '';
    const diff = deadline1.days - deadline2.days;
    if (diff === 0) return '(same)';
    return diff > 0 ? `(+${diff} days)` : `(${diff} days)`;
  };

  if (comparison.length === 0) {
    return (
      <div className="border-2 border-ink bg-gray-50 p-8 text-center">
        <p className="text-gray-600">No jurisdictions to compare</p>
      </div>
    );
  }

  if (comparison.length === 1) {
    return (
      <div className="border-2 border-ink bg-yellow-50 p-4">
        <p className="text-sm text-yellow-900">
          ⚠ Comparison requires at least 2 jurisdictions. Only showing {comparison[0].jurisdiction_name}.
        </p>
      </div>
    );
  }

  return (
    <div className={`border-2 border-ink bg-white ${className}`}>
      {/* Header */}
      <div className="border-b-2 border-ink bg-gray-50 px-4 py-3">
        <h3 className="font-semibold text-ink">
          {triggerType.replace(/_/g, ' ').toUpperCase()} Rules Comparison
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          Comparing {comparison.length} jurisdictions
        </p>
      </div>

      {/* Jurisdiction Headers */}
      <div className="border-b-2 border-ink grid gap-px bg-ink" style={{ gridTemplateColumns: `200px repeat(${comparison.length}, 1fr)` }}>
        <div className="bg-gray-100 p-3 font-semibold text-sm text-ink">
          DEADLINE TYPE
        </div>
        {comparison.map((jurisdiction) => (
          <div key={jurisdiction.jurisdiction_id} className="bg-gray-100 p-3">
            <p className="font-semibold text-sm text-ink">{jurisdiction.jurisdiction_name}</p>
            <p className="text-xs text-gray-600 mt-0.5">
              {jurisdiction.rule_count} rule(s)
            </p>
          </div>
        ))}
      </div>

      {/* Comparison Rows */}
      <div className="divide-y-2 divide-ink">
        {deadlineTitles.length === 0 ? (
          <div className="p-8 text-center text-gray-600">
            No deadline specifications found for comparison
          </div>
        ) : (
          deadlineTitles.map((title, idx) => {
            const results = comparison.map(j => findDeadline(j, title));
            const hasAnyResult = results.some(r => r !== null);

            if (!hasAnyResult) return null;

            return (
              <div
                key={idx}
                className={`grid gap-px bg-ink cursor-pointer hover:bg-gray-50 transition-colors ${
                  selectedDeadline === title ? 'bg-blue-50' : ''
                }`}
                style={{ gridTemplateColumns: `200px repeat(${comparison.length}, 1fr)` }}
                onClick={() => setSelectedDeadline(selectedDeadline === title ? null : title)}
              >
                {/* Deadline Title */}
                <div className="bg-white p-3">
                  <p className="text-sm font-medium text-ink">{title}</p>
                </div>

                {/* Each Jurisdiction's Value */}
                {results.map((result, jIdx) => {
                  if (!result) {
                    return (
                      <div key={jIdx} className="bg-white p-3">
                        <p className="text-sm text-gray-400 italic">N/A</p>
                      </div>
                    );
                  }

                  const { deadline, rule } = result;
                  const refResult = results.find(r => r !== null);
                  const diff = refResult && refResult.deadline.days_from_trigger !== deadline.days_from_trigger
                    ? getDeadlineDiff(
                        { days: deadline.days_from_trigger },
                        { days: refResult.deadline.days_from_trigger }
                      )
                    : '';

                  return (
                    <div key={jIdx} className="bg-white p-3">
                      <p className="text-sm font-semibold text-ink">
                        {deadline.days_from_trigger} days
                        {diff && <span className="ml-1 text-xs text-gray-500">{diff}</span>}
                      </p>
                      <p className="text-xs text-gray-600 mt-0.5">
                        {deadline.calculation_method}
                      </p>
                      {selectedDeadline === title && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <p className="text-xs font-mono text-gray-600">{rule.rule_code}</p>
                          <p className="text-xs text-gray-500 mt-0.5 font-serif italic">{rule.citation}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })
        )}
      </div>

      {/* Service Extensions Section */}
      <div className="border-t-2 border-ink bg-gray-50 p-4">
        <h4 className="font-semibold text-sm text-ink mb-3">SERVICE EXTENSIONS</h4>
        <div className="grid gap-px bg-ink" style={{ gridTemplateColumns: `repeat(${comparison.length}, 1fr)` }}>
          {comparison.map((jurisdiction) => {
            const hasExtensions = jurisdiction.rules.some(r =>
              r.service_extensions && Object.keys(r.service_extensions).length > 0
            );

            return (
              <div key={jurisdiction.jurisdiction_id} className="bg-white p-3">
                <p className="font-medium text-xs text-gray-600 mb-2">{jurisdiction.jurisdiction_name}</p>
                {!hasExtensions ? (
                  <p className="text-xs text-gray-400 italic">No extensions</p>
                ) : (
                  <div className="space-y-1">
                    {jurisdiction.rules.map((rule, rIdx) => {
                      if (!rule.service_extensions || Object.keys(rule.service_extensions).length === 0) {
                        return null;
                      }

                      return (
                        <div key={rIdx} className="text-xs">
                          {Object.entries(rule.service_extensions).map(([method, days]) => (
                            <div key={method} className="flex justify-between">
                              <span className="text-gray-600 capitalize">{method}:</span>
                              <span className="font-semibold text-ink">+{days} days</span>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary */}
      <div className="border-t-2 border-ink bg-gray-100 px-4 py-3">
        <p className="text-xs text-gray-600">
          💡 <span className="font-semibold">Tip:</span> Click on any row to see rule citations and codes.
          Different jurisdictions may have significant timing variations for the same deadline type.
        </p>
      </div>
    </div>
  );
}

// Simplified comparison view for chat display
export function RuleComparisonSummary({
  comparison,
  triggerType
}: {
  comparison: JurisdictionComparison[];
  triggerType: string;
}) {
  const totalRules = comparison.reduce((sum, j) => sum + j.rule_count, 0);
  const jurisdictionNames = comparison.map(j => j.jurisdiction_name).join(', ');

  return (
    <div className="border-2 border-ink bg-blue-50 p-3">
      <p className="text-sm font-medium text-ink">
        Comparing <span className="font-bold">{triggerType.replace(/_/g, ' ')}</span> rules across {comparison.length} jurisdictions:
      </p>
      <p className="text-sm text-gray-700 mt-1">{jurisdictionNames}</p>
      <p className="text-xs text-gray-600 mt-2">
        Found {totalRules} total rule(s) for comparison
      </p>
    </div>
  );
}
