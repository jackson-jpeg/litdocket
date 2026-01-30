'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import {
  FileSearch,
  Brain,
  Tag,
  Hash,
  AlertCircle,
  CheckCircle,
  Clock,
  Users,
  DollarSign,
  Calendar,
  ChevronDown,
  ChevronUp,
  Sparkles,
  RefreshCw,
  Eye,
  FileText,
} from 'lucide-react';

interface ExtractedEntity {
  type: string;
  value: string;
  confidence: number;
  context?: string;
}

interface DocumentAnalysis {
  id: string;
  document_id: string;
  document_type: string;
  classification: {
    primary_type: string;
    confidence: number;
    secondary_types: string[];
  };
  summary: string;
  key_points: string[];
  entities: ExtractedEntity[];
  dates: Array<{
    date: string;
    context: string;
    importance: string;
  }>;
  amounts: Array<{
    amount: string;
    currency: string;
    context: string;
  }>;
  parties_mentioned: Array<{
    name: string;
    role: string;
    mentions: number;
  }>;
  legal_citations: Array<{
    citation: string;
    context: string;
  }>;
  risk_indicators: Array<{
    indicator: string;
    severity: string;
    explanation: string;
  }>;
  analyzed_at: string;
}

interface DocumentIntelligenceProps {
  caseId: string;
  documentId: string;
  documentName: string;
  onAnalysisComplete?: (analysis: DocumentAnalysis) => void;
  className?: string;
}

const ENTITY_ICONS: Record<string, typeof Users> = {
  person: Users,
  organization: FileText,
  date: Calendar,
  money: DollarSign,
  location: FileSearch,
};

const ENTITY_COLORS: Record<string, string> = {
  person: 'bg-blue-100 text-blue-700 border-blue-200',
  organization: 'bg-purple-100 text-purple-700 border-purple-200',
  date: 'bg-green-100 text-green-700 border-green-200',
  money: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  location: 'bg-orange-100 text-orange-700 border-orange-200',
};

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percentage = Math.round(confidence * 100);
  const color =
    percentage >= 90
      ? 'text-green-600'
      : percentage >= 70
      ? 'text-yellow-600'
      : 'text-orange-600';

  return (
    <span className={`text-xs font-medium ${color}`}>{percentage}% confident</span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-green-100 text-green-700',
  };

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[severity] || colors.medium}`}>
      {severity}
    </span>
  );
}

export default function DocumentIntelligence({
  caseId,
  documentId,
  documentName,
  onAnalysisComplete,
  className = '',
}: DocumentIntelligenceProps) {
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [activeSection, setActiveSection] = useState<'summary' | 'entities' | 'risks' | 'citations'>('summary');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (expanded && !analysis && !loading) {
      fetchAnalysis();
    }
  }, [expanded, documentId]);

  const fetchAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(`/api/v1/documents/${documentId}/analysis`);
      if (response.data) {
        setAnalysis(response.data);
        onAnalysisComplete?.(response.data);
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) {
        // No analysis exists yet - that's okay
        setAnalysis(null);
      } else {
        setError('Failed to load analysis');
      }
    } finally {
      setLoading(false);
    }
  };

  const runAnalysis = async () => {
    try {
      setAnalyzing(true);
      setError(null);
      const response = await apiClient.post(`/api/v1/documents/${documentId}/analyze`, {
        extract_entities: true,
        extract_dates: true,
        extract_amounts: true,
        extract_citations: true,
        identify_risks: true,
      });
      setAnalysis(response.data);
      onAnalysisComplete?.(response.data);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Analysis failed. Please try again.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className={`border border-slate-200 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-600" />
          <span className="text-sm font-medium text-slate-900">Document Intelligence</span>
          {analysis && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">
              Analyzed
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-slate-200">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-5 h-5 text-purple-500 animate-spin" />
              <span className="ml-2 text-sm text-slate-500">Loading analysis...</span>
            </div>
          ) : !analysis ? (
            <div className="p-4 text-center">
              <Sparkles className="w-8 h-8 text-purple-400 mx-auto mb-2" />
              <p className="text-sm text-slate-600 mb-3">
                AI-powered analysis extracts key information from this document
              </p>
              {error && (
                <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                  {error}
                </div>
              )}
              <button
                onClick={runAnalysis}
                disabled={analyzing}
                className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                {analyzing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Brain className="w-4 h-4" />
                    Analyze Document
                  </>
                )}
              </button>
            </div>
          ) : (
            <div>
              {/* Section Tabs */}
              <div className="flex border-b border-slate-200 text-xs">
                {(['summary', 'entities', 'risks', 'citations'] as const).map((section) => (
                  <button
                    key={section}
                    onClick={() => setActiveSection(section)}
                    className={`flex-1 px-3 py-2 font-medium capitalize transition-colors ${
                      activeSection === section
                        ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {section}
                  </button>
                ))}
              </div>

              {/* Section Content */}
              <div className="p-4 max-h-80 overflow-y-auto">
                {activeSection === 'summary' && (
                  <div className="space-y-4">
                    {/* Classification */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-slate-500">Document Type</span>
                        <ConfidenceBadge confidence={analysis.classification.confidence} />
                      </div>
                      <div className="flex items-center gap-2">
                        <Tag className="w-4 h-4 text-purple-500" />
                        <span className="font-medium text-slate-900 capitalize">
                          {analysis.classification.primary_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      {analysis.classification.secondary_types.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {analysis.classification.secondary_types.map((type, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs"
                            >
                              {type.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Summary */}
                    <div>
                      <h4 className="text-xs text-slate-500 mb-2">Summary</h4>
                      <p className="text-sm text-slate-700">{analysis.summary}</p>
                    </div>

                    {/* Key Points */}
                    {analysis.key_points && analysis.key_points.length > 0 && (
                      <div>
                        <h4 className="text-xs text-slate-500 mb-2">Key Points</h4>
                        <ul className="space-y-1">
                          {analysis.key_points.map((point, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-slate-700">
                              <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                              {point}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Dates & Amounts */}
                    <div className="grid grid-cols-2 gap-4">
                      {analysis.dates && analysis.dates.length > 0 && (
                        <div>
                          <h4 className="text-xs text-slate-500 mb-2">Important Dates</h4>
                          <div className="space-y-1">
                            {analysis.dates.slice(0, 5).map((date, idx) => (
                              <div key={idx} className="flex items-center gap-2 text-xs">
                                <Calendar className="w-3 h-3 text-green-500" />
                                <span className="font-medium">{date.date}</span>
                                <span className="text-slate-500 truncate">{date.context}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {analysis.amounts && analysis.amounts.length > 0 && (
                        <div>
                          <h4 className="text-xs text-slate-500 mb-2">Monetary Amounts</h4>
                          <div className="space-y-1">
                            {analysis.amounts.slice(0, 5).map((amount, idx) => (
                              <div key={idx} className="flex items-center gap-2 text-xs">
                                <DollarSign className="w-3 h-3 text-yellow-500" />
                                <span className="font-medium">{amount.amount}</span>
                                <span className="text-slate-500 truncate">{amount.context}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {activeSection === 'entities' && (
                  <div className="space-y-3">
                    {/* Parties */}
                    {analysis.parties_mentioned && analysis.parties_mentioned.length > 0 && (
                      <div>
                        <h4 className="text-xs text-slate-500 mb-2">Parties Mentioned</h4>
                        <div className="flex flex-wrap gap-2">
                          {analysis.parties_mentioned.map((party, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs border border-blue-200"
                            >
                              <Users className="w-3 h-3" />
                              {party.name}
                              {party.role && (
                                <span className="text-blue-500">({party.role})</span>
                              )}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Other Entities */}
                    {analysis.entities && analysis.entities.length > 0 && (
                      <div>
                        <h4 className="text-xs text-slate-500 mb-2">Extracted Entities</h4>
                        <div className="space-y-1">
                          {analysis.entities.map((entity, idx) => {
                            const Icon = ENTITY_ICONS[entity.type] || Hash;
                            const colorClass = ENTITY_COLORS[entity.type] || 'bg-slate-100 text-slate-700 border-slate-200';

                            return (
                              <div key={idx} className="flex items-center justify-between text-xs">
                                <span className={`inline-flex items-center gap-1 px-2 py-1 rounded border ${colorClass}`}>
                                  <Icon className="w-3 h-3" />
                                  {entity.value}
                                </span>
                                <span className="text-slate-400">
                                  {Math.round(entity.confidence * 100)}%
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {activeSection === 'risks' && (
                  <div className="space-y-3">
                    {analysis.risk_indicators && analysis.risk_indicators.length > 0 ? (
                      analysis.risk_indicators.map((risk, idx) => (
                        <div
                          key={idx}
                          className={`p-3 rounded-lg border ${
                            risk.severity === 'high'
                              ? 'bg-red-50 border-red-200'
                              : risk.severity === 'medium'
                              ? 'bg-yellow-50 border-yellow-200'
                              : 'bg-green-50 border-green-200'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <AlertCircle
                                className={`w-4 h-4 ${
                                  risk.severity === 'high'
                                    ? 'text-red-500'
                                    : risk.severity === 'medium'
                                    ? 'text-yellow-500'
                                    : 'text-green-500'
                                }`}
                              />
                              <span className="font-medium text-sm text-slate-900">
                                {risk.indicator}
                              </span>
                            </div>
                            <SeverityBadge severity={risk.severity} />
                          </div>
                          <p className="text-xs text-slate-600">{risk.explanation}</p>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-6">
                        <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
                        <p className="text-sm text-slate-500">No risk indicators identified</p>
                      </div>
                    )}
                  </div>
                )}

                {activeSection === 'citations' && (
                  <div className="space-y-2">
                    {analysis.legal_citations && analysis.legal_citations.length > 0 ? (
                      analysis.legal_citations.map((citation, idx) => (
                        <div
                          key={idx}
                          className="p-2 bg-slate-50 rounded border border-slate-200"
                        >
                          <p className="text-sm font-medium text-slate-900">{citation.citation}</p>
                          {citation.context && (
                            <p className="text-xs text-slate-500 mt-1">{citation.context}</p>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-6">
                        <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm text-slate-500">No legal citations found</p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Refresh Button */}
              <div className="p-2 border-t border-slate-200 bg-slate-50">
                <button
                  onClick={runAnalysis}
                  disabled={analyzing}
                  className="w-full flex items-center justify-center gap-2 text-xs text-purple-600 hover:text-purple-700 font-medium"
                >
                  <RefreshCw className={`w-3 h-3 ${analyzing ? 'animate-spin' : ''}`} />
                  {analyzing ? 'Re-analyzing...' : 'Re-analyze Document'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
