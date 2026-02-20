'use client';

import React, { useState } from 'react';
import { Search, FileText, AlertCircle, Sparkles, ExternalLink } from 'lucide-react';
import axios from 'axios';
import apiClient from '@/lib/api-client';

interface Source {
  source_number: number;
  document_id: string;
  document_name: string;
  document_type: string | null;
  chunk_text: string;
  similarity: number;
}

interface RAGResponse {
  question: string;
  answer: string;
  sources: Source[];
  confidence: 'low' | 'medium' | 'high';
  total_sources: number;
}

interface SmartDocumentSearchProps {
  caseId: string;
  onOpenDocument?: (documentId: string) => void;
}

export default function SmartDocumentSearch({ caseId, onOpenDocument }: SmartDocumentSearchProps) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const exampleQuestions = [
    "What was the service date for the complaint?",
    "Find all mentions of expert witness deadlines",
    "What did the judge say about summary judgment?",
    "List all discovery deadlines mentioned in court orders",
    "Summarize the key arguments in the motion to dismiss"
  ];

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.post('/rag/ask', {
        question: query,
        case_id: caseId,
        include_sources: true
      });

      if (response.data.success) {
        setResult(response.data.data);
      } else {
        setError(response.data.message || 'Search failed');
      }
    } catch (err: unknown) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : err instanceof Error ? err.message : 'Failed to search documents';
      setError(message);
      console.error('RAG search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'text-green-600 bg-green-50';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50';
      case 'low':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg">
          <Sparkles className="w-6 h-6 text-blue-600" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Smart Document Search</h2>
          <p className="text-sm text-gray-600">
            Ask questions in natural language. AI will search all case documents and provide answers with citations.
          </p>
        </div>
      </div>

      {/* Search Input */}
      <div className="space-y-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your case documents..."
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={2}
              disabled={loading}
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Searching...</span>
              </div>
            ) : (
              'Ask'
            )}
          </button>
        </div>

        {/* Example Questions */}
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-gray-500 self-center">Try:</span>
          {exampleQuestions.slice(0, 3).map((example, i) => (
            <button
              key={i}
              onClick={() => setQuery(example)}
              className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
              disabled={loading}
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
          <div>
            <p className="font-medium text-red-900">Search Failed</p>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Answer Card */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-blue-900">Answer</h3>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getConfidenceColor(result.confidence)}`}>
                {result.confidence} confidence
              </span>
            </div>
            <div className="prose prose-sm max-w-none text-gray-800">
              {result.answer.split('\n').map((line, i) => (
                <p key={i} className="mb-2 last:mb-0">{line}</p>
              ))}
            </div>
          </div>

          {/* Sources */}
          {result.sources && result.sources.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Sources ({result.sources.length})
              </h3>

              <div className="space-y-3">
                {result.sources.map((source, i) => (
                  <div
                    key={i}
                    className="border-l-4 border-blue-500 bg-white p-4 rounded-r-lg shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="inline-flex items-center justify-center w-6 h-6 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">
                            {source.source_number}
                          </span>
                          <h4 className="font-medium text-gray-900">{source.document_name}</h4>
                          {source.document_type && (
                            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                              {source.document_type}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600">
                          Relevance: {Math.round(source.similarity * 100)}%
                        </p>
                      </div>

                      {onOpenDocument && (
                        <button
                          onClick={() => onOpenDocument(source.document_id)}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded transition-colors"
                        >
                          <span>Open</span>
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      )}
                    </div>

                    <div className="bg-gray-50 p-3 rounded text-sm text-gray-700 italic">
                      "{source.chunk_text}"
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!result && !error && !loading && (
        <div className="text-center py-12 px-4 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Ask a Question About Your Documents
          </h3>
          <p className="text-gray-600 max-w-md mx-auto">
            Use natural language to search across all case documents. The AI will find relevant sections
            and provide answers with exact citations.
          </p>
        </div>
      )}
    </div>
  );
}
