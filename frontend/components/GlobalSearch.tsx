'use client';

/**
 * GlobalSearch V2 - Command Center
 *
 * Sovereign Design System:
 * - Dark header with terminal-style input
 * - Dense columnar table results
 * - Full keyboard navigation
 * - Zero radius, high density
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api-client';

interface SearchResult {
  query: string;
  cases: any[];
  documents: any[];
  deadlines: any[];
  total_results: number;
}

interface FlatResult {
  type: 'CASE' | 'DOC' | 'DEADLINE';
  id: string;
  case_id?: string;
  identifier: string;
  title: string;
  status: string;
  meta: string;
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
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'CASE' | 'DOC' | 'DEADLINE'>('ALL');
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimer = useRef<NodeJS.Timeout>();
  const resultsContainerRef = useRef<HTMLDivElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Debounced search
  useEffect(() => {
    if (query.length >= 2) {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(performSearch, 200);
    } else {
      setResults(null);
    }
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [query]);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results, activeFilter]);

  const performSearch = async () => {
    if (query.length < 2) return;
    setLoading(true);
    try {
      const response = await apiClient.get('/api/v1/search/', {
        params: { q: query, limit: 50 }
      });
      setResults(response.data);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  // Flatten results into single list for keyboard navigation
  const getFlatResults = useCallback((): FlatResult[] => {
    if (!results) return [];

    const flat: FlatResult[] = [];

    if (activeFilter === 'ALL' || activeFilter === 'CASE') {
      results.cases.forEach(c => flat.push({
        type: 'CASE',
        id: c.id,
        identifier: c.case_number || c.id.slice(0, 8),
        title: c.title || 'Untitled Case',
        status: c.status || 'active',
        meta: c.court || c.jurisdiction || ''
      }));
    }

    if (activeFilter === 'ALL' || activeFilter === 'DOC') {
      results.documents.forEach(d => flat.push({
        type: 'DOC',
        id: d.id,
        case_id: d.case_id,
        identifier: d.file_name?.slice(0, 20) || d.id.slice(0, 8),
        title: d.document_type || d.file_name || 'Document',
        status: d.document_type || 'file',
        meta: d.case_number || ''
      }));
    }

    if (activeFilter === 'ALL' || activeFilter === 'DEADLINE') {
      results.deadlines.forEach(d => flat.push({
        type: 'DEADLINE',
        id: d.id,
        case_id: d.case_id,
        identifier: d.deadline_date ? new Date(d.deadline_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'TBD',
        title: d.title || 'Deadline',
        status: d.priority || 'standard',
        meta: d.case_number || ''
      }));
    }

    return flat;
  }, [results, activeFilter]);

  const flatResults = getFlatResults();

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleClose();
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, flatResults.length - 1));
      scrollToSelected(selectedIndex + 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
      scrollToSelected(selectedIndex - 1);
    } else if (e.key === 'Enter' && flatResults.length > 0) {
      e.preventDefault();
      navigateToResult(flatResults[selectedIndex]);
    } else if (e.key === 'Tab') {
      e.preventDefault();
      // Cycle through filters
      const filters: Array<'ALL' | 'CASE' | 'DOC' | 'DEADLINE'> = ['ALL', 'CASE', 'DOC', 'DEADLINE'];
      const currentIdx = filters.indexOf(activeFilter);
      setActiveFilter(filters[(currentIdx + 1) % filters.length]);
    }
  }, [flatResults, selectedIndex, activeFilter]);

  const scrollToSelected = (index: number) => {
    if (resultsContainerRef.current) {
      const rows = resultsContainerRef.current.querySelectorAll('tr[data-result]');
      if (rows[index]) {
        rows[index].scrollIntoView({ block: 'nearest' });
      }
    }
  };

  const navigateToResult = (result: FlatResult) => {
    if (result.type === 'CASE') {
      router.push(`/cases/${result.id}`);
    } else {
      router.push(`/cases/${result.case_id}`);
    }
    handleClose();
  };

  const handleClose = () => {
    setQuery('');
    setResults(null);
    setActiveFilter('ALL');
    setSelectedIndex(0);
    onClose();
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'CASE': return 'text-cyan-400';
      case 'DOC': return 'text-amber-400';
      case 'DEADLINE': return 'text-rose-400';
      default: return 'text-slate-400';
    }
  };

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'fatal' || s === 'critical') return 'text-red-500';
    if (s === 'important' || s === 'high') return 'text-amber-500';
    if (s === 'active' || s === 'pending') return 'text-emerald-500';
    if (s === 'completed') return 'text-slate-500';
    return 'text-slate-400';
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-start justify-center z-50 pt-16"
      onClick={handleClose}
    >
      <div
        className="bg-slate-900 border border-slate-700 w-full max-w-4xl mx-4 flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Terminal Header */}
        <div className="bg-slate-800 border-b border-slate-700 px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-emerald-400 font-mono text-sm">&gt;_</span>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="search cases, documents, deadlines..."
              className="flex-1 bg-transparent text-white font-mono text-sm placeholder-slate-500 focus:outline-none"
              spellCheck={false}
            />
            {loading && (
              <span className="text-slate-500 font-mono text-xs animate-pulse">SEARCHING...</span>
            )}
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="bg-slate-850 border-b border-slate-700 px-4 py-2 flex items-center gap-1">
          {(['ALL', 'CASE', 'DOC', 'DEADLINE'] as const).map((filter) => {
            const count = filter === 'ALL'
              ? (results?.total_results || 0)
              : filter === 'CASE'
                ? (results?.cases.length || 0)
                : filter === 'DOC'
                  ? (results?.documents.length || 0)
                  : (results?.deadlines.length || 0);

            return (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`px-3 py-1 font-mono text-xs transition-colors ${
                  activeFilter === filter
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {filter} <span className="text-slate-500">({count})</span>
              </button>
            );
          })}
          <span className="ml-auto text-slate-600 font-mono text-xs">TAB to cycle</span>
        </div>

        {/* Results Table */}
        <div
          ref={resultsContainerRef}
          className="flex-1 overflow-y-auto max-h-[400px] bg-slate-900"
        >
          {query.length < 2 && (
            <div className="p-8 text-center">
              <p className="text-slate-500 font-mono text-sm">TYPE TO SEARCH</p>
              <p className="text-slate-600 font-mono text-xs mt-2">min 2 characters</p>
            </div>
          )}

          {query.length >= 2 && !loading && flatResults.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-slate-500 font-mono text-sm">NO RESULTS</p>
              <p className="text-slate-600 font-mono text-xs mt-2">"{query}"</p>
            </div>
          )}

          {flatResults.length > 0 && (
            <table className="w-full font-mono text-sm">
              <thead className="bg-slate-800 sticky top-0">
                <tr className="text-slate-400 text-xs uppercase">
                  <th className="text-left px-4 py-2 w-20">Type</th>
                  <th className="text-left px-4 py-2 w-32">ID</th>
                  <th className="text-left px-4 py-2">Title</th>
                  <th className="text-left px-4 py-2 w-24">Status</th>
                  <th className="text-left px-4 py-2 w-32">Case</th>
                </tr>
              </thead>
              <tbody>
                {flatResults.map((result, idx) => (
                  <tr
                    key={`${result.type}-${result.id}`}
                    data-result
                    onClick={() => navigateToResult(result)}
                    className={`cursor-pointer border-b border-slate-800 transition-colors ${
                      idx === selectedIndex
                        ? 'bg-slate-700 text-white'
                        : 'text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    <td className={`px-4 py-2 ${getTypeColor(result.type)}`}>
                      {result.type}
                    </td>
                    <td className="px-4 py-2 text-slate-400 truncate max-w-[120px]">
                      {result.identifier}
                    </td>
                    <td className="px-4 py-2 truncate max-w-[300px]">
                      {result.title}
                    </td>
                    <td className={`px-4 py-2 ${getStatusColor(result.status)}`}>
                      {result.status.toUpperCase()}
                    </td>
                    <td className="px-4 py-2 text-slate-500 truncate max-w-[120px]">
                      {result.meta || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-800 border-t border-slate-700 px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-4 text-slate-500 font-mono text-xs">
            <span><kbd className="px-1 bg-slate-700 text-slate-300">↑↓</kbd> navigate</span>
            <span><kbd className="px-1 bg-slate-700 text-slate-300">↵</kbd> select</span>
            <span><kbd className="px-1 bg-slate-700 text-slate-300">TAB</kbd> filter</span>
            <span><kbd className="px-1 bg-slate-700 text-slate-300">ESC</kbd> close</span>
          </div>
          {flatResults.length > 0 && (
            <span className="text-slate-500 font-mono text-xs">
              {selectedIndex + 1}/{flatResults.length}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
