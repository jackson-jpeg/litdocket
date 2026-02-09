/**
 * RuleCard - Display Authority Core rule with full metadata
 *
 * Phase 4: Chat Integration Component
 *
 * Shows a court rule from Authority Core with:
 * - Rule code and name
 * - Citation and source URL
 * - Confidence score badge
 * - Authority tier (federal/state/local)
 * - Deadline count
 * - Expandable deadline list
 * - Verification status
 *
 * Follows Paper & Steel design system: zero border-radius, gap-px grid, border-ink
 */

import React, { useState } from 'react';
import { ConfidenceBadge } from './ConfidenceBadge';

interface AuthorityRule {
  rule_id: string;
  rule_code: string;
  rule_name: string;
  citation: string;
  trigger_type: string;
  authority_tier: 'federal' | 'state' | 'local';
  confidence_score: number;
  deadline_count: number;
  deadlines_preview?: Array<{
    title: string;
    days_from_trigger: number;
    calculation_method: string;
    priority: string;
  }>;
  is_verified: boolean;
  source_url?: string;
}

interface RuleCardProps {
  rule: AuthorityRule;
  onUseRule?: (ruleId: string) => void;
  onViewDetails?: (ruleId: string) => void;
  compact?: boolean;
  className?: string;
}

export function RuleCard({
  rule,
  onUseRule,
  onViewDetails,
  compact = false,
  className = ''
}: RuleCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Authority tier badge
  const getTierBadge = () => {
    const tierColors = {
      federal: 'bg-blue-50 border-blue-600 text-blue-900',
      state: 'bg-purple-50 border-purple-600 text-purple-900',
      local: 'bg-gray-50 border-gray-600 text-gray-900'
    };

    return (
      <span className={`px-2 py-0.5 text-xs font-medium border-2 ${tierColors[rule.authority_tier]}`}>
        {rule.authority_tier.toUpperCase()}
      </span>
    );
  };

  // Verification badge
  const getVerificationBadge = () => {
    if (rule.is_verified) {
      return (
        <span className="px-2 py-0.5 text-xs font-medium border-2 bg-green-50 border-green-600 text-green-900">
          ✓ VERIFIED
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-xs font-medium border-2 bg-yellow-50 border-yellow-600 text-yellow-900">
        PENDING
      </span>
    );
  };

  if (compact) {
    return (
      <div className={`border-2 border-ink bg-white p-3 ${className}`}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-sm font-semibold text-ink">
                {rule.rule_code}
              </span>
              {getTierBadge()}
              <ConfidenceBadge score={rule.confidence_score} size="sm" showLabel={false} />
            </div>
            <p className="text-sm text-ink leading-snug">{rule.rule_name}</p>
            <p className="text-xs text-gray-600 mt-1 font-serif italic">{rule.citation}</p>
          </div>
          {onUseRule && (
            <button
              onClick={() => onUseRule(rule.rule_id)}
              className="px-3 py-1 text-sm font-medium border-2 border-ink bg-white hover:bg-gray-50 transition-colors flex-shrink-0"
            >
              Use
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`border-2 border-ink bg-white ${className}`}>
      {/* Header */}
      <div className="border-b-2 border-ink bg-gray-50 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="font-mono text-lg font-bold text-ink">{rule.rule_code}</h3>
              {getTierBadge()}
              {getVerificationBadge()}
            </div>
            <p className="text-base text-ink font-medium leading-snug">{rule.rule_name}</p>
          </div>
          <ConfidenceBadge score={rule.confidence_score} size="lg" />
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* Citation */}
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-1">CITATION</p>
          <p className="font-serif italic text-sm text-ink">{rule.citation}</p>
          {rule.source_url && (
            <a
              href={rule.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline mt-1 inline-block"
            >
              View official source →
            </a>
          )}
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-3 gap-px bg-ink">
          <div className="bg-white p-2">
            <p className="text-xs font-semibold text-gray-500">TRIGGER</p>
            <p className="text-sm text-ink font-medium">{rule.trigger_type.replace(/_/g, ' ')}</p>
          </div>
          <div className="bg-white p-2">
            <p className="text-xs font-semibold text-gray-500">DEADLINES</p>
            <p className="text-sm text-ink font-medium">{rule.deadline_count} deadline(s)</p>
          </div>
          <div className="bg-white p-2">
            <p className="text-xs font-semibold text-gray-500">AUTHORITY</p>
            <p className="text-sm text-ink font-medium capitalize">{rule.authority_tier}</p>
          </div>
        </div>

        {/* Deadlines Preview */}
        {rule.deadlines_preview && rule.deadlines_preview.length > 0 && (
          <div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs font-semibold text-gray-500 hover:text-ink flex items-center gap-1"
            >
              {expanded ? '▼' : '▶'} DEADLINE SPECIFICATIONS ({rule.deadlines_preview.length})
            </button>

            {expanded && (
              <div className="mt-2 space-y-px bg-ink">
                {rule.deadlines_preview.map((deadline, idx) => (
                  <div key={idx} className="bg-white p-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-ink">{deadline.title}</p>
                        <p className="text-xs text-gray-600 mt-0.5">
                          {deadline.days_from_trigger} days ({deadline.calculation_method}) · Priority: {deadline.priority}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="border-t-2 border-ink bg-gray-50 px-4 py-3 flex gap-2">
        {onUseRule && (
          <button
            onClick={() => onUseRule(rule.rule_id)}
            className="px-4 py-2 font-medium border-2 border-ink bg-white hover:bg-gray-100 transition-colors"
          >
            Use This Rule
          </button>
        )}
        {onViewDetails && (
          <button
            onClick={() => onViewDetails(rule.rule_id)}
            className="px-4 py-2 font-medium border-2 border-gray-300 bg-white hover:bg-gray-50 transition-colors"
          >
            View Full Details
          </button>
        )}
      </div>
    </div>
  );
}

// List of Rule Cards
export function RuleCardList({
  rules,
  onUseRule,
  onViewDetails,
  compact = false
}: {
  rules: AuthorityRule[];
  onUseRule?: (ruleId: string) => void;
  onViewDetails?: (ruleId: string) => void;
  compact?: boolean;
}) {
  if (rules.length === 0) {
    return (
      <div className="border-2 border-ink bg-gray-50 p-8 text-center">
        <p className="text-gray-600">No rules found</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {rules.map((rule) => (
        <RuleCard
          key={rule.rule_id}
          rule={rule}
          onUseRule={onUseRule}
          onViewDetails={onViewDetails}
          compact={compact}
        />
      ))}
    </div>
  );
}
