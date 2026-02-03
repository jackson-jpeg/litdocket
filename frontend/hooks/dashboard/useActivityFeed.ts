/**
 * useActivityFeed - Lazy-loaded activity feed hook
 *
 * Loads recent document uploads and case activity.
 * Background revalidation without UI flicker.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/lib/api-client';

export interface ActivityItem {
  type: string;
  timestamp: string;
  case_id: string;
  case_number: string;
  description: string;
  document_type: string | null;
  icon: string;
}

export interface ActivityFeedData {
  activities: ActivityItem[];
  total_count: number;
}

interface UseActivityFeedResult {
  data: ActivityFeedData | null;
  isLoading: boolean;
  error: string | null;
  mutate: () => Promise<void>;
}

const REVALIDATE_INTERVAL = 60000; // 60 seconds

export function useActivityFeed(limit = 10): UseActivityFeedResult {
  const [data, setData] = useState<ActivityFeedData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isInitialLoad = useRef(true);

  const fetchActivity = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setIsLoading(true);
    }

    try {
      const response = await apiClient.get<ActivityFeedData>('/api/v1/dashboard/activity', {
        params: { limit }
      });
      setData(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch activity feed:', err);
      if (isInitialLoad.current) {
        setError('Failed to load activity');
      }
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
      isInitialLoad.current = false;
    }
  }, [limit]);

  useEffect(() => {
    fetchActivity(true);
  }, [fetchActivity]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchActivity(false);
      }
    }, REVALIDATE_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchActivity]);

  const mutate = useCallback(async () => {
    await fetchActivity(false);
  }, [fetchActivity]);

  return {
    data,
    isLoading,
    error,
    mutate,
  };
}
