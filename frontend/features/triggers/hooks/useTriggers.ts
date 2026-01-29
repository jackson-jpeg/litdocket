'use client';

/**
 * useTriggers - Unified Trigger Management Hook
 *
 * Handles all trigger operations:
 * - Fetch triggers for a case
 * - Create new triggers (with deadline generation)
 * - Update trigger dates (with cascade recalculation)
 * - Delete triggers
 *
 * Trigger events are the core of the deadline calculation system.
 * One trigger (e.g., Trial Date) generates 20-50+ dependent deadlines.
 */

import { useState, useCallback, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import { emitEvent, useEventBus } from '@/lib/eventBus';

// Trigger type definition
export interface Trigger {
  id: string;
  case_id: string;
  title: string;
  trigger_type: string;
  trigger_date: string;
  status: string;
  jurisdiction?: string;
  court_type?: string;
  service_method?: string;
  created_at?: string;
  updated_at?: string;
  // Nested child deadlines (from detailed fetch)
  deadlines?: TriggerDeadline[];
  child_deadlines_count?: number;
}

export interface TriggerDeadline {
  id: string;
  title: string;
  description?: string;
  deadline_date: string | null;
  priority: string;
  status: string;
  is_overdue: boolean;
  applicable_rule?: string;
  calculation_basis?: string;
  is_manually_overridden: boolean;
  auto_recalculate: boolean;
}

export interface TriggerType {
  id: string;
  trigger_type: string;
  name: string;
  friendly_name: string;
  description: string;
  category: string;
  icon: string;
  example: string;
  generates_approx: number;
}

export interface CreateTriggerData {
  case_id: string;
  trigger_type: string;
  trigger_date: string;
  jurisdiction?: string;
  court_type?: string;
  service_method?: string;
}

export interface UpdateTriggerDateData {
  new_date: string;
  reason?: string;
}

interface UseTriggersReturn {
  triggers: Trigger[];
  triggerTypes: TriggerType[];
  loading: boolean;
  error: string | null;

  // Actions
  refetch: () => Promise<void>;
  fetchTriggerTypes: (query?: string) => Promise<TriggerType[]>;
  createTrigger: (data: CreateTriggerData) => Promise<{ trigger: Trigger; deadlinesCreated: number } | null>;
  updateTriggerDate: (triggerId: string, data: UpdateTriggerDateData) => Promise<boolean>;
  recalculateTrigger: (triggerId: string) => Promise<boolean>;
  deleteTrigger: (triggerId: string) => Promise<boolean>;
  previewTrigger: (data: CreateTriggerData) => Promise<{ count: number; deadlines: TriggerDeadline[] } | null>;
}

export function useTriggers(caseId?: string): UseTriggersReturn {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [triggerTypes, setTriggerTypes] = useState<TriggerType[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch triggers for a case
  const fetchTriggers = useCallback(async () => {
    if (!caseId) {
      setTriggers([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(`/api/v1/triggers/case/${caseId}/triggers`);
      setTriggers(response.data.triggers || []);
    } catch (err: unknown) {
      console.error('Failed to fetch triggers:', err);
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || 'Failed to load triggers');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  // Initial fetch
  useEffect(() => {
    if (caseId) {
      fetchTriggers();
    }
  }, [caseId, fetchTriggers]);

  // Subscribe to events
  useEventBus('trigger:created', useCallback(() => {
    fetchTriggers();
  }, [fetchTriggers]));

  useEventBus('trigger:updated', useCallback(() => {
    fetchTriggers();
  }, [fetchTriggers]));

  useEventBus('trigger:deleted', useCallback(() => {
    fetchTriggers();
  }, [fetchTriggers]));

  // Fetch available trigger types
  const fetchTriggerTypes = useCallback(async (query?: string): Promise<TriggerType[]> => {
    try {
      const response = await apiClient.get('/api/v1/triggers/types', {
        params: query ? { q: query } : undefined,
      });
      const types = response.data.types || [];
      setTriggerTypes(types);
      return types;
    } catch (err) {
      console.error('Failed to fetch trigger types:', err);
      return [];
    }
  }, []);

  // Create new trigger
  const createTrigger = useCallback(async (
    data: CreateTriggerData
  ): Promise<{ trigger: Trigger; deadlinesCreated: number } | null> => {
    try {
      const response = await apiClient.post('/api/v1/triggers/create', {
        case_id: data.case_id,
        trigger_type: data.trigger_type,
        trigger_date: data.trigger_date,
        jurisdiction: data.jurisdiction || 'florida_state',
        court_type: data.court_type || 'civil',
        service_method: data.service_method || 'email',
      });

      const trigger = response.data.trigger_deadline;
      const deadlinesCreated = response.data.dependent_deadlines_created || 0;

      // Emit events
      emitEvent('trigger:created', { trigger, deadlinesCreated });
      emitEvent('calendar:refresh', {});

      // Refetch to get updated list
      await fetchTriggers();

      return { trigger, deadlinesCreated };
    } catch (err: unknown) {
      console.error('Failed to create trigger:', err);
      const axiosError = err as { response?: { data?: { detail?: string } } };
      throw new Error(axiosError.response?.data?.detail || 'Failed to create trigger');
    }
  }, [fetchTriggers]);

  // Preview trigger (without creating)
  const previewTrigger = useCallback(async (
    data: CreateTriggerData
  ): Promise<{ count: number; deadlines: TriggerDeadline[] } | null> => {
    try {
      const response = await apiClient.post('/api/v1/triggers/simulate', {
        trigger_type: data.trigger_type,
        trigger_date: data.trigger_date,
        jurisdiction: data.jurisdiction || 'florida_state',
        court_type: data.court_type || 'civil',
        service_method: data.service_method || 'email',
      });

      return {
        count: response.data.total_deadlines || 0,
        deadlines: response.data.deadlines || [],
      };
    } catch (err) {
      console.error('Failed to preview trigger:', err);
      return null;
    }
  }, []);

  // Update trigger date (cascades to dependent deadlines)
  const updateTriggerDate = useCallback(async (
    triggerId: string,
    data: UpdateTriggerDateData
  ): Promise<boolean> => {
    try {
      await apiClient.patch(`/api/v1/triggers/${triggerId}/update-date`, {
        new_date: data.new_date,
        reason: data.reason,
      });

      emitEvent('trigger:updated', { triggerId });
      emitEvent('calendar:refresh', {});
      await fetchTriggers();

      return true;
    } catch (err) {
      console.error('Failed to update trigger date:', err);
      return false;
    }
  }, [fetchTriggers]);

  // Recalculate all deadlines for a trigger
  const recalculateTrigger = useCallback(async (triggerId: string): Promise<boolean> => {
    try {
      await apiClient.patch(`/api/v1/triggers/${triggerId}/recalculate`);

      emitEvent('trigger:updated', { triggerId });
      emitEvent('calendar:refresh', {});
      await fetchTriggers();

      return true;
    } catch (err) {
      console.error('Failed to recalculate trigger:', err);
      return false;
    }
  }, [fetchTriggers]);

  // Delete trigger (and all dependent deadlines)
  const deleteTrigger = useCallback(async (triggerId: string): Promise<boolean> => {
    try {
      await apiClient.delete(`/api/v1/triggers/${triggerId}`);

      // Optimistic update
      setTriggers(prev => prev.filter(t => t.id !== triggerId));

      emitEvent('trigger:deleted', { triggerId });
      emitEvent('calendar:refresh', {});

      return true;
    } catch (err) {
      console.error('Failed to delete trigger:', err);
      await fetchTriggers(); // Revert on error
      return false;
    }
  }, [fetchTriggers]);

  return {
    triggers,
    triggerTypes,
    loading,
    error,
    refetch: fetchTriggers,
    fetchTriggerTypes,
    createTrigger,
    updateTriggerDate,
    recalculateTrigger,
    deleteTrigger,
    previewTrigger,
  };
}
