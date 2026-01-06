'use client';

import { useState, useEffect, useRef } from 'react';
import { Search, X, FileText, Calendar, Folder, Loader2, ExternalLink } from 'lucide-react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api-client';

interface SearchResult {
  query: string;
  cases: any[];
  documents: any[];
  deadlines: any[];
  total_results: number;
}

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function GlobalSearch({ isOpen, onClose }: GlobalSearchProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'cases' | 'documents' | 'deadlines'>('all');
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimer = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (query.length >= 2) {
      // Debounce search
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }

      debounceTimer.current = setTimeout(() => {
        performSearch();
      }, 300);
    } else {
      setResults(null);
    }

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [query]);

  const performSearch = async () => {
    if (query.length < 2) return;

    setLoading(true);
    try {
      const response = await apiClient.get('/api/v1/search/', {
        params: { q: query, limit: 20 }
      });
      setResults(response.data);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setQuery('');
    setResults(null);
    setActiveTab('all');
    onClose();
  };

  const handleResultClick = (type: string, id: string) => {
    if (type === 'case') {
      router.push(`/cases/${id}`);
    } else if (type === 'document' || type === 'deadline') {
      // Navigate to the case (documents and deadlines belong to cases)
      const item = type === 'document'
        ? results?.documents.find(d => d.id === id)
        : results?.deadlines.find(d => d.id === id);
      if (item?.case_id) {
        router.push(`/cases/${item.case_id}`);
      }
    }
    handleClose();
  };

  const getVisibleResults = () => {
    if (!results) return { cases: [], documents: [], deadlines: [] };

    switch (activeTab) {
      case 'cases':
        return { cases: results.cases, documents: [], deadlines: [] };
      case 'documents':
        return { cases: [], documents: results.documents, deadlines: [] };
      case 'deadlines':
        return { cases: [], documents: [], deadlines: results.deadlines };
      default:
        return results;
    }
  };

  if (!isOpen) return null;

  const visibleResults = getVisibleResults();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 pt-20" onClick={handleClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl mx-4 max-h-[600px] flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Search Input */}
        <div className="p-4 border-b border-slate-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search cases, documents, deadlines..."
              className="w-full pl-10 pr-10 py-3 text-lg border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 p-1 hover:bg-slate-100 rounded"
              >
                <X className="w-4 h-4 text-slate-400" />
              </button>
            )}
          </div>

          {/* Tabs */}
          {results && (
            <div className="flex items-center gap-2 mt-3">
              <button
                onClick={() => setActiveTab('all')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'all'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                All ({results.total_results})
              </button>
              <button
                onClick={() => setActiveTab('cases')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'cases'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                Cases ({results.cases.length})
              </button>
              <button
                onClick={() => setActiveTab('documents')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'documents'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                Documents ({results.documents.length})
              </button>
              <button
                onClick={() => setActiveTab('deadlines')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'deadlines'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                Deadlines ({results.deadlines.length})
              </button>
            </div>
          )}
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            </div>
          )}

          {!loading && query.length < 2 && (
            <div className="text-center py-12">
              <Search className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500">Type at least 2 characters to search</p>
            </div>
          )}

          {!loading && query.length >= 2 && results && results.total_results === 0 && (
            <div className="text-center py-12">
              <Search className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500">No results found for "{query}"</p>
            </div>
          )}

          {!loading && results && results.total_results > 0 && (
            <div className="space-y-4">
              {/* Cases */}
              {visibleResults.cases.length > 0 && (
                <div>
                  {activeTab === 'all' && (
                    <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                      <Folder className="w-4 h-4" />
                      Cases
                    </h3>
                  )}
                  <div className="space-y-2">
                    {visibleResults.cases.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => handleResultClick('case', item.id)}
                        className="w-full text-left p-3 border border-slate-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-slate-900">{item.case_number}</p>
                            <p className="text-sm text-slate-600 mt-0.5">{item.title}</p>
                            <p className="text-xs text-slate-500 mt-1">{item.court}</p>
                          </div>
                          <ExternalLink className="w-4 h-4 text-slate-400" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Documents */}
              {visibleResults.documents.length > 0 && (
                <div>
                  {activeTab === 'all' && (
                    <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Documents
                    </h3>
                  )}
                  <div className="space-y-2">
                    {visibleResults.documents.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => handleResultClick('document', item.id)}
                        className="w-full text-left p-3 border border-slate-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-slate-900 text-sm">{item.file_name}</p>
                            {item.document_type && (
                              <span className="inline-block mt-1 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                                {item.document_type}
                              </span>
                            )}
                            {item.ai_summary && (
                              <p className="text-xs text-slate-500 mt-1 line-clamp-2">{item.ai_summary}</p>
                            )}
                            {item.case_number && (
                              <p className="text-xs text-slate-400 mt-1">Case: {item.case_number}</p>
                            )}
                          </div>
                          <ExternalLink className="w-4 h-4 text-slate-400" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Deadlines */}
              {visibleResults.deadlines.length > 0 && (
                <div>
                  {activeTab === 'all' && (
                    <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      Deadlines
                    </h3>
                  )}
                  <div className="space-y-2">
                    {visibleResults.deadlines.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => handleResultClick('deadline', item.id)}
                        className="w-full text-left p-3 border border-slate-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-slate-900 text-sm">{item.title}</p>
                            <div className="flex items-center gap-2 mt-1">
                              {item.deadline_date && (
                                <span className="text-xs text-slate-600">
                                  {new Date(item.deadline_date).toLocaleDateString()}
                                </span>
                              )}
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                item.priority === 'fatal' || item.priority === 'critical'
                                  ? 'bg-red-100 text-red-700'
                                  : item.priority === 'important' || item.priority === 'high'
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-blue-100 text-blue-700'
                              }`}>
                                {item.priority}
                              </span>
                            </div>
                            {item.case_number && (
                              <p className="text-xs text-slate-400 mt-1">Case: {item.case_number}</p>
                            )}
                          </div>
                          <ExternalLink className="w-4 h-4 text-slate-400" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-200 bg-slate-50 rounded-b-xl">
          <p className="text-xs text-slate-500 text-center">
            Press <kbd className="px-2 py-0.5 bg-white border border-slate-300 rounded text-xs">ESC</kbd> to close
          </p>
        </div>
      </div>
    </div>
  );
}
