/**
 * useMatterHealth - Lazy-loaded matter health cards hook
 *
 * Only fetches when enabled (cases tab selected).
 * Background revalidation without UI flicker.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/lib/api-client';

export interface MatterHealthCard {
  case_id: string;
  case_number: string;
  title: string;
  court: string;
  judge: string;
  judge_stats: {
    total_cases_with_judge: number;
  };
  jurisdiction: string;
  case_type: string;
  progress: {
    completed: number;
    pending: number;
    total: number;
    percentage: number;
  };
  next_deadline: {
    title: string;
    date: string;
    days_until: number;
    priority: string;
  } | null;
  next_deadline_urgency: string;
  health_status: string;
  document_count: number;
  filing_date: string | null;
}

export interface CriticalCase {
  case_id: string;
  case_number: string;
  title: string;
  court: string | null;
  next_deadline_date: string;
  next_deadline_title: string;
  days_until_deadline: number;
  urgency_level: string;
  total_pending_deadlines: number;
}

export interface ZombieCase {
  case_id: string;
  case_number: string;
  title: string;
  court: string | null;
  judge: string | null;
  last_activity: string | null;
  risk_level: string;
  recommended_action: string;
}

export interface MatterHealthData {
  health_cards: MatterHealthCard[];
  critical_cases: CriticalCase[];
  zombie_cases: ZombieCase[];
}

interface UseMatterHealthResult {
  data: MatterHealthData | null;
  isLoading: boolean;
  error: string | null;
  mutate: () => Promise<void>;
}

const REVALIDATE_INTERVAL = 60000; // 60 seconds

export function useMatterHealth(enabled = true): UseMatterHealthResult {
  const [data, setData] = useState<MatterHealthData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isInitialLoad = useRef(true);
  const hasFetched = useRef(false);

  const fetchHealth = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setIsLoading(true);
    }

    try {
      const response = await apiClient.get<MatterHealthData>('/api/v1/dashboard/health');
      setData(response.data);
      setError(null);
      hasFetched.current = true;
    } catch (err) {
      console.error('Failed to fetch matter health:', err);
      if (isInitialLoad.current) {
        setError('Failed to load matter health');
      }
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
      isInitialLoad.current = false;
    }
  }, []);

  // Only fetch when enabled and haven't fetched yet
  useEffect(() => {
    if (enabled && !hasFetched.current) {
      fetchHealth(true);
    }
  }, [enabled, fetchHealth]);

  // Background revalidation only when enabled
  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchHealth(false);
      }
    }, REVALIDATE_INTERVAL);

    return () => clearInterval(interval);
  }, [enabled, fetchHealth]);

  const mutate = useCallback(async () => {
    await fetchHealth(false);
  }, [fetchHealth]);

  return {
    data,
    isLoading: enabled ? isLoading : false,
    error,
    mutate,
  };
}
