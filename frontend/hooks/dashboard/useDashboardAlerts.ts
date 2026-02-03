/**
 * useDashboardAlerts - Critical path hook for deadline alerts
 *
 * Loads overdue/urgent/upcoming deadline counts immediately.
 * Background revalidation without UI flicker.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/lib/api-client';

interface DeadlineAlert {
  id: string;
  case_id: string;
  title: string;
  deadline_date: string | null;
  priority: string;
  party_role: string | null;
  action_required: string | null;
  urgency_level: string;
  days_until: number | null;
  rule_citation: string | null;
}

interface AlertCategory {
  count: number;
  deadlines: DeadlineAlert[];
}

export interface DashboardAlerts {
  overdue: AlertCategory;
  urgent: AlertCategory;
  upcoming_week: AlertCategory;
  upcoming_month: AlertCategory;
}

interface UseDashboardAlertsResult {
  data: DashboardAlerts | null;
  isLoading: boolean;
  error: string | null;
  mutate: () => Promise<void>;
  lastUpdated: Date | null;
}

const REVALIDATE_INTERVAL = 30000; // 30 seconds

export function useDashboardAlerts(): UseDashboardAlertsResult {
  const [data, setData] = useState<DashboardAlerts | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const isInitialLoad = useRef(true);

  const fetchAlerts = useCallback(async (showLoading = false) => {
    // Only show loading on initial load, not on background refresh
    if (showLoading) {
      setIsLoading(true);
    }

    try {
      const response = await apiClient.get<DashboardAlerts>('/api/v1/dashboard/alerts');
      setData(response.data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Failed to fetch dashboard alerts:', err);
      // Only set error on initial load, not on background refresh
      if (isInitialLoad.current) {
        setError('Failed to load alerts');
      }
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
      isInitialLoad.current = false;
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchAlerts(true);
  }, [fetchAlerts]);

  // Background revalidation with visibility awareness
  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchAlerts(false); // Don't show loading on background refresh
      }
    }, REVALIDATE_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchAlerts]);

  // Manual refresh function
  const mutate = useCallback(async () => {
    await fetchAlerts(false);
  }, [fetchAlerts]);

  return {
    data,
    isLoading,
    error,
    mutate,
    lastUpdated,
  };
}
