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
      case 'CASE': return 'text-terminal-green';
      case 'DOC': return 'text-terminal-amber';
      case 'DEADLINE': return 'text-fatal';
      default: return 'text-ink-muted';
    }
  };

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'fatal' || s === 'critical') return 'text-fatal';
    if (s === 'important' || s === 'high') return 'text-critical';
    if (s === 'active' || s === 'pending') return 'text-terminal-green';
    if (s === 'completed') return 'text-ink-secondary';
    return 'text-ink-muted';
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="fixed inset-0 bg-ink/80 flex items-start justify-center z-50 pt-16"
          onClick={handleClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="bg-terminal-bg border-2 border-ink w-full max-w-4xl mx-4 flex flex-col"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={handleKeyDown}
          >
        {/* Terminal Header - Paper & Steel */}
        <div className="bg-steel border-b-2 border-ink px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-terminal-green font-mono text-sm font-bold">&gt;_</span>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="search cases, documents, deadlines..."
              className="flex-1 bg-transparent text-terminal-text font-mono text-sm placeholder-ink-muted focus:outline-none"
              spellCheck={false}
            />
            {loading && (
              <span className="text-terminal-amber font-mono text-xs font-bold">SEARCHING_</span>
            )}
          </div>
        </div>

        {/* Filter Tabs - Hard borders, no fade */}
        <div className="bg-steel border-b border-ink px-4 py-2 flex items-center gap-1">
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
                className={`px-3 py-1 font-mono text-xs border transition-transform hover:translate-x-0.5 ${
                  activeFilter === filter
                    ? 'bg-ink text-terminal-text border-terminal-green'
                    : 'text-terminal-text border-steel hover:border-terminal-green'
                }`}
              >
                {filter} <span className="text-ink-muted">({count})</span>
              </button>
            );
          })}
          <span className="ml-auto text-terminal-text font-mono text-[10px] uppercase tracking-wide">TAB CYCLE</span>
        </div>

        {/* Results Table - Dense, tactical */}
        <div
          ref={resultsContainerRef}
          className="flex-1 overflow-y-auto max-h-[400px] bg-terminal-bg"
        >
          {query.length < 2 && (
            <div className="p-8 text-center">
              <p className="text-terminal-text font-mono text-sm font-bold">TYPE TO SEARCH</p>
              <p className="text-ink-muted font-mono text-xs mt-2">min 2 characters</p>
            </div>
          )}

          {query.length >= 2 && !loading && flatResults.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-terminal-amber font-mono text-sm font-bold">NO RESULTS</p>
              <p className="text-ink-muted font-mono text-xs mt-2">"{query}"</p>
            </div>
          )}

          {flatResults.length > 0 && (
            <table className="w-full font-mono text-sm border-collapse">
              <thead className="bg-steel sticky top-0 border-b-2 border-ink">
                <tr className="text-terminal-text text-[10px] uppercase tracking-wider font-bold">
                  <th className="text-left px-4 py-2 w-20 border-r border-ink">Type</th>
                  <th className="text-left px-4 py-2 w-32 border-r border-ink">ID</th>
                  <th className="text-left px-4 py-2 border-r border-ink">Title</th>
                  <th className="text-left px-4 py-2 w-24 border-r border-ink">Status</th>
                  <th className="text-left px-4 py-2 w-32">Case</th>
                </tr>
              </thead>
              <tbody>
                {flatResults.map((result, idx) => (
                  <tr
                    key={`${result.type}-${result.id}`}
                    data-result
                    onClick={() => navigateToResult(result)}
                    className={`cursor-pointer border-b border-ink/30 transition-transform ${
                      idx === selectedIndex
                        ? 'bg-steel text-terminal-text border-terminal-green border-l-4'
                        : 'text-terminal-text/80 hover:translate-x-1 hover:bg-steel/50'
                    }`}
                  >
                    <td className={`px-4 py-2 border-r border-ink/30 font-bold ${getTypeColor(result.type)}`}>
                      {result.type}
                    </td>
                    <td className="px-4 py-2 border-r border-ink/30 text-ink-muted truncate max-w-[120px]">
                      {result.identifier}
                    </td>
                    <td className="px-4 py-2 border-r border-ink/30 truncate max-w-[300px]">
                      {result.title}
                    </td>
                    <td className={`px-4 py-2 border-r border-ink/30 font-bold ${getStatusColor(result.status)}`}>
                      {result.status.toUpperCase()}
                    </td>
                    <td className="px-4 py-2 text-ink-muted truncate max-w-[120px]">
                      {result.meta || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer - Hard keyboard navigation legend */}
        <div className="bg-steel border-t-2 border-ink px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-4 text-terminal-text font-mono text-[10px] uppercase tracking-wide">
            <span><kbd className="px-1.5 py-0.5 border border-terminal-green text-terminal-green">↑↓</kbd> NAV</span>
            <span><kbd className="px-1.5 py-0.5 border border-terminal-green text-terminal-green">↵</kbd> SEL</span>
            <span><kbd className="px-1.5 py-0.5 border border-terminal-green text-terminal-green">TAB</kbd> FLTR</span>
            <span><kbd className="px-1.5 py-0.5 border border-terminal-green text-terminal-green">ESC</kbd> EXIT</span>
          </div>
          {flatResults.length > 0 && (
            <span className="text-terminal-text font-mono text-xs font-bold">
              {selectedIndex + 1}/{flatResults.length}
            </span>
          )}
        </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
