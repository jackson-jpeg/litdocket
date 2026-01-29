'use client';

/**
 * ConflictCard Component
 *
 * Displays a rule conflict between two Authority Core rules,
 * showing the differences and allowing resolution.
 */

import { useState } from 'react';
import {
  AlertTriangle,
  Scale,
  ArrowRight,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
} from 'lucide-react';
import type { RuleConflict, AuthorityRule } from '@/types';

interface ConflictCardProps {
  conflict: RuleConflict;
  ruleA?: AuthorityRule;
  ruleB?: AuthorityRule;
  onResolve: (conflictId: string, resolution: string, winningRuleId?: string) => Promise<void>;
}

const TIER_PRECEDENCE: Record<string, number> = {
  federal: 5,
  state: 4,
  local: 3,
  standing_order: 2,
  firm: 1,
};

const TIER_COLORS: Record<string, { bg: string; text: string }> = {
  federal: { bg: 'bg-purple-100', text: 'text-purple-700' },
  state: { bg: 'bg-blue-100', text: 'text-blue-700' },
  local: { bg: 'bg-green-100', text: 'text-green-700' },
  standing_order: { bg: 'bg-amber-100', text: 'text-amber-700' },
  firm: { bg: 'bg-slate-100', text: 'text-slate-700' },
};

const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  error: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  warning: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
};

export default function ConflictCard({
  conflict,
  ruleA,
  ruleB,
  onResolve,
}: ConflictCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isResolving, setIsResolving] = useState(false);

  const severity = conflict.severity || 'warning';
  const severityStyle = SEVERITY_STYLES[severity] || SEVERITY_STYLES.warning;

  // Determine which rule has higher precedence
  const tierA = ruleA?.authority_tier || 'firm';
  const tierB = ruleB?.authority_tier || 'firm';
  const precedenceA = TIER_PRECEDENCE[tierA] || 0;
  const precedenceB = TIER_PRECEDENCE[tierB] || 0;
  const higherPrecedenceRule = precedenceA >= precedenceB ? ruleA : ruleB;
  const higherPrecedenceId = precedenceA >= precedenceB ? conflict.rule_a_id : conflict.rule_b_id;

  const handleResolve = async (resolution: string, winningRuleId?: string) => {
    setIsResolving(true);
    try {
      await onResolve(conflict.id, resolution, winningRuleId);
    } finally {
      setIsResolving(false);
    }
  };

  const isResolved = conflict.resolution && conflict.resolution !== 'pending';

  return (
    <div className={`rounded-xl border ${severityStyle.border} ${severityStyle.bg} overflow-hidden`}>
      {/* Header */}
      <div className="px-4 py-3 flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${severity === 'error' ? 'bg-red-100' : 'bg-amber-100'}`}>
            <AlertTriangle className={`w-5 h-5 ${severity === 'error' ? 'text-red-600' : 'text-amber-600'}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className={`font-medium ${severityStyle.text}`}>
                {conflict.conflict_type === 'days_mismatch' ? 'Deadline Conflict' :
                 conflict.conflict_type === 'method_mismatch' ? 'Calculation Method Conflict' :
                 'Rule Conflict'}
              </h3>
              {isResolved && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">
                  <CheckCircle className="w-3 h-3" />
                  Resolved
                </span>
              )}
            </div>
            <p className="text-sm text-slate-600 mt-0.5">{conflict.description}</p>
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 rounded-lg hover:bg-white/50 text-slate-500"
        >
          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>

      {/* Rules Comparison */}
      <div className="px-4 pb-3">
        <div className="flex items-center gap-2 text-sm">
          {/* Rule A */}
          <div className="flex-1 p-2 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center gap-2 mb-1">
              <Scale className="w-4 h-4 text-slate-400" />
              <span className="font-medium text-slate-900 truncate">
                {ruleA?.rule_name || 'Rule A'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${TIER_COLORS[tierA]?.bg || 'bg-slate-100'} ${TIER_COLORS[tierA]?.text || 'text-slate-600'}`}>
                {tierA}
              </span>
              {ruleA?.citation && (
                <span className="text-xs text-slate-500 truncate">{ruleA.citation}</span>
              )}
            </div>
          </div>

          <ArrowRight className="w-4 h-4 text-slate-400 flex-shrink-0" />

          {/* Rule B */}
          <div className="flex-1 p-2 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center gap-2 mb-1">
              <Scale className="w-4 h-4 text-slate-400" />
              <span className="font-medium text-slate-900 truncate">
                {ruleB?.rule_name || 'Rule B'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${TIER_COLORS[tierB]?.bg || 'bg-slate-100'} ${TIER_COLORS[tierB]?.text || 'text-slate-600'}`}>
                {tierB}
              </span>
              {ruleB?.citation && (
                <span className="text-xs text-slate-500 truncate">{ruleB.citation}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-slate-200/50 pt-4">
          {/* Detailed Comparison */}
          <div className="grid grid-cols-2 gap-4">
            {/* Rule A Details */}
            <div className="bg-white rounded-lg p-3 border border-slate-200">
              <h4 className="text-sm font-medium text-slate-900 mb-2">
                {ruleA?.rule_name || 'Rule A'}
              </h4>
              {ruleA?.deadlines && ruleA.deadlines.length > 0 && (
                <div className="space-y-1.5">
                  {ruleA.deadlines.slice(0, 3).map((d, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="text-slate-600 truncate">{d.title}</span>
                      <span className="flex items-center gap-1 text-slate-500">
                        <Clock className="w-3 h-3" />
                        {d.days_from_trigger > 0 ? '+' : ''}{d.days_from_trigger}d
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {ruleA?.source_text && (
                <div className="mt-2 pt-2 border-t border-slate-100">
                  <p className="text-xs text-slate-500 line-clamp-3">{ruleA.source_text}</p>
                </div>
              )}
            </div>

            {/* Rule B Details */}
            <div className="bg-white rounded-lg p-3 border border-slate-200">
              <h4 className="text-sm font-medium text-slate-900 mb-2">
                {ruleB?.rule_name || 'Rule B'}
              </h4>
              {ruleB?.deadlines && ruleB.deadlines.length > 0 && (
                <div className="space-y-1.5">
                  {ruleB.deadlines.slice(0, 3).map((d, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="text-slate-600 truncate">{d.title}</span>
                      <span className="flex items-center gap-1 text-slate-500">
                        <Clock className="w-3 h-3" />
                        {d.days_from_trigger > 0 ? '+' : ''}{d.days_from_trigger}d
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {ruleB?.source_text && (
                <div className="mt-2 pt-2 border-t border-slate-100">
                  <p className="text-xs text-slate-500 line-clamp-3">{ruleB.source_text}</p>
                </div>
              )}
            </div>
          </div>

          {/* Resolution Actions */}
          {!isResolved && (
            <div className="bg-white rounded-lg p-3 border border-slate-200">
              <h4 className="text-sm font-medium text-slate-900 mb-3">Resolve Conflict</h4>
              <div className="flex flex-wrap gap-2">
                {/* Use Higher Tier */}
                {precedenceA !== precedenceB && (
                  <button
                    onClick={() => handleResolve('use_higher_tier', higherPrecedenceId)}
                    disabled={isResolving}
                    className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    <Scale className="w-4 h-4" />
                    Use {higherPrecedenceRule?.authority_tier || 'higher'} tier rule
                  </button>
                )}

                {/* Choose Rule A */}
                <button
                  onClick={() => handleResolve('manual', conflict.rule_a_id)}
                  disabled={isResolving}
                  className="flex items-center gap-2 px-3 py-2 bg-slate-100 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
                >
                  <CheckCircle className="w-4 h-4" />
                  Use {ruleA?.rule_name || 'Rule A'}
                </button>

                {/* Choose Rule B */}
                <button
                  onClick={() => handleResolve('manual', conflict.rule_b_id)}
                  disabled={isResolving}
                  className="flex items-center gap-2 px-3 py-2 bg-slate-100 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
                >
                  <CheckCircle className="w-4 h-4" />
                  Use {ruleB?.rule_name || 'Rule B'}
                </button>

                {/* Dismiss */}
                <button
                  onClick={() => handleResolve('dismissed')}
                  disabled={isResolving}
                  className="flex items-center gap-2 px-3 py-2 text-slate-500 text-sm font-medium rounded-lg hover:bg-slate-100 transition-colors disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  Dismiss
                </button>
              </div>

              {/* Recommendation */}
              {precedenceA !== precedenceB && (
                <p className="mt-3 text-xs text-slate-500 flex items-center gap-1">
                  <FileText className="w-3 h-3" />
                  Recommendation: Higher-tier rules ({precedenceA > precedenceB ? tierA : tierB}) generally take precedence
                </p>
              )}
            </div>
          )}

          {/* Resolution Info */}
          {isResolved && (
            <div className="bg-green-50 rounded-lg p-3 border border-green-200">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-green-800">
                  Resolved: {conflict.resolution}
                </span>
              </div>
              {conflict.resolved_at && (
                <p className="text-xs text-green-600 mt-1">
                  {new Date(conflict.resolved_at).toLocaleDateString()}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
