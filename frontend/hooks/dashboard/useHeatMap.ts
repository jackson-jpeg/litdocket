/**
 * useHeatMap - Lazy-loaded heat map data hook
 *
 * Only fetches when enabled (tab selected).
 * Background revalidation without UI flicker.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/lib/api-client';

interface HeatMapCell {
  severity: string;
  urgency: string;
  count: number;
  case_ids: string[];
  deadlines: Array<{
    id: string;
    case_id: string;
    title: string;
    deadline_date: string;
    days_until: number;
  }>;
}

export interface HeatMapData {
  matrix: HeatMapCell[];
  summary: {
    total: number;
    critical: number;
    today: number;
  };
}

interface UseHeatMapResult {
  data: HeatMapData | null;
  isLoading: boolean;
  error: string | null;
  mutate: () => Promise<void>;
}

const REVALIDATE_INTERVAL = 60000; // 60 seconds for lazy data

export function useHeatMap(enabled = true): UseHeatMapResult {
  const [data, setData] = useState<HeatMapData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isInitialLoad = useRef(true);
  const hasFetched = useRef(false);

  const fetchHeatMap = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setIsLoading(true);
    }

    try {
      const response = await apiClient.get<HeatMapData>('/api/v1/dashboard/heatmap');
      setData(response.data);
      setError(null);
      hasFetched.current = true;
    } catch (err) {
      console.error('Failed to fetch heat map:', err);
      if (isInitialLoad.current) {
        setError('Failed to load heat map');
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
      fetchHeatMap(true);
    }
  }, [enabled, fetchHeatMap]);

  // Background revalidation only when enabled
  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchHeatMap(false);
      }
    }, REVALIDATE_INTERVAL);

    return () => clearInterval(interval);
  }, [enabled, fetchHeatMap]);

  const mutate = useCallback(async () => {
    await fetchHeatMap(false);
  }, [fetchHeatMap]);

  return {
    data,
    isLoading: enabled ? isLoading : false,
    error,
    mutate,
  };
}
