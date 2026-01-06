/**
 * Centralized case data synchronization hook
 * Manages data flow and updates across all case components
 */

import { useCallback, useEffect, useRef } from 'react';
import { eventBus, useEventBus } from '@/lib/eventBus';

interface UseCaseSyncOptions {
  caseId: string;
  onDeadlinesUpdate?: () => void;
  onDocumentsUpdate?: () => void;
  onTriggersUpdate?: () => void;
  onCaseUpdate?: () => void;
  onInsightsUpdate?: () => void;
}

export function useCaseSync({
  caseId,
  onDeadlinesUpdate,
  onDocumentsUpdate,
  onTriggersUpdate,
  onCaseUpdate,
  onInsightsUpdate,
}: UseCaseSyncOptions) {
  const refreshTimerRef = useRef<NodeJS.Timeout>();

  // Debounced refresh to avoid too many API calls
  const debouncedRefresh = useCallback((callback?: () => void, delay = 500) => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }

    refreshTimerRef.current = setTimeout(() => {
      callback?.();
    }, delay);
  }, []);

  // Listen to deadline events
  useEventBus('deadline:created', useCallback(() => {
    debouncedRefresh(onDeadlinesUpdate);
  }, [debouncedRefresh, onDeadlinesUpdate]));

  useEventBus('deadline:updated', useCallback(() => {
    debouncedRefresh(onDeadlinesUpdate);
  }, [debouncedRefresh, onDeadlinesUpdate]));

  useEventBus('deadline:deleted', useCallback(() => {
    debouncedRefresh(onDeadlinesUpdate);
  }, [debouncedRefresh, onDeadlinesUpdate]));

  useEventBus('deadline:completed', useCallback(() => {
    debouncedRefresh(onDeadlinesUpdate);
  }, [debouncedRefresh, onDeadlinesUpdate]));

  useEventBus('deadlines:bulk-updated', useCallback(() => {
    debouncedRefresh(onDeadlinesUpdate);
  }, [debouncedRefresh, onDeadlinesUpdate]));

  // Listen to document events
  useEventBus('document:uploaded', useCallback(() => {
    debouncedRefresh(onDocumentsUpdate);
  }, [debouncedRefresh, onDocumentsUpdate]));

  useEventBus('document:analyzed', useCallback(() => {
    debouncedRefresh(onDocumentsUpdate);
  }, [debouncedRefresh, onDocumentsUpdate]));

  // Listen to trigger events
  useEventBus('trigger:created', useCallback(() => {
    debouncedRefresh(onTriggersUpdate);
    debouncedRefresh(onDeadlinesUpdate);
  }, [debouncedRefresh, onTriggersUpdate, onDeadlinesUpdate]));

  useEventBus('trigger:deleted', useCallback(() => {
    debouncedRefresh(onTriggersUpdate);
    debouncedRefresh(onDeadlinesUpdate);
  }, [debouncedRefresh, onTriggersUpdate, onDeadlinesUpdate]));

  // Listen to case update events
  useEventBus('case:updated', useCallback(() => {
    debouncedRefresh(onCaseUpdate);
  }, [debouncedRefresh, onCaseUpdate]));

  // Listen to calendar/insights refresh events
  useEventBus('calendar:refresh', useCallback(() => {
    debouncedRefresh(onDeadlinesUpdate, 300);
  }, [debouncedRefresh, onDeadlinesUpdate]));

  useEventBus('insights:refresh', useCallback(() => {
    debouncedRefresh(onInsightsUpdate, 1000); // Longer delay for insights
  }, [debouncedRefresh, onInsightsUpdate]));

  // Listen to chat action events
  useEventBus('chat:action-taken', useCallback((action) => {
    // Refresh everything when chat takes an action
    debouncedRefresh(() => {
      onDeadlinesUpdate?.();
      onTriggersUpdate?.();
      onCaseUpdate?.();
      onInsightsUpdate?.();
    }, 500);
  }, [debouncedRefresh, onDeadlinesUpdate, onTriggersUpdate, onCaseUpdate, onInsightsUpdate]));

  // Cleanup
  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, []);

  return {
    emitDeadlineCreated: (deadline: any) => eventBus.emit('deadline:created', deadline),
    emitDeadlineUpdated: (deadline: any) => eventBus.emit('deadline:updated', deadline),
    emitDeadlineDeleted: (deadlineId: string) => eventBus.emit('deadline:deleted', deadlineId),
    emitDeadlineCompleted: (deadline: any) => eventBus.emit('deadline:completed', deadline),
    emitDocumentUploaded: (document: any) => eventBus.emit('document:uploaded', document),
    emitCaseUpdated: () => eventBus.emit('case:updated'),
    refreshAll: () => {
      onDeadlinesUpdate?.();
      onDocumentsUpdate?.();
      onTriggersUpdate?.();
      onCaseUpdate?.();
      onInsightsUpdate?.();
    },
  };
}
