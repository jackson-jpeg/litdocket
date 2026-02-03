'use client';

/**
 * GlobalSearch - Command Palette
 *
 * Paper & Steel Design System:
 * - Clean white modal with slate text
 * - Professional list-based results
 * - Full keyboard navigation
 * - Spacious and readable
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
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
      case 'CASE': return 'text-blue-600';
      case 'DOC': return 'text-amber-600';
      case 'DEADLINE': return 'text-red-600';
      default: return 'text-slate-500';
    }
  };

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'fatal') return 'text-red-600';
    if (s === 'critical') return 'text-orange-600';
    if (s === 'important' || s === 'high') return 'text-amber-600';
    if (s === 'active' || s === 'pending') return 'text-green-600';
    if (s === 'completed') return 'text-slate-500';
    return 'text-slate-400';
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 pt-16"
          onClick={handleClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="bg-white rounded-xl shadow-modal w-full max-w-4xl mx-4 flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={handleKeyDown}
          >
        {/* Search Header */}
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="text-blue-600 font-medium text-lg">⌘</span>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search cases, documents, deadlines..."
              className="flex-1 bg-transparent text-slate-900 text-base placeholder-slate-400 focus:outline-none"
              spellCheck={false}
            />
            {loading && (
              <span className="text-blue-600 text-sm font-medium">Searching...</span>
            )}
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-2">
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
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  activeFilter === filter
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {filter} <span className="text-slate-400">({count})</span>
              </button>
            );
          })}
          <span className="ml-auto text-slate-500 text-xs">Press Tab to cycle</span>
        </div>

        {/* Results List */}
        <div
          ref={resultsContainerRef}
          className="flex-1 overflow-y-auto max-h-[500px] bg-white"
        >
          {query.length < 2 && (
            <div className="p-12 text-center">
              <p className="text-slate-900 text-base font-medium">Start typing to search</p>
              <p className="text-slate-500 text-sm mt-2">Search across cases, documents, and deadlines</p>
            </div>
          )}

          {query.length >= 2 && !loading && flatResults.length === 0 && (
            <div className="p-12 text-center">
              <p className="text-slate-900 text-base font-medium">No results found</p>
              <p className="text-slate-500 text-sm mt-2">Try different keywords</p>
            </div>
          )}

          {flatResults.length > 0 && (
            <div className="divide-y divide-slate-200">
              {flatResults.map((result, idx) => (
                <div
                  key={`${result.type}-${result.id}`}
                  data-result
                  onClick={() => navigateToResult(result)}
                  className={`cursor-pointer px-6 py-4 transition-colors ${
                    idx === selectedIndex
                      ? 'bg-blue-50 border-l-4 border-blue-500 pl-[22px]'
                      : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className={`text-xs font-semibold uppercase ${getTypeColor(result.type)}`}>
                          {result.type}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">
                          {result.identifier}
                        </span>
                      </div>
                      <p className="text-sm text-slate-900 font-medium truncate">
                        {result.title}
                      </p>
                      {result.meta && (
                        <p className="text-xs text-slate-500 mt-1 truncate">
                          {result.meta}
                        </p>
                      )}
                    </div>
                    <div className={`text-xs font-medium px-2 py-1 rounded ${getStatusColor(result.status)}`}>
                      {result.status}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer - Keyboard shortcuts */}
        <div className="bg-slate-50 border-t border-slate-200 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4 text-slate-600 text-xs">
            <span><kbd className="px-2 py-1 bg-white border border-slate-300 rounded text-xs font-mono text-slate-700">↑↓</kbd> Navigate</span>
            <span><kbd className="px-2 py-1 bg-white border border-slate-300 rounded text-xs font-mono text-slate-700">↵</kbd> Select</span>
            <span><kbd className="px-2 py-1 bg-white border border-slate-300 rounded text-xs font-mono text-slate-700">Tab</kbd> Filter</span>
            <span><kbd className="px-2 py-1 bg-white border border-slate-300 rounded text-xs font-mono text-slate-700">Esc</kbd> Close</span>
          </div>
          {flatResults.length > 0 && (
            <span className="text-slate-600 text-sm font-medium">
              {selectedIndex + 1} of {flatResults.length}
            </span>
          )}
        </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
