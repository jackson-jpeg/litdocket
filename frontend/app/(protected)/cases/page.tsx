'use client';

/**
 * All Cases - CompuLaw-Grade Portfolio View
 *
 * Gold Standard Design System:
 * - Health Bar visual indicators (border-l-4)
 * - Dense data layout with split columns
 * - Hover quick actions
 * - Quick-view drawer
 * - Bulk selection with floating action bar
 */

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search, Folder, Calendar, Clock, AlertTriangle,
  ChevronRight, FileText, Scale, LayoutGrid, List,
  Upload, ExternalLink, CheckSquare, Square, X,
  FileDown, Users, Archive, User, Building
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import GlobalSearch from '@/shared/components/ui/GlobalSearch';
import CaseQuickView from '@/features/cases/components/CaseQuickView';
import ContextMenu from '@/features/cases/components/ContextMenu';

interface Case {
  id: string;
  case_number: string;
  title: string;
  court: string;
  judge: string;
  jurisdiction: string;
  case_type: string;
  status: string;
  created_at: string;
  parties: { name: string; role: string }[];
  _stats?: {
    document_count: number;
    pending_deadlines: number;
    next_deadline?: string;
    days_until_next_deadline?: number;
    next_deadline_priority?: string;
  };
}

export default function CasesListPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<Case[]>([]);
  const [filteredCases, setFilteredCases] = useState<Case[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterJurisdiction, setFilterJurisdiction] = useState('all');
  const [filterCaseType, setFilterCaseType] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [sortBy, setSortBy] = useState<'date' | 'case_number' | 'deadline'>('deadline');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [globalSearchOpen, setGlobalSearchOpen] = useState(false);

  // Quick View drawer state
  const [quickViewOpen, setQuickViewOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);

  // Bulk selection state
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Context menu state
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; caseItem: Case } | null>(null);

  // Keyboard navigation state
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const caseRowRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  useEffect(() => {
    fetchCases();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [cases, searchQuery, filterJurisdiction, filterCaseType, filterStatus, sortBy]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Global search (Cmd/Ctrl+K)
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setGlobalSearchOpen(true);
        return;
      }

      // Select all (Ctrl+A) - only in selection mode
      if ((e.metaKey || e.ctrlKey) && e.key === 'a' && selectionMode) {
        e.preventDefault();
        toggleSelectAll();
        return;
      }

      // Escape to close drawer/context menu
      if (e.key === 'Escape') {
        setQuickViewOpen(false);
        setContextMenu(null);
        if (selectionMode && selectedIds.size === 0) {
          setSelectionMode(false);
        }
        return;
      }

      // Arrow key navigation (only in list view)
      if (viewMode === 'list' && filteredCases.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setFocusedIndex((prev) => {
            const newIndex = prev < filteredCases.length - 1 ? prev + 1 : prev;
            // Scroll into view
            const caseId = filteredCases[newIndex]?.id;
            if (caseId) {
              const element = caseRowRefs.current.get(caseId);
              element?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            return newIndex;
          });
          return;
        }

        if (e.key === 'ArrowUp') {
          e.preventDefault();
          setFocusedIndex((prev) => {
            const newIndex = prev > 0 ? prev - 1 : prev;
            // Scroll into view
            const caseId = filteredCases[newIndex]?.id;
            if (caseId) {
              const element = caseRowRefs.current.get(caseId);
              element?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            return newIndex;
          });
          return;
        }

        // Enter to open case
        if (e.key === 'Enter' && focusedIndex >= 0 && focusedIndex < filteredCases.length) {
          e.preventDefault();
          const focusedCase = filteredCases[focusedIndex];
          if (focusedCase) {
            setSelectedCase(focusedCase);
            setQuickViewOpen(true);
          }
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectionMode, selectedIds, viewMode, filteredCases, focusedIndex]);

  const fetchCases = async () => {
    try {
      const response = await apiClient.get('/api/v1/cases');

      // First, set cases immediately so page loads fast
      const baseCases = response.data.map((caseItem: Case) => ({
        ...caseItem,
        _stats: {
          document_count: 0,
          pending_deadlines: 0,
          next_deadline: undefined,
          days_until_next_deadline: undefined,
          next_deadline_priority: undefined
        }
      }));
      setCases(baseCases);
      setLoading(false);

      // Then fetch stats for each case in parallel
      const casesWithStats = await Promise.all(
        response.data.map(async (caseItem: Case) => {
          try {
            const [docsRes, deadlinesRes] = await Promise.all([
              apiClient.get(`/api/v1/cases/${caseItem.id}/documents`).catch(() => ({ data: [] })),
              apiClient.get(`/api/v1/deadlines/case/${caseItem.id}`).catch(() => ({ data: [] }))
            ]);

            const pendingDeadlines = (deadlinesRes.data || []).filter(
              (d: { status: string; deadline_date: string }) => d.status === 'pending' && d.deadline_date
            );
            pendingDeadlines.sort((a: { deadline_date: string }, b: { deadline_date: string }) =>
              new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime()
            );

            const nextDeadline = pendingDeadlines[0];
            const daysUntil = nextDeadline
              ? Math.ceil(
                  (new Date(nextDeadline.deadline_date).getTime() - Date.now()) /
                    (1000 * 60 * 60 * 24)
                )
              : null;

            return {
              ...caseItem,
              _stats: {
                document_count: (docsRes.data || []).length,
                pending_deadlines: pendingDeadlines.length,
                next_deadline: nextDeadline?.deadline_date,
                days_until_next_deadline: daysUntil,
                next_deadline_priority: nextDeadline?.priority
              }
            };
          } catch (err) {
            console.warn(`Failed to fetch stats for case ${caseItem.id}:`, err);
            return {
              ...caseItem,
              _stats: {
                document_count: 0,
                pending_deadlines: 0,
                next_deadline: undefined,
                days_until_next_deadline: undefined,
                next_deadline_priority: undefined
              }
            };
          }
        })
      );

      setCases(casesWithStats);
    } catch (err) {
      console.error('Failed to load cases:', err);
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...cases];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.case_number?.toLowerCase().includes(query) ||
          c.title?.toLowerCase().includes(query) ||
          c.court?.toLowerCase().includes(query) ||
          c.judge?.toLowerCase().includes(query) ||
          c.parties?.some((p) => p.name?.toLowerCase().includes(query))
      );
    }

    // Jurisdiction filter
    if (filterJurisdiction !== 'all') {
      filtered = filtered.filter((c) => c.jurisdiction === filterJurisdiction);
    }

    // Case type filter
    if (filterCaseType !== 'all') {
      filtered = filtered.filter((c) => c.case_type === filterCaseType);
    }

    // Status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter((c) => c.status === filterStatus);
    }

    // Sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'case_number':
          return (a.case_number || '').localeCompare(b.case_number || '');
        case 'deadline':
          const aDeadline = a._stats?.next_deadline || '9999-12-31';
          const bDeadline = b._stats?.next_deadline || '9999-12-31';
          return aDeadline.localeCompare(bDeadline);
        case 'date':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

    setFilteredCases(filtered);
  };

  // Priority dot color logic
  const getPriorityDotColor = (caseItem: Case) => {
    const days = caseItem._stats?.days_until_next_deadline;
    const priority = caseItem._stats?.next_deadline_priority;

    if (days === null || days === undefined) return 'bg-green-600';
    if (days < 0) return 'bg-red-600'; // Overdue
    if (priority === 'fatal' || priority === 'critical') return 'bg-red-600';
    if (days <= 3) return 'bg-orange-600'; // < 3 days
    if (days <= 7) return 'bg-amber-500'; // < 7 days
    return 'bg-green-600'; // Safe
  };

  const getUrgencyBadge = (daysUntil: number | null | undefined) => {
    if (daysUntil === null || daysUntil === undefined) return null;
    if (daysUntil < 0)
      return (
        <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded">
          OVERDUE
        </span>
      );
    if (daysUntil <= 3)
      return (
        <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-bold rounded">
          URGENT
        </span>
      );
    if (daysUntil <= 7)
      return (
        <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded">
          THIS WEEK
        </span>
      );
    return null;
  };

  // Bulk selection handlers
  const toggleSelection = (id: string) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedIds(newSelection);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredCases.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredCases.map(c => c.id)));
    }
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
    setSelectionMode(false);
  };

  // Row click handler
  const handleRowClick = (caseItem: Case, e: React.MouseEvent) => {
    if (selectionMode) {
      toggleSelection(caseItem.id);
    } else {
      // Open Quick View drawer
      setSelectedCase(caseItem);
      setQuickViewOpen(true);
    }
  };

  // Navigate to case
  const navigateToCase = (caseId: string) => {
    router.push(`/cases/${caseId}`);
  };

  // Context menu handlers
  const handleContextMenu = (e: React.MouseEvent, caseItem: Case) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      caseItem,
    });
  };

  const handleArchiveCase = async () => {
    if (!contextMenu) return;
    // TODO: Implement archive API call
    alert(`Archive case: ${contextMenu.caseItem.case_number}\n\nThis feature will be implemented with backend support.`);
  };

  const handleExportDetails = async () => {
    if (!contextMenu) return;
    // TODO: Implement export API call
    alert(`Export details: ${contextMenu.caseItem.case_number}\n\nThis feature will be implemented with backend support.`);
  };

  const handleGenerateReport = async () => {
    if (!contextMenu) return;
    // TODO: Implement generate report API call
    alert(`Generate report: ${contextMenu.caseItem.case_number}\n\nThis feature will be implemented with backend support.`);
  };

  const handleAssignAttorney = async () => {
    if (!contextMenu) return;
    // TODO: Implement assign attorney modal
    alert(`Assign attorney: ${contextMenu.caseItem.case_number}\n\nThis feature will be implemented with backend support.`);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Folder className="w-12 h-12 text-blue-600 animate-pulse mx-auto mb-4" />
          <p className="text-slate-600">Loading cases...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      {/* Global Search Modal */}
      <GlobalSearch isOpen={globalSearchOpen} onClose={() => setGlobalSearchOpen(false)} />

      {/* Case Quick View Drawer */}
      <CaseQuickView
        isOpen={quickViewOpen}
        caseData={selectedCase}
        onClose={() => setQuickViewOpen(false)}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">All Cases</h1>
          <p className="text-sm text-slate-500">
            Showing {cases.length} case{cases.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push('/dashboard')}
            className="btn-ghost"
          >
            Dashboard
          </button>
          <button
            onClick={() => router.push('/')}
            className="btn-primary"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload Document
          </button>
        </div>
      </div>
        {/* Filters and Search */}
        <div className="card mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
            {/* Search */}
            <div className="lg:col-span-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search cases, parties, courts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Jurisdiction Filter */}
            <select
              value={filterJurisdiction}
              onChange={(e) => setFilterJurisdiction(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="all">All Jurisdictions</option>
              <option value="state">State</option>
              <option value="federal">Federal</option>
            </select>

            {/* Case Type Filter */}
            <select
              value={filterCaseType}
              onChange={(e) => setFilterCaseType(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="all">All Types</option>
              <option value="civil">Civil</option>
              <option value="criminal">Criminal</option>
              <option value="appellate">Appellate</option>
            </select>

            {/* Status Filter */}
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="stayed">Stayed</option>
              <option value="closed">Closed</option>
            </select>

            {/* Sort By */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'date' | 'case_number' | 'deadline')}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="deadline">Sort: Urgency</option>
              <option value="date">Sort: Newest First</option>
              <option value="case_number">Sort: Case Number</option>
            </select>
          </div>

          {/* Results count and view controls */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-200">
            <div className="flex items-center gap-4">
              <p className="text-sm text-slate-600">
                Showing {filteredCases.length} of {cases.length} cases
              </p>
              <button
                onClick={() => setSelectionMode(!selectionMode)}
                className={`text-sm px-3 py-1 rounded-lg transition-colors ${
                  selectionMode
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {selectionMode ? 'Cancel Selection' : 'Select Cases'}
              </button>
              {viewMode === 'list' && (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <kbd className="px-1.5 py-0.5 bg-slate-200 rounded border border-slate-300">↑↓</kbd>
                  <span>Navigate</span>
                  <kbd className="px-1.5 py-0.5 bg-slate-200 rounded border border-slate-300">Enter</kbd>
                  <span>Open</span>
                  <kbd className="px-1.5 py-0.5 bg-slate-200 rounded border border-slate-300">Right-click</kbd>
                  <span>Menu</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded ${
                  viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <List className="w-5 h-5" />
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded ${
                  viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <LayoutGrid className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Cases Display */}
        {filteredCases.length === 0 ? (
          <div className="card text-center py-16">
            <Folder className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No cases found</h3>
            <p className="text-slate-600 mb-6">
              {searchQuery || filterJurisdiction !== 'all' || filterCaseType !== 'all'
                ? 'Try adjusting your filters'
                : 'Upload a document to create your first case'}
            </p>
            <button
              onClick={() => router.push('/')}
              className="btn-primary"
            >
              Upload Document
            </button>
          </div>
        ) : viewMode === 'list' ? (
          <div className="card overflow-hidden">
            {/* Table Header */}
            <div className="bg-slate-50 border-b border-slate-200 px-6 py-3">
              <div className="flex items-center gap-4">
                {selectionMode && (
                  <button
                    onClick={toggleSelectAll}
                    className="text-slate-600 hover:text-slate-900"
                  >
                    {selectedIds.size === filteredCases.length ? (
                      <CheckSquare className="w-5 h-5 text-blue-600" />
                    ) : (
                      <Square className="w-5 h-5" />
                    )}
                  </button>
                )}
                <div className="flex-1 grid grid-cols-12 gap-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <div className="col-span-4">Case</div>
                  <div className="col-span-3">Court / Judge</div>
                  <div className="col-span-2">Stats</div>
                  <div className="col-span-2">Next Deadline</div>
                  <div className="col-span-1"></div>
                </div>
              </div>
            </div>

            {/* Table Body */}
            <div className="divide-y divide-slate-200">
              {filteredCases.map((caseItem, index) => (
                <div
                  key={caseItem.id}
                  ref={(el) => {
                    if (el) {
                      caseRowRefs.current.set(caseItem.id, el);
                    } else {
                      caseRowRefs.current.delete(caseItem.id);
                    }
                  }}
                  onClick={(e) => handleRowClick(caseItem, e)}
                  onContextMenu={(e) => handleContextMenu(e, caseItem)}
                  className={`
                    group px-6 py-5 cursor-pointer transition-all
                    ${focusedIndex === index ? 'bg-blue-50 ring-2 ring-blue-500 ring-inset' : 'hover:bg-slate-50'}
                  `}
                >
                  <div className="flex items-center gap-4">
                    {/* Priority Dot */}
                    <div className={`w-2 h-2 rounded-full ${getPriorityDotColor(caseItem)}`}></div>

                    {/* Checkbox */}
                    {selectionMode && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleSelection(caseItem.id);
                        }}
                        className="text-slate-600 hover:text-slate-900"
                      >
                        {selectedIds.has(caseItem.id) ? (
                          <CheckSquare className="w-5 h-5 text-blue-600" />
                        ) : (
                          <Square className="w-5 h-5" />
                        )}
                      </button>
                    )}

                    <div className="flex-1 grid grid-cols-12 gap-4 items-center">
                      {/* Case Column - Dense Layout */}
                      <div className="col-span-4">
                        <p className="font-mono text-sm font-semibold text-blue-600 mb-0.5 font-medium">
                          {caseItem.case_number}
                        </p>
                        <p className="text-base text-slate-900 truncate leading-tight font-medium">
                          {caseItem.title}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          {caseItem.jurisdiction && (
                            <span className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
                              {caseItem.jurisdiction}
                            </span>
                          )}
                          {caseItem.case_type && (
                            <span className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">
                              {caseItem.case_type}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Court/Judge Column - Dense Layout */}
                      <div className="col-span-3">
                        <div className="flex items-center gap-1.5 text-sm text-slate-700 mb-0.5">
                          <Building className="w-3.5 h-3.5 text-slate-400" />
                          <span className="truncate">{caseItem.court || 'N/A'}</span>
                        </div>
                        {caseItem.judge && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSearchQuery(caseItem.judge);
                            }}
                            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-blue-600 transition-colors"
                          >
                            <User className="w-3 h-3" />
                            <span className="px-1.5 py-0.5 bg-slate-100 hover:bg-blue-100 rounded transition-colors">
                              Judge {caseItem.judge}
                            </span>
                          </button>
                        )}
                      </div>

                      {/* Stats Column */}
                      <div className="col-span-2">
                        <div className="flex items-center gap-4 text-sm">
                          <div className="flex items-center gap-1.5 text-slate-600">
                            <FileText className="w-4 h-4" />
                            <span className="font-medium">{caseItem._stats?.document_count || 0}</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-slate-600">
                            <Clock className="w-4 h-4" />
                            <span className="font-medium">{caseItem._stats?.pending_deadlines || 0}</span>
                          </div>
                        </div>
                      </div>

                      {/* Next Deadline Column */}
                      <div className="col-span-2">
                        {caseItem._stats?.next_deadline ? (
                          <div>
                            <p className="text-sm font-mono font-medium text-slate-700">
                              {new Date(caseItem._stats.next_deadline).toLocaleDateString()}
                            </p>
                            <div className="flex items-center gap-2 mt-0.5">
                              {getUrgencyBadge(caseItem._stats.days_until_next_deadline)}
                              {!getUrgencyBadge(caseItem._stats.days_until_next_deadline) && (
                                <span className="text-xs text-slate-500">
                                  {caseItem._stats.days_until_next_deadline}d
                                </span>
                              )}
                            </div>
                          </div>
                        ) : (
                          <span className="text-sm text-slate-400">No deadlines</span>
                        )}
                      </div>

                      {/* Actions Column */}
                      <div className="col-span-1 flex items-center justify-end gap-2">
                        {/* Hover Quick Actions */}
                        <div className="hidden group-hover:flex items-center gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigateToCase(caseItem.id);
                            }}
                            className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Upload Document"
                          >
                            <Upload className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push('/calendar');
                            }}
                            className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="View Calendar"
                          >
                            <Calendar className="w-4 h-4" />
                          </button>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigateToCase(caseItem.id);
                          }}
                          className="p-1.5 text-slate-400 hover:text-slate-600"
                        >
                          <ChevronRight className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Grid View */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCases.map((caseItem) => (
              <div
                key={caseItem.id}
                onClick={(e) => handleRowClick(caseItem, e)}
                className="card-hover cursor-pointer"
              >
                {selectionMode && (
                  <div className="flex justify-end mb-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelection(caseItem.id);
                      }}
                    >
                      {selectedIds.has(caseItem.id) ? (
                        <CheckSquare className="w-5 h-5 text-blue-600" />
                      ) : (
                        <Square className="w-5 h-5 text-slate-400" />
                      )}
                    </button>
                  </div>
                )}

                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1 flex items-start gap-3">
                    <div className={`w-2 h-2 rounded-full ${getPriorityDotColor(caseItem)} mt-2`}></div>
                    <div className="flex-1">
                      <p className="font-mono text-sm font-semibold text-blue-600 mb-1">
                        {caseItem.case_number}
                      </p>
                      <h3 className="font-semibold text-slate-900 line-clamp-2">{caseItem.title}</h3>
                    </div>
                  </div>
                  {getUrgencyBadge(caseItem._stats?.days_until_next_deadline)}
                </div>

                <div className="space-y-2 mb-4 text-sm">
                  {caseItem.court && (
                    <div className="flex items-center gap-2 text-slate-600">
                      <Building className="w-4 h-4 text-slate-400" />
                      {caseItem.court}
                    </div>
                  )}
                  {caseItem.judge && (
                    <div className="flex items-center gap-2 text-slate-600">
                      <User className="w-4 h-4 text-slate-400" />
                      Judge {caseItem.judge}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-4 text-sm text-slate-600 mb-4">
                  <div className="flex items-center gap-1">
                    <FileText className="w-4 h-4" />
                    <span>{caseItem._stats?.document_count || 0} docs</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    <span>{caseItem._stats?.pending_deadlines || 0} deadlines</span>
                  </div>
                </div>

                {caseItem._stats?.next_deadline && (
                  <div className="pt-4 border-t border-slate-200">
                    <p className="text-xs text-slate-500 mb-1">Next Deadline</p>
                    <p className="text-sm font-mono font-medium text-slate-700">
                      {new Date(caseItem._stats.next_deadline).toLocaleDateString()}
                      <span className="text-slate-500 font-normal ml-2">
                        ({caseItem._stats.days_until_next_deadline}d)
                      </span>
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

      {/* Bulk Action Bar */}
      {selectionMode && selectedIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-20">
          <div className="bg-slate-900 text-white rounded-xl shadow-2xl px-6 py-4 flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold">{selectedIds.size}</span>
              <span className="text-slate-400">selected</span>
            </div>
            <div className="h-8 w-px bg-slate-700" />
            <div className="flex items-center gap-2">
              <button
                onClick={() => alert('Generate Docket Report - Coming soon')}
                className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <FileDown className="w-4 h-4" />
                Generate Report
              </button>
              <button
                onClick={() => alert('Assign Attorney - Coming soon')}
                className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <Users className="w-4 h-4" />
                Assign Attorney
              </button>
              <button
                onClick={() => alert('Archive Cases - Coming soon')}
                className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <Archive className="w-4 h-4" />
                Archive
              </button>
            </div>
            <div className="h-8 w-px bg-slate-700" />
            <button
              onClick={clearSelection}
              className="p-2 text-slate-400 hover:text-white rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Context Menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          onArchive={handleArchiveCase}
          onExportDetails={handleExportDetails}
          onGenerateReport={handleGenerateReport}
          onAssignAttorney={handleAssignAttorney}
        />
      )}
    </div>
  );
}
