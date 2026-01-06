'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Scale, ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';
import apiClient from '@/lib/api-client';
import CalendarView from '@/components/CalendarView';

interface Deadline {
  id: string;
  title: string;
  deadline_date: string;
  priority: string;
  case_id: string;
  status: string;
  description?: string;
  applicable_rule?: string;
}

interface CaseInfo {
  id: string;
  case_number: string;
  title: string;
}

export default function CalendarPage() {
  const router = useRouter();
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [cases, setCases] = useState<CaseInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDeadline, setSelectedDeadline] = useState<Deadline | null>(null);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      // Fetch all cases
      const casesResponse = await apiClient.get('/api/v1/cases/');
      setCases(casesResponse.data);

      // Fetch all deadlines across all cases
      const allDeadlines: Deadline[] = [];
      for (const caseData of casesResponse.data) {
        const deadlinesResponse = await apiClient.get(`/api/v1/deadlines/case/${caseData.id}`);
        allDeadlines.push(...deadlinesResponse.data);
      }

      setDeadlines(allDeadlines);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeadlineClick = (deadline: Deadline) => {
    setSelectedDeadline(deadline);
  };

  const getCaseInfo = (caseId: string) => {
    return cases.find(c => c.id === caseId);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Loading calendar...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Scale className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-slate-800">LitDocket</h1>
                <p className="text-sm text-slate-600">Master Deadline Calendar</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Dashboard</span>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Summary Banner */}
        <div className="mb-6 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl shadow-lg p-6 text-white">
          <div className="grid grid-cols-3 gap-6">
            <div>
              <p className="text-blue-100 text-sm mb-1">Total Cases</p>
              <p className="text-3xl font-bold">{cases.length}</p>
            </div>
            <div>
              <p className="text-blue-100 text-sm mb-1">All Deadlines</p>
              <p className="text-3xl font-bold">{deadlines.length}</p>
            </div>
            <div>
              <p className="text-blue-100 text-sm mb-1">Pending</p>
              <p className="text-3xl font-bold">
                {deadlines.filter(d => d.status === 'pending').length}
              </p>
            </div>
          </div>
        </div>

        {/* Calendar */}
        <CalendarView deadlines={deadlines} onDeadlineClick={handleDeadlineClick} />

        {/* Deadline Detail Modal */}
        {selectedDeadline && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setSelectedDeadline(null)}>
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 p-6" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-xl font-bold text-slate-800 mb-4">{selectedDeadline.title}</h3>

              {selectedDeadline.description && (
                <div className="mb-4">
                  <p className="text-sm text-slate-600 whitespace-pre-line">{selectedDeadline.description}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-sm font-medium text-slate-500">Deadline Date</p>
                  <p className="text-base text-slate-900">
                    {new Date(selectedDeadline.deadline_date).toLocaleDateString('en-US', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">Priority</p>
                  <p className="text-base text-slate-900 capitalize">{selectedDeadline.priority}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">Status</p>
                  <p className="text-base text-slate-900 capitalize">{selectedDeadline.status}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">Case</p>
                  <p className="text-base text-blue-600 hover:underline cursor-pointer" onClick={() => router.push(`/cases/${selectedDeadline.case_id}`)}>
                    {getCaseInfo(selectedDeadline.case_id)?.case_number || 'Unknown'}
                  </p>
                </div>
              </div>

              {selectedDeadline.applicable_rule && (
                <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm font-medium text-blue-900 mb-1">Applicable Rule</p>
                  <p className="text-sm text-blue-700">{selectedDeadline.applicable_rule}</p>
                </div>
              )}

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setSelectedDeadline(null)}
                  className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => router.push(`/cases/${selectedDeadline.case_id}`)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Go to Case
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
