'use client';

/**
 * Phase 7: Math Trail UI Component
 *
 * Displays the complete calculation trail for a deadline, showing:
 * - Base rule and days (e.g., "20 days from Rule 1.140")
 * - Service method extension (e.g., "+5 days for mail service")
 * - Final calculation (e.g., "= 25 days total")
 * - Link to view full rule details
 *
 * This component makes deadline calculation transparent and legally defensible.
 */

import React from 'react';
import { Deadline } from '@/types';

interface CalculationTrailProps {
  deadline: Deadline;
  showFullDetails?: boolean;
  onViewRule?: (ruleId: string) => void;
}

export function CalculationTrail({
  deadline,
  showFullDetails = false,
  onViewRule
}: CalculationTrailProps) {
  // Only show if we have calculation data
  if (!deadline.calculation_basis && !deadline.source_rule_id) {
    return null;
  }

  // Parse service method label
  const getServiceMethodLabel = (method?: string): string => {
    switch (method) {
      case 'mail':
        return '+5 days (Mail Service)';
      case 'electronic':
        return '+0 days (Electronic)';
      case 'hand_delivery':
        return '+0 days (Hand Delivery)';
      default:
        return '';
    }
  };

  const serviceLabel = getServiceMethodLabel(deadline.service_method);

  // Determine extraction source badge
  const getSourceBadge = () => {
    if (deadline.source_rule_id) {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-green-100 text-green-800 border border-green-200">
          Authority Core
        </span>
      );
    }
    if (deadline.extraction_method === 'rule-based') {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-blue-100 text-blue-800 border border-blue-200">
          Rule-Based
        </span>
      );
    }
    if (deadline.extraction_method === 'manual') {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-800 border border-gray-200">
          Manual
        </span>
      );
    }
    return null;
  };

  // Compact mode: Single line with calculation
  if (!showFullDetails) {
    return (
      <div className="mt-1 border-l-2 border-blue-500 pl-2 text-xs text-gray-700">
        {deadline.calculation_basis && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-[11px]">{deadline.calculation_basis}</span>
            {serviceLabel && (
              <span className="px-1 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-medium">
                {serviceLabel}
              </span>
            )}
            {getSourceBadge()}
          </div>
        )}
        {deadline.source_rule_id && onViewRule && (
          <button
            onClick={() => onViewRule(deadline.source_rule_id!)}
            className="text-blue-600 hover:text-blue-800 underline text-[10px] mt-0.5"
          >
            View Rule Details →
          </button>
        )}
      </div>
    );
  }

  // Full details mode: Multi-line breakdown
  return (
    <div className="mt-2 border border-gray-200 bg-gray-50 p-3 text-xs">
      <div className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
        Calculation Trail
        {getSourceBadge()}
      </div>

      {/* Base calculation */}
      {deadline.calculation_basis && (
        <div className="mb-2">
          <div className="text-gray-700">
            <span className="font-mono bg-white px-1 py-0.5 border border-gray-300">
              {deadline.calculation_basis}
            </span>
          </div>
        </div>
      )}

      {/* Service method extension */}
      {deadline.service_method && (
        <div className="mb-2">
          <div className="text-gray-600">
            Service Method: <span className="font-semibold">{deadline.service_method}</span>
          </div>
          {serviceLabel && (
            <div className="mt-1 px-2 py-1 bg-blue-50 border border-blue-200 text-blue-800 inline-block">
              {serviceLabel}
            </div>
          )}
        </div>
      )}

      {/* Calculation type */}
      {deadline.calculation_type && (
        <div className="mb-2 text-gray-600">
          Method: <span className="font-semibold capitalize">{deadline.calculation_type.replace('_', ' ')}</span>
        </div>
      )}

      {/* Days count */}
      {deadline.days_count && (
        <div className="mb-2 text-gray-600">
          Base Days: <span className="font-semibold">{deadline.days_count} days</span>
        </div>
      )}

      {/* Rule citation */}
      {deadline.applicable_rule && (
        <div className="mb-2">
          <div className="text-gray-600">Rule Citation:</div>
          <div className="mt-1 font-mono text-[11px] text-gray-800 bg-white px-2 py-1 border border-gray-300">
            {deadline.applicable_rule}
          </div>
        </div>
      )}

      {/* Rule details link */}
      {deadline.source_rule_id && onViewRule && (
        <div className="mt-3 pt-2 border-t border-gray-300">
          <button
            onClick={() => onViewRule(deadline.source_rule_id!)}
            className="text-sm text-blue-600 hover:text-blue-800 underline font-medium"
          >
            View Full Rule Details →
          </button>
        </div>
      )}

      {/* Confidence indicator */}
      {deadline.confidence_score !== undefined && (
        <div className="mt-3 pt-2 border-t border-gray-300">
          <div className="flex items-center gap-2">
            <span className="text-gray-600">Confidence:</span>
            <div className="flex-1 bg-gray-200 h-2 max-w-[100px]">
              <div
                className={`h-2 ${
                  deadline.confidence_score >= 90
                    ? 'bg-green-500'
                    : deadline.confidence_score >= 70
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
                style={{ width: `${deadline.confidence_score}%` }}
              />
            </div>
            <span className="font-semibold text-gray-900">{deadline.confidence_score}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact inline version for deadline cards
 */
export function CalculationTrailCompact({ deadline }: { deadline: Deadline }) {
  return <CalculationTrail deadline={deadline} showFullDetails={false} />;
}

/**
 * Full details version for modals/expanded views
 */
export function CalculationTrailFull({
  deadline,
  onViewRule
}: {
  deadline: Deadline;
  onViewRule?: (ruleId: string) => void;
}) {
  return <CalculationTrail deadline={deadline} showFullDetails={true} onViewRule={onViewRule} />;
}
