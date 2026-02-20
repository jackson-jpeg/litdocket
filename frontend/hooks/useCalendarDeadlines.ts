'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import apiClient from '@/lib/api-client';
import { eventBus, useEventBus } from '@/lib/eventBus';

export interface CalendarDeadline {
  id: string;
  case_id: string;
  case_number: string;
  case_title: string;
  title: string;
  description?: string;
  deadline_date: string | null;
  deadline_type?: string;
  priority: string;
  status: string;
  party_role?: string;
  action_required?: string;
  applicable_rule?: string;
  is_calculated: boolean;
  is_manually_overridden: boolean;
  is_estimated: boolean;
  created_at: string;
  updated_at: string;
}

export interface CaseInfo {
  id: string;
  case_number: string;
  title: string;
}

export interface CalendarFilters {
  status?: string;
  priority?: string;
  caseIds?: string[];
  startDate?: string;
  endDate?: string;
}

interface UseCalendarDeadlinesReturn {
  deadlines: CalendarDeadline[];
  cases: CaseInfo[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  rescheduleDeadline: (deadlineId: string, newDate: Date, reason?: string) => Promise<boolean>;
  createDeadline: (data: CreateDeadlineData) => Promise<CalendarDeadline | null>;
  updateDeadlineStatus: (deadlineId: string, status: string) => Promise<boolean>;
  // Computed data for sidebar
  overdueDeadlines: CalendarDeadline[];
  upcomingDeadlines: CalendarDeadline[];
  stats: {
    total: number;
    pending: number;
    overdue: number;
    critical: number;
    completedThisMonth: number;
  };
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

export function useCalendarDeadlines(filters?: CalendarFilters): UseCalendarDeadlinesReturn {
  const [deadlines, setDeadlines] = useState<CalendarDeadline[]>([]);
  const [cases, setCases] = useState<CaseInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch all deadlines in a single call
  const fetchDeadlines = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = new URLSearchParams();
      if (filters?.status) params.set('status', filters.status);
      if (filters?.priority) params.set('priority', filters.priority);
      if (filters?.caseIds?.length) params.set('case_ids', filters.caseIds.join(','));
      if (filters?.startDate) params.set('start_date', filters.startDate);
      if (filters?.endDate) params.set('end_date', filters.endDate);

      const queryString = params.toString();
      const url = `/api/v1/deadlines/user/all${queryString ? `?${queryString}` : ''}`;

      const response = await apiClient.get(url);
      setDeadlines(response.data);

      // Extract unique cases from deadlines
      const caseMap = new Map<string, CaseInfo>();
      response.data.forEach((d: CalendarDeadline) => {
        if (!caseMap.has(d.case_id)) {
          caseMap.set(d.case_id, {
            id: d.case_id,
            case_number: d.case_number,
            title: d.case_title,
          });
        }
      });
      setCases(Array.from(caseMap.values()));

    } catch (err: unknown) {
      console.error('Failed to fetch deadlines:', err);
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : err instanceof Error ? err.message : 'Failed to load deadlines';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [filters?.status, filters?.priority, filters?.caseIds?.join(','), filters?.startDate, filters?.endDate]);

  // Initial fetch and subscribe to events
  useEffect(() => {
    fetchDeadlines();
  }, [fetchDeadlines]);

  // Subscribe to calendar refresh events
  useEventBus('calendar:refresh', useCallback(() => {
    fetchDeadlines();
  }, [fetchDeadlines]));

  // Reschedule deadline (for drag-drop)
  const rescheduleDeadline = useCallback(async (
    deadlineId: string,
    newDate: Date,
    reason?: string
  ): Promise<boolean> => {
    try {
      const formattedDate = newDate.toISOString().split('T')[0];

      // Optimistic update
      setDeadlines(prev => prev.map(d =>
        d.id === deadlineId
          ? { ...d, deadline_date: formattedDate, is_manually_overridden: true }
          : d
      ));

      await apiClient.patch(`/api/v1/deadlines/${deadlineId}/reschedule`, {
        new_date: formattedDate,
        reason: reason || undefined,
      });

      return true;
    } catch (err: unknown) {
      console.error('Failed to reschedule deadline:', err);
      // Revert on error
      fetchDeadlines();
      return false;
    }
  }, [fetchDeadlines]);

  // Create new deadline
  const createDeadline = useCallback(async (data: CreateDeadlineData): Promise<CalendarDeadline | null> => {
    try {
      const response = await apiClient.post('/api/v1/deadlines/', data);

      // Add to local state
      const newDeadline = response.data.deadline;
      setDeadlines(prev => [...prev, newDeadline].sort((a, b) => {
        if (!a.deadline_date) return 1;
        if (!b.deadline_date) return -1;
        return new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime();
      }));

      return newDeadline;
    } catch (err: unknown) {
      console.error('Failed to create deadline:', err);
      return null;
    }
  }, []);

  // Update deadline status
  const updateDeadlineStatus = useCallback(async (
    deadlineId: string,
    status: string
  ): Promise<boolean> => {
    try {
      // Optimistic update
      setDeadlines(prev => prev.map(d =>
        d.id === deadlineId ? { ...d, status } : d
      ));

      await apiClient.patch(`/api/v1/deadlines/${deadlineId}/status?status=${status}`);
      return true;
    } catch (err: unknown) {
      console.error('Failed to update deadline status:', err);
      fetchDeadlines();
      return false;
    }
  }, [fetchDeadlines]);

  // Compute overdue deadlines (past date + pending status)
  const overdueDeadlines = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return deadlines.filter(d => {
      if (!d.deadline_date || d.status !== 'pending') return false;
      const deadlineDate = new Date(d.deadline_date);
      deadlineDate.setHours(0, 0, 0, 0);
      return deadlineDate < today;
    }).sort((a, b) => {
      // Most overdue first
      return new Date(a.deadline_date!).getTime() - new Date(b.deadline_date!).getTime();
    });
  }, [deadlines]);

  // Compute upcoming deadlines (next 7 days)
  const upcomingDeadlines = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const weekFromNow = new Date(today);
    weekFromNow.setDate(weekFromNow.getDate() + 7);

    return deadlines.filter(d => {
      if (!d.deadline_date || d.status !== 'pending') return false;
      const deadlineDate = new Date(d.deadline_date);
      deadlineDate.setHours(0, 0, 0, 0);
      return deadlineDate >= today && deadlineDate <= weekFromNow;
    }).sort((a, b) => {
      return new Date(a.deadline_date!).getTime() - new Date(b.deadline_date!).getTime();
    });
  }, [deadlines]);

  // Compute stats
  const stats = useMemo(() => {
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
      if (d.status !== 'completed') return false;
      const updatedAt = new Date(d.updated_at);
      return updatedAt >= startOfMonth;
    });

    return {
      total: deadlines.length,
      pending: pending.length,
      overdue: overdue.length,
      critical: critical.length,
      completedThisMonth: completedThisMonth.length,
    };
  }, [deadlines]);

  return {
    deadlines,
    cases,
    loading,
    error,
    refetch: fetchDeadlines,
    rescheduleDeadline,
    createDeadline,
    updateDeadlineStatus,
    overdueDeadlines,
    upcomingDeadlines,
    stats,
  };
}
