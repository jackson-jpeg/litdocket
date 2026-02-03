/**
 * useDashboardStats - Case statistics hook
 *
 * Loads case/document/deadline counts by category.
 * Background revalidation without UI flicker.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/lib/api-client';

export interface DashboardStats {
  total_cases: number;
  total_documents: number;
  total_pending_deadlines: number;
  by_jurisdiction: {
    state: number;
    federal: number;
    unknown: number;
  };
  by_case_type: {
    civil: number;
    criminal: number;
    appellate: number;
    other: number;
  };
}

interface UseDashboardStatsResult {
  data: DashboardStats | null;
  isLoading: boolean;
  error: string | null;
  mutate: () => Promise<void>;
}

const REVALIDATE_INTERVAL = 30000;

export function useDashboardStats(): UseDashboardStatsResult {
  const [data, setData] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isInitialLoad = useRef(true);

  const fetchStats = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setIsLoading(true);
    }

    try {
      const response = await apiClient.get<DashboardStats>('/api/v1/dashboard/stats');
      setData(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch dashboard stats:', err);
      if (isInitialLoad.current) {
        setError('Failed to load statistics');
      }
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
      isInitialLoad.current = false;
    }
  }, []);

  useEffect(() => {
    fetchStats(true);
  }, [fetchStats]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchStats(false);
      }
    }, REVALIDATE_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchStats]);

  const mutate = useCallback(async () => {
    await fetchStats(false);
  }, [fetchStats]);

  return {
    data,
    isLoading,
    error,
    mutate,
  };
}
