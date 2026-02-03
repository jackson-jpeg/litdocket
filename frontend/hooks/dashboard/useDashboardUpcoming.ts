/**
 * useDashboardUpcoming - Upcoming deadlines hook
 *
 * Loads next 30 days of deadlines.
 * Background revalidation without UI flicker.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/lib/api-client';

export interface UpcomingDeadline {
  id: string;
  case_id: string;
  title: string;
  deadline_date: string | null;
  deadline_time: string | null;
  priority: string;
  party_role: string | null;
  action_required: string | null;
  urgency_level: string;
  days_until: number | null;
  rule_citation: string | null;
}

export interface DashboardUpcoming {
  deadlines: UpcomingDeadline[];
  total_count: number;
  range_days: number;
}

interface UseDashboardUpcomingResult {
  data: DashboardUpcoming | null;
  isLoading: boolean;
  error: string | null;
  mutate: () => Promise<void>;
}

const REVALIDATE_INTERVAL = 30000;

export function useDashboardUpcoming(days = 30, limit = 20): UseDashboardUpcomingResult {
  const [data, setData] = useState<DashboardUpcoming | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isInitialLoad = useRef(true);

  const fetchUpcoming = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setIsLoading(true);
    }

    try {
      const response = await apiClient.get<DashboardUpcoming>('/api/v1/dashboard/upcoming', {
        params: { days, limit }
      });
      setData(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch upcoming deadlines:', err);
      if (isInitialLoad.current) {
        setError('Failed to load upcoming deadlines');
      }
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
      isInitialLoad.current = false;
    }
  }, [days, limit]);

  useEffect(() => {
    fetchUpcoming(true);
  }, [fetchUpcoming]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchUpcoming(false);
      }
    }, REVALIDATE_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchUpcoming]);

  const mutate = useCallback(async () => {
    await fetchUpcoming(false);
  }, [fetchUpcoming]);

  return {
    data,
    isLoading,
    error,
    mutate,
  };
}
