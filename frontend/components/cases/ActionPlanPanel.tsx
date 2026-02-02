'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/api-client';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  X,
  FileText,
  Calculator,
  MessageSquare,
  Calendar,
  RefreshCw,
  Zap,
  Scale,
  BookOpen,
} from 'lucide-react';
import type {
  ActionPlanResponse,
  EnhancedRecommendation,
  UrgencyLevel,
  SuggestedTool,
} from '@/types';

interface ActionPlanPanelProps {
  caseId: string;
  onActionTaken?: () => void;
  className?: string;
}

const urgencyConfig: Record<UrgencyLevel, { bg: string; border: string; text: string; icon: React.ReactNode }> = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-700',
    icon: <AlertTriangle className="w-4 h-4 text-red-600" />,
  },
  high: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    text: 'text-orange-700',
    icon: <Zap className="w-4 h-4 text-orange-500" />,
  },
  medium: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    text: 'text-yellow-700',
    icon: <Clock className="w-4 h-4 text-yellow-600" />,
  },
  low: {
    bg: 'bg-slate-50',
    border: 'border-slate-200',
    text: 'text-slate-600',
    icon: <FileText className="w-4 h-4 text-slate-500" />,
  },
};

function getToolIcon(tool: string) {
  switch (tool) {
    case 'deadline-calculator':
      return <Calculator className="w-3.5 h-3.5" />;
    case 'ai-assistant':
      return <MessageSquare className="w-3.5 h-3.5" />;
    case 'calendar':
      return <Calendar className="w-3.5 h-3.5" />;
    case 'document-analyzer':
      return <FileText className="w-3.5 h-3.5" />;
    default:
      return <ExternalLink className="w-3.5 h-3.5" />;
  }
}

function getToolLink(tool: string, caseId: string): string {
  switch (tool) {
    case 'deadline-calculator':
      return '/tools/deadline-calculator';
    case 'ai-assistant':
      return `/ai-assistant?case=${caseId}`;
    case 'calendar':
      return '/calendar';
    case 'document-analyzer':
      return '/tools/document-analyzer';
    default:
      return '#';
  }
}

function RecommendationCard({
  recommendation,
  caseId,
  onComplete,
  onDismiss,
  isProcessing,
}: {
  recommendation: EnhancedRecommendation;
  caseId: string;
  onComplete: () => void;
  onDismiss: () => void;
  isProcessing: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const config = urgencyConfig[recommendation.urgency_level];

  return (
    <div className={`border rounded-lg p-4 ${config.bg} ${config.border}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="mt-0.5">{config.icon}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-xs font-semibold uppercase tracking-wide ${config.text}`}>
                {recommendation.urgency_level}
              </span>
              <span className="text-xs text-slate-500 bg-white/80 px-1.5 py-0.5 rounded capitalize">
                {recommendation.category}
              </span>
              {recommendation.days_until_consequence !== null &&
                recommendation.days_until_consequence !== undefined &&
                recommendation.days_until_consequence <= 7 && (
                  <span className="text-xs font-medium text-red-600">
                    {recommendation.days_until_consequence === 0
                      ? 'OVERDUE'
                      : `${recommendation.days_until_consequence} day(s)`}
                  </span>
                )}
            </div>
            <h4 className="font-medium text-slate-900 mt-1">{recommendation.action}</h4>

            {recommendation.rule_citations && recommendation.rule_citations.length > 0 && (
              <div className="flex items-center gap-1.5 mt-1.5">
                <BookOpen className="w-3 h-3 text-slate-400" />
                <span className="text-xs text-slate-500">
                  {recommendation.rule_citations.join(', ')}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {!isProcessing ? (
            <>
              <button
                onClick={onComplete}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors"
                title="Mark as complete"
              >
                <CheckCircle className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={onDismiss}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-slate-500 hover:text-slate-700 hover:bg-white/50 text-sm rounded-md transition-colors"
                title="Dismiss"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </>
          ) : (
            <RefreshCw className="w-4 h-4 text-slate-400 animate-spin" />
          )}
        </div>
      </div>

      {/* Expandable details */}
      <div className="mt-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3 h-3" /> Hide details
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" /> Show details & actions
            </>
          )}
        </button>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-slate-200/50 space-y-3">
            {recommendation.reasoning && (
              <p className="text-sm text-slate-600">{recommendation.reasoning}</p>
            )}

            {recommendation.consequence_if_ignored && (
              <div className="bg-red-100/50 rounded p-2">
                <p className="text-xs font-medium text-red-700 mb-1">If Ignored:</p>
                <p className="text-sm text-red-600">{recommendation.consequence_if_ignored}</p>
              </div>
            )}

            {recommendation.triggered_by_deadline && (
              <div className="bg-white/50 rounded p-2">
                <p className="text-xs font-medium text-slate-500 mb-1">Linked Deadline:</p>
                <p className="text-sm text-slate-700 font-medium">
                  {recommendation.triggered_by_deadline.title}
                </p>
                {recommendation.triggered_by_deadline.deadline_date && (
                  <p className="text-xs text-slate-500">
                    Due:{' '}
                    {new Date(recommendation.triggered_by_deadline.deadline_date).toLocaleDateString(
                      'en-US',
                      { weekday: 'short', month: 'short', day: 'numeric' }
                    )}
                  </p>
                )}
              </div>
            )}

            {/* Suggested Tools */}
            {recommendation.suggested_tools && recommendation.suggested_tools.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-2">Suggested Actions:</p>
                <div className="flex flex-wrap gap-2">
                  {recommendation.suggested_tools.map((tool: SuggestedTool, idx: number) => (
                    <Link
                      key={idx}
                      href={getToolLink(tool.tool, caseId)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-md text-sm text-slate-700 hover:bg-slate-50 hover:border-blue-300 transition-colors"
                    >
                      {getToolIcon(tool.tool)}
                      <span>{tool.action}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested Document Types */}
            {recommendation.suggested_document_types &&
              recommendation.suggested_document_types.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-2">Documents to Prepare:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {recommendation.suggested_document_types.map((docType: string, idx: number) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-white border border-slate-200 rounded text-xs text-slate-600"
                      >
                        {docType}
                      </span>
                    ))}
                  </div>
                </div>
              )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ActionPlanPanel({
  caseId,
  onActionTaken,
  className = '',
}: ActionPlanPanelProps) {
  const [actionPlan, setActionPlan] = useState<ActionPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());
  const [collapsed, setCollapsed] = useState(false);

  const fetchActionPlan = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get<ActionPlanResponse>(
        `/api/v1/case-intelligence/cases/${caseId}/action-plan`
      );
      setActionPlan(response.data);
    } catch (err) {
      console.error('Failed to fetch action plan:', err);
      setError('Failed to load action plan');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchActionPlan();
  }, [fetchActionPlan]);

  const handleComplete = async (recId: string) => {
    setProcessingIds((prev) => new Set(prev).add(recId));
    try {
      await apiClient.patch(`/api/v1/case-intelligence/recommendations/${recId}`, {
        status: 'completed',
      });
      // Remove from local state
      if (actionPlan) {
        setActionPlan({
          ...actionPlan,
          recommendations: actionPlan.recommendations.filter((r) => r.id !== recId),
          total_recommendations: actionPlan.total_recommendations - 1,
        });
      }
      onActionTaken?.();
    } catch (err) {
      console.error('Failed to complete recommendation:', err);
    } finally {
      setProcessingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(recId);
        return newSet;
      });
    }
  };

  const handleDismiss = async (recId: string) => {
    setProcessingIds((prev) => new Set(prev).add(recId));
    try {
      await apiClient.patch(`/api/v1/case-intelligence/recommendations/${recId}`, {
        status: 'dismissed',
      });
      // Remove from local state
      if (actionPlan) {
        setActionPlan({
          ...actionPlan,
          recommendations: actionPlan.recommendations.filter((r) => r.id !== recId),
          total_recommendations: actionPlan.total_recommendations - 1,
        });
      }
    } catch (err) {
      console.error('Failed to dismiss recommendation:', err);
    } finally {
      setProcessingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(recId);
        return newSet;
      });
    }
  };

  // Don't render if no recommendations
  if (!loading && (!actionPlan || actionPlan.total_recommendations === 0)) {
    return (
      <div className={`card ${className}`}>
        <div className="flex items-center gap-2 text-green-600">
          <CheckCircle className="w-5 h-5" />
          <span className="font-medium">Case is healthy - no action items</span>
        </div>
      </div>
    );
  }

  const hasCritical = actionPlan && actionPlan.by_urgency.critical > 0;

  return (
    <div className={`card ${className} ${hasCritical ? 'ring-2 ring-red-300' : ''}`}>
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-3">
          <Scale className="w-5 h-5 text-blue-600" />
          <div>
            <h3 className="font-semibold text-slate-800">Action Plan</h3>
            {actionPlan && (
              <p className="text-sm text-slate-500">
                {actionPlan.total_recommendations} item{actionPlan.total_recommendations !== 1 ? 's' : ''} requiring attention
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {actionPlan && (
            <div className="flex items-center gap-1.5">
              {actionPlan.by_urgency.critical > 0 && (
                <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded">
                  {actionPlan.by_urgency.critical} Critical
                </span>
              )}
              {actionPlan.by_urgency.high > 0 && (
                <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-medium rounded">
                  {actionPlan.by_urgency.high} High
                </span>
              )}
            </div>
          )}
          {collapsed ? (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </div>

      {!collapsed && (
        <div className="mt-4 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <RefreshCw className="w-5 h-5 text-slate-400 animate-spin" />
              <span className="ml-2 text-slate-500">Loading action plan...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-red-600 py-4">
              <AlertTriangle className="w-5 h-5" />
              <span>{error}</span>
              <button onClick={fetchActionPlan} className="ml-auto text-blue-600 hover:underline text-sm">
                Retry
              </button>
            </div>
          ) : (
            actionPlan?.recommendations.map((rec) => (
              <RecommendationCard
                key={rec.id}
                recommendation={rec}
                caseId={caseId}
                onComplete={() => handleComplete(rec.id)}
                onDismiss={() => handleDismiss(rec.id)}
                isProcessing={processingIds.has(rec.id)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
