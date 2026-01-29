'use client';

/**
 * useDeadlines - Unified Deadline Management Hook
 *
 * Extends the calendar hook with additional functionality for:
 * - Case-specific deadline queries
 * - Deadline deletion
 * - Cross-case aggregations
 *
 * This is the single source of truth for deadline operations.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import apiClient from '@/lib/api-client';
import { useEventBus, emitEvent } from '@/lib/eventBus';
import type { Deadline, CalendarDeadline } from '@/types';

// Re-export types for convenience
export type { Deadline, CalendarDeadline };

export interface CaseInfo {
  id: string;
  case_number: string;
  title: string;
}

export interface DeadlineFilters {
  status?: string;
  priority?: string;
  caseIds?: string[];
  caseId?: string; // Single case filter
  startDate?: string;
  endDate?: string;
  triggerId?: string;
}

export interface CreateDeadlineData {
  case_id: string;
  title: string;
  deadline_date: string;
  description?: string;
  priority?: string;
  deadline_type?: string;
  applicable_rule?: string;
  party_role?: string;
  action_required?: string;
}

export interface DeadlineStats {
  total: number;
  pending: number;
  overdue: number;
  critical: number; // fatal + critical priority
  completedThisMonth: number;
  byPriority: Record<string, number>;
  byCaseId: Record<string, number>;
}

interface UseDeadlinesReturn {
  deadlines: CalendarDeadline[];
  cases: CaseInfo[];
  loading: boolean;
  error: string | null;

  // Actions
  refetch: () => Promise<void>;
  createDeadline: (data: CreateDeadlineData) => Promise<CalendarDeadline | null>;
  updateDeadline: (id: string, data: Partial<Deadline>) => Promise<boolean>;
  updateDeadlineStatus: (id: string, status: string) => Promise<boolean>;
  rescheduleDeadline: (id: string, newDate: Date, reason?: string) => Promise<boolean>;
  deleteDeadline: (id: string) => Promise<boolean>;

  // Computed data
  overdueDeadlines: CalendarDeadline[];
  upcomingDeadlines: CalendarDeadline[];
  todayDeadlines: CalendarDeadline[];
  stats: DeadlineStats;
}

export function useDeadlines(filters?: DeadlineFilters): UseDeadlinesReturn {
  const [deadlines, setDeadlines] = useState<CalendarDeadline[]>([]);
  const [cases, setCases] = useState<CaseInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Build filter key for dependency tracking
  const filterKey = useMemo(() => {
    return JSON.stringify({
      status: filters?.status,
      priority: filters?.priority,
      caseIds: filters?.caseIds?.join(','),
      caseId: filters?.caseId,
      startDate: filters?.startDate,
      endDate: filters?.endDate,
      triggerId: filters?.triggerId,
    });
  }, [filters]);

  // Fetch deadlines
  const fetchDeadlines = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Determine which endpoint to use
      let url: string;
      const params = new URLSearchParams();

      if (filters?.caseId) {
        // Single case - use case-specific endpoint
        url = `/api/v1/deadlines/case/${filters.caseId}`;
      } else {
        // Cross-case - use user/all endpoint
        url = '/api/v1/deadlines/user/all';
        if (filters?.caseIds?.length) {
          params.set('case_ids', filters.caseIds.join(','));
        }
      }

      // Common filters
      if (filters?.status) params.set('status', filters.status);
      if (filters?.priority) params.set('priority', filters.priority);
      if (filters?.startDate) params.set('start_date', filters.startDate);
      if (filters?.endDate) params.set('end_date', filters.endDate);

      const queryString = params.toString();
      const fullUrl = `${url}${queryString ? `?${queryString}` : ''}`;

      const response = await apiClient.get(fullUrl);
      const data = Array.isArray(response.data) ? response.data : response.data.deadlines || [];

      setDeadlines(data);

      // Extract unique cases from deadlines
      const caseMap = new Map<string, CaseInfo>();
      data.forEach((d: CalendarDeadline) => {
        if (!caseMap.has(d.case_id) && d.case_number) {
          caseMap.set(d.case_id, {
            id: d.case_id,
            case_number: d.case_number,
            title: d.case_title || '',
          });
        }
      });
      setCases(Array.from(caseMap.values()));

    } catch (err: unknown) {
      console.error('Failed to fetch deadlines:', err);
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || 'Failed to load deadlines');
    } finally {
      setLoading(false);
    }
  }, [filterKey]);

  // Initial fetch
  useEffect(() => {
    fetchDeadlines();
  }, [fetchDeadlines]);

  // Subscribe to events
  useEventBus('calendar:refresh', useCallback(() => {
    fetchDeadlines();
  }, [fetchDeadlines]));

  useEventBus('deadline:created', useCallback(() => {
    fetchDeadlines();
  }, [fetchDeadlines]));

  useEventBus('deadline:updated', useCallback(() => {
    fetchDeadlines();
  }, [fetchDeadlines]));

  useEventBus('deadline:deleted', useCallback(() => {
    fetchDeadlines();
  }, [fetchDeadlines]));

  // Create deadline
  const createDeadline = useCallback(async (data: CreateDeadlineData): Promise<CalendarDeadline | null> => {
    try {
      const response = await apiClient.post('/api/v1/deadlines/', data);
      const newDeadline = response.data.deadline;

      // Add to local state
      setDeadlines(prev => [...prev, newDeadline].sort((a, b) => {
        if (!a.deadline_date) return 1;
        if (!b.deadline_date) return -1;
        return new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime();
      }));

      emitEvent('deadline:created', newDeadline);
      return newDeadline;
    } catch (err: unknown) {
      console.error('Failed to create deadline:', err);
      return null;
    }
  }, []);

  // Update deadline
  const updateDeadline = useCallback(async (id: string, data: Partial<Deadline>): Promise<boolean> => {
    try {
      await apiClient.patch(`/api/v1/deadlines/${id}`, data);

      // Optimistic update
      setDeadlines(prev => prev.map(d =>
        d.id === id ? { ...d, ...data } : d
      ));

      emitEvent('deadline:updated', { id, ...data });
      return true;
    } catch (err: unknown) {
      console.error('Failed to update deadline:', err);
      fetchDeadlines(); // Revert on error
      return false;
    }
  }, [fetchDeadlines]);

  // Update status
  const updateDeadlineStatus = useCallback(async (id: string, status: string): Promise<boolean> => {
    try {
      // Optimistic update
      setDeadlines(prev => prev.map(d =>
        d.id === id ? { ...d, status } : d
      ));

      await apiClient.patch(`/api/v1/deadlines/${id}/status?status=${status}`);

      emitEvent('deadline:updated', { id, status });
      return true;
    } catch (err: unknown) {
      console.error('Failed to update deadline status:', err);
      fetchDeadlines();
      return false;
    }
  }, [fetchDeadlines]);

  // Reschedule (drag-drop)
  const rescheduleDeadline = useCallback(async (
    id: string,
    newDate: Date,
    reason?: string
  ): Promise<boolean> => {
    try {
      const formattedDate = newDate.toISOString().split('T')[0];

      // Optimistic update
      setDeadlines(prev => prev.map(d =>
        d.id === id
          ? { ...d, deadline_date: formattedDate, is_manually_overridden: true }
          : d
      ));

      await apiClient.patch(`/api/v1/deadlines/${id}/reschedule`, {
        new_date: formattedDate,
        reason: reason || undefined,
      });

      emitEvent('deadline:updated', { id, deadline_date: formattedDate });
      return true;
    } catch (err: unknown) {
      console.error('Failed to reschedule deadline:', err);
      fetchDeadlines();
      return false;
    }
  }, [fetchDeadlines]);

  // Delete deadline
  const deleteDeadline = useCallback(async (id: string): Promise<boolean> => {
    try {
      // Optimistic update
      setDeadlines(prev => prev.filter(d => d.id !== id));

      await apiClient.delete(`/api/v1/deadlines/${id}`);

      emitEvent('deadline:deleted', { id });
      return true;
    } catch (err: unknown) {
      console.error('Failed to delete deadline:', err);
      fetchDeadlines();
      return false;
    }
  }, [fetchDeadlines]);

  // Computed: Overdue deadlines
  const overdueDeadlines = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return deadlines.filter(d => {
      if (!d.deadline_date || d.status !== 'pending') return false;
      const deadlineDate = new Date(d.deadline_date);
      deadlineDate.setHours(0, 0, 0, 0);
      return deadlineDate < today;
    }).sort((a, b) => {
      return new Date(a.deadline_date!).getTime() - new Date(b.deadline_date!).getTime();
    });
  }, [deadlines]);

  // Computed: Today's deadlines
  const todayDeadlines = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return deadlines.filter(d => {
      if (!d.deadline_date || d.status !== 'pending') return false;
      const deadlineDate = new Date(d.deadline_date);
      deadlineDate.setHours(0, 0, 0, 0);
      return deadlineDate.getTime() === today.getTime();
    });
  }, [deadlines]);

  // Computed: Upcoming (next 7 days, excluding today and overdue)
  const upcomingDeadlines = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const weekFromNow = new Date(today);
    weekFromNow.setDate(weekFromNow.getDate() + 7);

    return deadlines.filter(d => {
      if (!d.deadline_date || d.status !== 'pending') return false;
      const deadlineDate = new Date(d.deadline_date);
      deadlineDate.setHours(0, 0, 0, 0);
      return deadlineDate >= tomorrow && deadlineDate <= weekFromNow;
    }).sort((a, b) => {
      return new Date(a.deadline_date!).getTime() - new Date(b.deadline_date!).getTime();
    });
  }, [deadlines]);

  // Computed: Stats
  const stats = useMemo((): DeadlineStats => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

    const pending = deadlines.filter(d => d.status === 'pending');
    const overdue = pending.filter(d => {
      if (!d.deadline_date) return false;
      return new Date(d.deadline_date) < today;
    });
    const critical = pending.filter(d =>
      d.priority === 'critical' || d.priority === 'fatal'
    );
    const completedThisMonth = deadlines.filter(d => {
      if (d.status !== 'completed' || !d.updated_at) return false;
      return new Date(d.updated_at) >= startOfMonth;
    });

    // By priority
    const byPriority: Record<string, number> = {};
    pending.forEach(d => {
      const priority = d.priority || 'standard';
      byPriority[priority] = (byPriority[priority] || 0) + 1;
    });

    // By case
    const byCaseId: Record<string, number> = {};
    pending.forEach(d => {
      byCaseId[d.case_id] = (byCaseId[d.case_id] || 0) + 1;
    });

    return {
      total: deadlines.length,
      pending: pending.length,
      overdue: overdue.length,
      critical: critical.length,
      completedThisMonth: completedThisMonth.length,
      byPriority,
      byCaseId,
    };
  }, [deadlines]);

  return {
    deadlines,
    cases,
    loading,
    error,
    refetch: fetchDeadlines,
    createDeadline,
    updateDeadline,
    updateDeadlineStatus,
    rescheduleDeadline,
    deleteDeadline,
    overdueDeadlines,
    upcomingDeadlines,
    todayDeadlines,
    stats,
  };
}
