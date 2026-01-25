import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api-client';
import { eventBus } from '@/lib/eventBus';

interface HeatmapDay {
  risk_score: number;
  deadline_count: number;
  intensity: 'low' | 'medium' | 'high' | 'very_high' | 'extreme';
}

interface WorkloadStats {
  average_deadlines_per_day: number;
  peak_workload_day: {
    date: string;
    deadline_count: number;
  } | null;
  saturated_days_count: number;
  total_deadlines: number;
  analysis_period_days: number;
}

interface BurnoutAlert {
  type: string;
  start_date: string;
  end_date: string;
  consecutive_days: number;
  message: string;
  severity: string;
}

interface AISuggestion {
  date: string;
  risk_score: number;
  ai_recommendations: Array<{
    deadline_title: string;
    deadline_id?: string;
    move_to_date: string;
    reason: string;
  }>;
  summary: string;
  adjacent_days?: Array<{
    date: string;
    current_deadlines: number;
    risk_score: number;
    available_capacity: number;
  }>;
}

interface RiskDay {
  date: string;
  risk_score: number;
  deadline_count: number;
  fatal_count: number;
  critical_count: number;
  important_count: number;
  intensity: string;
}

interface WorkloadAnalysis {
  risk_days: RiskDay[];
  burnout_alerts: BurnoutAlert[];
  ai_suggestions: AISuggestion[];
  workload_heatmap: Record<string, HeatmapDay>;
  statistics: WorkloadStats;
}

interface UseWorkloadOptions {
  daysAhead?: number;
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
  onAnalysisComplete?: (analysis: WorkloadAnalysis) => void;
}

export function useWorkload({
  daysAhead = 60,
  autoRefresh = false,
  refreshInterval = 300000, // 5 minutes default
  onAnalysisComplete
}: UseWorkloadOptions = {}) {
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<WorkloadAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch workload analysis
   */
  const fetchAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get('/workload/analysis', {
        params: { days_ahead: daysAhead }
      });

      if (response.data.success) {
        const analysisData = response.data.data as WorkloadAnalysis;
        setAnalysis(analysisData);
        onAnalysisComplete?.(analysisData);
        return analysisData;
      } else {
        throw new Error(response.data.message || 'Analysis failed');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to analyze workload';
      setError(errorMessage);
      console.error('Workload analysis error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [daysAhead, onAnalysisComplete]);

  /**
   * Get just the heatmap data (faster, lighter response)
   */
  const fetchHeatmap = useCallback(async () => {
    try {
      const response = await apiClient.get('/workload/heatmap', {
        params: { days_ahead: daysAhead }
      });

      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (err: any) {
      console.error('Heatmap fetch error:', err);
      return null;
    }
  }, [daysAhead]);

  /**
   * Get AI rebalancing suggestions
   */
  const fetchSuggestions = useCallback(async () => {
    try {
      const response = await apiClient.get('/workload/suggestions', {
        params: { days_ahead: daysAhead }
      });

      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (err: any) {
      console.error('Suggestions fetch error:', err);
      return null;
    }
  }, [daysAhead]);

  /**
   * Refresh analysis (debounced)
   */
  const refresh = useCallback(() => {
    // Debounce to avoid excessive API calls
    const timeoutId = setTimeout(() => {
      fetchAnalysis();
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [fetchAnalysis]);

  /**
   * Get intensity level for a specific date
   */
  const getIntensityForDate = useCallback((date: string): HeatmapDay | null => {
    if (!analysis?.workload_heatmap) return null;
    return analysis.workload_heatmap[date] || null;
  }, [analysis]);

  /**
   * Check if a date is high-risk
   */
  const isHighRiskDay = useCallback((date: string): boolean => {
    const intensity = getIntensityForDate(date);
    return intensity ? ['high', 'very_high', 'extreme'].includes(intensity.intensity) : false;
  }, [getIntensityForDate]);

  /**
   * Get burnout risk for current period
   */
  const getBurnoutRisk = useCallback((): 'none' | 'low' | 'medium' | 'high' => {
    if (!analysis?.burnout_alerts) return 'none';

    const alertCount = analysis.burnout_alerts.length;
    if (alertCount === 0) return 'none';
    if (alertCount === 1) return 'low';
    if (alertCount === 2) return 'medium';
    return 'high';
  }, [analysis]);

  // Initial fetch
  useEffect(() => {
    fetchAnalysis();
  }, [daysAhead]); // Re-fetch when daysAhead changes

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const intervalId = setInterval(() => {
      fetchAnalysis();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [autoRefresh, refreshInterval, fetchAnalysis]);

  // Listen for deadline changes and refresh
  useEffect(() => {
    const handleDeadlineChange = () => {
      refresh();
    };

    eventBus.on('deadline:created', handleDeadlineChange);
    eventBus.on('deadline:updated', handleDeadlineChange);
    eventBus.on('deadline:deleted', handleDeadlineChange);
    eventBus.on('deadlines:bulk-updated', handleDeadlineChange);

    return () => {
      eventBus.off('deadline:created', handleDeadlineChange);
      eventBus.off('deadline:updated', handleDeadlineChange);
      eventBus.off('deadline:deleted', handleDeadlineChange);
      eventBus.off('deadlines:bulk-updated', handleDeadlineChange);
    };
  }, [refresh]);

  return {
    // State
    loading,
    analysis,
    error,

    // Computed values
    riskDays: analysis?.risk_days || [],
    burnoutAlerts: analysis?.burnout_alerts || [],
    aiSuggestions: analysis?.ai_suggestions || [],
    heatmap: analysis?.workload_heatmap || {},
    stats: analysis?.statistics || null,

    // Methods
    refresh,
    fetchAnalysis,
    fetchHeatmap,
    fetchSuggestions,
    getIntensityForDate,
    isHighRiskDay,
    getBurnoutRisk
  };
}

/**
 * Example usage:
 *
 * const {
 *   loading,
 *   riskDays,
 *   burnoutAlerts,
 *   aiSuggestions,
 *   heatmap,
 *   stats,
 *   isHighRiskDay
 * } = useWorkload({ daysAhead: 60, autoRefresh: true });
 *
 * // Check if a date is high-risk
 * if (isHighRiskDay('2026-02-15')) {
 *   console.log('⚠️ High workload day!');
 * }
 *
 * // Display burnout alerts
 * burnoutAlerts.forEach(alert => {
 *   console.log(alert.message);
 * });
 *
 * // Show AI suggestions
 * aiSuggestions.forEach(suggestion => {
 *   console.log(`${suggestion.date}: ${suggestion.summary}`);
 * });
 */
