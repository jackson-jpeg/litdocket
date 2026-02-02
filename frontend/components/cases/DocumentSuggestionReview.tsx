'use client';

import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api-client';
import {
  Lightbulb,
  Calendar,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Zap,
  FileText,
  Clock,
  RefreshCw,
} from 'lucide-react';
import type {
  DeadlineSuggestion,
  SuggestionListResponse,
  ApplySuggestionsResponse,
  CasePendingSuggestions,
} from '@/types';

interface DocumentSuggestionReviewProps {
  caseId: string;
  documentId?: string;
  onSuggestionsApplied?: () => void;
  className?: string;
  compact?: boolean;
}

function ConfidenceBadge({ score }: { score: number }) {
  const getStyle = () => {
    if (score >= 75) return 'bg-green-100 text-green-700 ring-green-400';
    if (score >= 50) return 'bg-yellow-100 text-yellow-700 ring-yellow-400';
    return 'bg-orange-100 text-orange-700 ring-orange-400';
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ring-1 ${getStyle()}`}>
      {score}%
    </span>
  );
}

function SuggestionCard({
  suggestion,
  onApprove,
  onReject,
  isProcessing,
}: {
  suggestion: DeadlineSuggestion;
  onApprove: (applyAsTrigger: boolean) => void;
  onReject: () => void;
  isProcessing: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const isTrigger = suggestion.extraction_method === 'trigger_detected';

  const getExtractionIcon = () => {
    switch (suggestion.extraction_method) {
      case 'trigger_detected':
        return <Zap className="w-4 h-4 text-purple-500" />;
      case 'ai_key_dates':
        return <Calendar className="w-4 h-4 text-blue-500" />;
      default:
        return <FileText className="w-4 h-4 text-slate-500" />;
    }
  };

  const getExtractionLabel = () => {
    switch (suggestion.extraction_method) {
      case 'trigger_detected':
        return 'Trigger Detected';
      case 'ai_key_dates':
        return 'Key Date';
      case 'ai_deadlines_mentioned':
        return 'Deadline Mentioned';
      default:
        return 'Extracted';
    }
  };

  return (
    <div className={`border rounded-lg p-4 ${isTrigger ? 'border-purple-200 bg-purple-50/50' : 'border-slate-200 bg-white'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="mt-0.5">{getExtractionIcon()}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                {getExtractionLabel()}
              </span>
              <ConfidenceBadge score={suggestion.confidence_score} />
              {suggestion.rule_citation && (
                <span className="text-xs text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                  {suggestion.rule_citation}
                </span>
              )}
            </div>
            <h4 className="font-medium text-slate-900 mt-1 truncate">{suggestion.title}</h4>
            {suggestion.suggested_date && (
              <p className="text-sm text-slate-600 flex items-center gap-1.5 mt-1">
                <Clock className="w-3.5 h-3.5" />
                {new Date(suggestion.suggested_date).toLocaleDateString('en-US', {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {!isProcessing ? (
            <>
              {isTrigger ? (
                <button
                  onClick={() => onApprove(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 transition-colors"
                  title="Apply as trigger to generate all related deadlines"
                >
                  <Zap className="w-3.5 h-3.5" />
                  Apply Trigger
                </button>
              ) : (
                <button
                  onClick={() => onApprove(false)}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
                  title="Create deadline from this suggestion"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={onReject}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-slate-500 hover:text-red-600 hover:bg-red-50 text-sm rounded-md transition-colors"
                title="Dismiss suggestion"
              >
                <XCircle className="w-3.5 h-3.5" />
              </button>
            </>
          ) : (
            <RefreshCw className="w-4 h-4 text-slate-400 animate-spin" />
          )}
        </div>
      </div>

      {suggestion.description && suggestion.description !== suggestion.title && (
        <div className="mt-2">
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
                <ChevronDown className="w-3 h-3" /> Show details
              </>
            )}
          </button>
          {expanded && (
            <p className="text-sm text-slate-600 mt-2 pl-7">{suggestion.description}</p>
          )}
        </div>
      )}

      {isTrigger && suggestion.confidence_factors?.expected_deadlines && (
        <p className="text-xs text-purple-600 mt-2 pl-7 font-medium">
          Will generate {suggestion.confidence_factors.expected_deadlines} deadline(s)
        </p>
      )}
    </div>
  );
}

export default function DocumentSuggestionReview({
  caseId,
  documentId,
  onSuggestionsApplied,
  className = '',
  compact = false,
}: DocumentSuggestionReviewProps) {
  const [suggestions, setSuggestions] = useState<DeadlineSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState(!compact);

  const fetchSuggestions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      let response;
      if (documentId) {
        response = await apiClient.get<SuggestionListResponse>(
          `/documents/${documentId}/suggestions?status=pending`
        );
        setSuggestions(response.data.suggestions);
      } else {
        response = await apiClient.get<CasePendingSuggestions>(
          `/documents/cases/${caseId}/pending-suggestions`
        );
        setSuggestions(response.data.suggestions);
      }
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
      setError('Failed to load suggestions');
    } finally {
      setLoading(false);
    }
  }, [caseId, documentId]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  const handleApprove = async (suggestion: DeadlineSuggestion, applyAsTrigger: boolean) => {
    setProcessingIds((prev) => new Set(prev).add(suggestion.id));

    try {
      const response = await apiClient.post<ApplySuggestionsResponse>(
        `/documents/${suggestion.document_id}/apply-deadlines`,
        {
          suggestions: [
            {
              suggestion_id: suggestion.id,
              apply_as_trigger: applyAsTrigger,
            },
          ],
        }
      );

      if (response.data.success) {
        // Remove from list
        setSuggestions((prev) => prev.filter((s) => s.id !== suggestion.id));
        onSuggestionsApplied?.();
      }
    } catch (err) {
      console.error('Failed to apply suggestion:', err);
    } finally {
      setProcessingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(suggestion.id);
        return newSet;
      });
    }
  };

  const handleReject = async (suggestion: DeadlineSuggestion) => {
    setProcessingIds((prev) => new Set(prev).add(suggestion.id));

    try {
      await apiClient.patch(`/documents/suggestions/${suggestion.id}`, {
        status: 'rejected',
      });

      // Remove from list
      setSuggestions((prev) => prev.filter((s) => s.id !== suggestion.id));
    } catch (err) {
      console.error('Failed to reject suggestion:', err);
    } finally {
      setProcessingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(suggestion.id);
        return newSet;
      });
    }
  };

  // Don't render if no suggestions
  if (!loading && suggestions.length === 0) {
    return null;
  }

  const triggerSuggestions = suggestions.filter((s) => s.extraction_method === 'trigger_detected');
  const otherSuggestions = suggestions.filter((s) => s.extraction_method !== 'trigger_detected');

  return (
    <div className={`${className}`}>
      {compact && suggestions.length > 0 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-amber-500" />
            <span className="font-medium text-amber-800">
              {suggestions.length} deadline suggestion{suggestions.length !== 1 ? 's' : ''} pending review
            </span>
          </div>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-amber-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-amber-500" />
          )}
        </button>
      )}

      {(expanded || !compact) && (
        <div className={`space-y-4 ${compact ? 'mt-4' : ''}`}>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-5 h-5 text-slate-400 animate-spin" />
              <span className="ml-2 text-slate-500">Loading suggestions...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-red-600 py-4">
              <AlertTriangle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          ) : (
            <>
              {!compact && suggestions.length > 0 && (
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="w-5 h-5 text-amber-500" />
                  <h3 className="font-semibold text-slate-800">
                    Pending Deadline Suggestions ({suggestions.length})
                  </h3>
                </div>
              )}

              {triggerSuggestions.length > 0 && (
                <div className="space-y-2">
                  {!compact && triggerSuggestions.length > 0 && otherSuggestions.length > 0 && (
                    <h4 className="text-sm font-medium text-purple-700 flex items-center gap-1.5">
                      <Zap className="w-4 h-4" /> Trigger Events
                    </h4>
                  )}
                  {triggerSuggestions.map((suggestion) => (
                    <SuggestionCard
                      key={suggestion.id}
                      suggestion={suggestion}
                      onApprove={(asTrigger) => handleApprove(suggestion, asTrigger)}
                      onReject={() => handleReject(suggestion)}
                      isProcessing={processingIds.has(suggestion.id)}
                    />
                  ))}
                </div>
              )}

              {otherSuggestions.length > 0 && (
                <div className="space-y-2">
                  {!compact && triggerSuggestions.length > 0 && otherSuggestions.length > 0 && (
                    <h4 className="text-sm font-medium text-slate-600 flex items-center gap-1.5 mt-4">
                      <Calendar className="w-4 h-4" /> Dates & Deadlines
                    </h4>
                  )}
                  {otherSuggestions.map((suggestion) => (
                    <SuggestionCard
                      key={suggestion.id}
                      suggestion={suggestion}
                      onApprove={(asTrigger) => handleApprove(suggestion, asTrigger)}
                      onReject={() => handleReject(suggestion)}
                      isProcessing={processingIds.has(suggestion.id)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
