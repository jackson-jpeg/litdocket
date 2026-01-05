'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search, Filter, Folder, Calendar, Clock, AlertTriangle,
  ChevronRight, FileText, Scale, LayoutGrid, List, SortAsc
} from 'lucide-react';
import apiClient from '@/lib/api-client';

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
  parties: any[];
  _stats?: {
    document_count: number;
    pending_deadlines: number;
    next_deadline?: string;
    days_until_next_deadline?: number;
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
  const [sortBy, setSortBy] = useState<'date' | 'case_number' | 'deadline'>('date');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');

  useEffect(() => {
    fetchCases();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [cases, searchQuery, filterJurisdiction, filterCaseType, filterStatus, sortBy]);

  const fetchCases = async () => {
    try {
      const response = await apiClient.get('/api/v1/cases');
      const casesWithStats = await Promise.all(
        response.data.map(async (caseItem: Case) => {
          // Fetch case stats
          const [docsRes, deadlinesRes] = await Promise.all([
            apiClient.get(`/api/v1/cases/${caseItem.id}/documents`),
            apiClient.get(`/api/v1/deadlines/case/${caseItem.id}`)
          ]);

          const pendingDeadlines = deadlinesRes.data.filter(
            (d: any) => d.status === 'pending' && d.deadline_date
          );
          pendingDeadlines.sort((a: any, b: any) =>
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
              document_count: docsRes.data.length,
              pending_deadlines: pendingDeadlines.length,
              next_deadline: nextDeadline?.deadline_date,
              days_until_next_deadline: daysUntil
            }
          };
        })
      );

      setCases(casesWithStats);
    } catch (err) {
      console.error('Failed to load cases:', err);
    } finally {
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

  const getUrgencyColor = (daysUntil: number | null | undefined) => {
    if (daysUntil === null || daysUntil === undefined) return 'text-slate-400';
    if (daysUntil < 0) return 'text-red-600';
    if (daysUntil <= 3) return 'text-orange-600';
    if (daysUntil <= 7) return 'text-yellow-600';
    return 'text-blue-600';
  };

  const getUrgencyBadge = (daysUntil: number | null | undefined) => {
    if (daysUntil === null || daysUntil === undefined) return null;
    if (daysUntil < 0)
      return (
        <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded">
          OVERDUE
        </span>
      );
    if (daysUntil <= 3)
      return (
        <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded">
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

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Folder className="w-12 h-12 text-blue-500 animate-pulse mx-auto mb-4" />
          <p className="text-slate-600">Loading cases...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push('/')}>
              <Scale className="w-7 h-7 text-blue-600" />
              <h1 className="text-xl font-bold text-slate-800">All Cases</h1>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => router.push('/dashboard')}
                className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors font-medium"
              >
                Dashboard
              </button>
              <button
                onClick={() => router.push('/')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Upload Document
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Filters and Search */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
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
              className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Jurisdictions</option>
              <option value="state">State</option>
              <option value="federal">Federal</option>
            </select>

            {/* Case Type Filter */}
            <select
              value={filterCaseType}
              onChange={(e) => setFilterCaseType(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Types</option>
              <option value="civil">Civil</option>
              <option value="criminal">Criminal</option>
              <option value="appellate">Appellate</option>
            </select>

            {/* Sort By */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="date">Sort: Newest First</option>
              <option value="case_number">Sort: Case Number</option>
              <option value="deadline">Sort: Next Deadline</option>
            </select>
          </div>

          {/* Results count and view toggle */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-200">
            <p className="text-sm text-slate-600">
              Showing {filteredCases.length} of {cases.length} cases
            </p>
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
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-12 text-center">
            <Folder className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-800 mb-2">No cases found</h3>
            <p className="text-slate-600 mb-6">
              {searchQuery || filterJurisdiction !== 'all' || filterCaseType !== 'all'
                ? 'Try adjusting your filters'
                : 'Upload a document to create your first case'}
            </p>
            <button
              onClick={() => router.push('/')}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Upload Document
            </button>
          </div>
        ) : viewMode === 'list' ? (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">Case</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">Court</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">Type</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">Documents</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">Next Deadline</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredCases.map((caseItem) => (
                  <tr
                    key={caseItem.id}
                    onClick={() => router.push(`/cases/${caseItem.id}`)}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-semibold text-slate-800">{caseItem.case_number}</p>
                        <p className="text-sm text-slate-600 truncate max-w-md">{caseItem.title}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-slate-700">{caseItem.court || 'N/A'}</p>
                      {caseItem.judge && (
                        <p className="text-xs text-slate-500">Judge {caseItem.judge}</p>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        {caseItem.jurisdiction && (
                          <span className="text-xs px-2 py-1 bg-slate-100 text-slate-700 rounded w-fit">
                            {caseItem.jurisdiction}
                          </span>
                        )}
                        {caseItem.case_type && (
                          <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded w-fit">
                            {caseItem.case_type}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3 text-sm">
                        <div className="flex items-center gap-1 text-slate-600">
                          <FileText className="w-4 h-4" />
                          <span>{caseItem._stats?.document_count || 0}</span>
                        </div>
                        <div className="flex items-center gap-1 text-slate-600">
                          <Clock className="w-4 h-4" />
                          <span>{caseItem._stats?.pending_deadlines || 0}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {caseItem._stats?.next_deadline ? (
                        <div>
                          <p className={`text-sm font-medium ${getUrgencyColor(caseItem._stats.days_until_next_deadline)}`}>
                            {new Date(caseItem._stats.next_deadline).toLocaleDateString()}
                          </p>
                          <p className="text-xs text-slate-500">
                            {caseItem._stats.days_until_next_deadline !== null &&
                              caseItem._stats.days_until_next_deadline !== undefined &&
                              (caseItem._stats.days_until_next_deadline < 0
                                ? `${Math.abs(caseItem._stats.days_until_next_deadline)} days ago`
                                : `${caseItem._stats.days_until_next_deadline} days`)}
                          </p>
                        </div>
                      ) : (
                        <span className="text-sm text-slate-400">No deadlines</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {getUrgencyBadge(caseItem._stats?.days_until_next_deadline)}
                        <ChevronRight className="w-5 h-5 text-slate-400" />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCases.map((caseItem) => (
              <div
                key={caseItem.id}
                onClick={() => router.push(`/cases/${caseItem.id}`)}
                className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 hover:shadow-md transition-shadow cursor-pointer"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-800 mb-1">{caseItem.case_number}</h3>
                    <p className="text-sm text-slate-600 line-clamp-2">{caseItem.title}</p>
                  </div>
                  {getUrgencyBadge(caseItem._stats?.days_until_next_deadline)}
                </div>

                <div className="space-y-2 mb-4">
                  {caseItem.court && (
                    <p className="text-sm text-slate-600">
                      <span className="font-medium">Court:</span> {caseItem.court}
                    </p>
                  )}
                  {caseItem.judge && (
                    <p className="text-sm text-slate-600">
                      <span className="font-medium">Judge:</span> {caseItem.judge}
                    </p>
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
                    <p className={`text-sm font-medium ${getUrgencyColor(caseItem._stats.days_until_next_deadline)}`}>
                      {new Date(caseItem._stats.next_deadline).toLocaleDateString()}
                      {caseItem._stats.days_until_next_deadline !== null &&
                        caseItem._stats.days_until_next_deadline !== undefined &&
                        ` (${
                          caseItem._stats.days_until_next_deadline < 0
                            ? `${Math.abs(caseItem._stats.days_until_next_deadline)} days ago`
                            : `${caseItem._stats.days_until_next_deadline} days`
                        })`}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
