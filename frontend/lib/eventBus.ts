/**
 * Event Bus - Centralized event system for component communication
 * Enables loose coupling between components while maintaining reactivity
 */

// Type definitions for event payloads
// Using Record<string, unknown> for flexibility while still providing structure
export interface BaseDeadline {
  id: string;
  title?: string;
  deadline_date?: string | null;
  priority?: string;
  status?: string;
  case_id?: string;
}

export interface BaseDocument {
  id: string;
  file_name?: string;
  case_id?: string;
  document_type?: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
}

export interface ChatAction {
  type: string;
  payload?: Record<string, unknown>;
}

export interface CaseSelection {
  id: string | null;
  case_number?: string;
  title?: string;
}

export interface ToastData {
  message: string;
  type?: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

export interface RescheduledData {
  deadlineId: string;
  oldDate: string;
  newDate: string;
}

/**
 * Filter types for terminal commands
 */
export type FilterCommand =
  | { type: 'show'; value: 'all' | 'overdue' | 'pending' | 'completed' }
  | { type: 'priority'; value: string }
  | { type: 'search'; value: string }
  | { type: 'clear' };

// Flexible deadline/document type that accepts any object with at least an id
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FlexibleDeadline = { id: string; [key: string]: any };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FlexibleDocument = { id: string; [key: string]: any };

// Event map defining the payload type for each event
// Using looser types to accommodate various component implementations
export interface EventPayloadMap {
  'deadline:created': FlexibleDeadline;
  'deadline:updated': FlexibleDeadline;
  'deadline:deleted': string;
  'deadline:completed': FlexibleDeadline;
  'deadline:rescheduled': RescheduledData;
  'deadlines:bulk-updated': FlexibleDeadline[];
  'document:uploaded': FlexibleDocument;
  'document:analyzed': FlexibleDocument;
  'document:updated': FlexibleDocument;
  'case:updated': { id: string };
  'case:selected': CaseSelection;
  'chat:message-sent': ChatMessage;
  'chat:action-taken': ChatAction;
  'trigger:created': { id: string; trigger_type: string };
  'trigger:deleted': string;
  'calendar:refresh': void;
  'insights:refresh': void;
  'ui:show-success': string;
  'ui:show-error': string;
  'ui:show-warning': string;
  'ui:show-info': string;
  'toast:show': ToastData;
  'filter:apply': FilterCommand;
  'filter:clear': void;
}

export type AppEvent = keyof EventPayloadMap;

type EventCallback<T extends AppEvent> = (data: EventPayloadMap[T]) => void;

class EventBus {
  private events: Map<AppEvent, Set<EventCallback<AppEvent>>> = new Map();

  /**
   * Subscribe to an event
   * Returns unsubscribe function
   */
  on<T extends AppEvent>(event: T, callback: EventCallback<T>): () => void {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }

    this.events.get(event)!.add(callback as EventCallback<AppEvent>);

    // Return unsubscribe function
    return () => this.off(event, callback);
  }

  /**
   * Unsubscribe from an event
   */
  off<T extends AppEvent>(event: T, callback: EventCallback<T>): void {
    const callbacks = this.events.get(event);
    if (callbacks) {
      callbacks.delete(callback as EventCallback<AppEvent>);
    }
  }

  /**
   * Emit an event to all subscribers
   */
  emit<T extends AppEvent>(event: T, data: EventPayloadMap[T]): void {
    const callbacks = this.events.get(event);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Subscribe to an event only once
   */
  once<T extends AppEvent>(event: T, callback: EventCallback<T>): () => void {
    const onceCallback = ((data: EventPayloadMap[T]) => {
      callback(data);
      this.off(event, onceCallback as EventCallback<T>);
    }) as EventCallback<T>;

    return this.on(event, onceCallback);
  }

  /**
   * Clear all subscribers for an event
   */
  clear(event: AppEvent): void {
    this.events.delete(event);
  }

  /**
   * Clear all events
   */
  clearAll(): void {
    this.events.clear();
  }

  /**
   * Get subscriber count for an event
   */
  getSubscriberCount(event: AppEvent): number {
    return this.events.get(event)?.size || 0;
  }

  /**
   * Emit multiple related events in sequence
   */
  emitChain<T extends AppEvent>(events: Array<{ event: T; data: EventPayloadMap[T] }>, delay = 0): void {
    events.forEach((item, index) => {
      setTimeout(() => {
        this.emit(item.event, item.data);
      }, delay * index);
    });
  }
}

// Singleton instance
export const eventBus = new EventBus();

/**
 * React hook for subscribing to events
 */
import { useEffect } from 'react';

export function useEventBus<T extends AppEvent>(event: T, callback: EventCallback<T>) {
  useEffect(() => {
    const unsubscribe = eventBus.on(event, callback);
    return unsubscribe;
  }, [event, callback]);
}

/**
 * Convenience functions for common UI events
 */
export const uiEvents = {
  showSuccess: (message: string) => eventBus.emit('ui:show-success', message),
  showError: (message: string) => eventBus.emit('ui:show-error', message),
  showWarning: (message: string) => eventBus.emit('ui:show-warning', message),
  showInfo: (message: string) => eventBus.emit('ui:show-info', message),
};

/**
 * Convenience functions for deadline events
 */
export const deadlineEvents = {
  created: (deadline: FlexibleDeadline) => {
    eventBus.emit('deadline:created', deadline);
    eventBus.emit('calendar:refresh', undefined as unknown as void);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
  updated: (deadline: FlexibleDeadline) => {
    eventBus.emit('deadline:updated', deadline);
    eventBus.emit('calendar:refresh', undefined as unknown as void);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
  deleted: (deadlineId: string) => {
    eventBus.emit('deadline:deleted', deadlineId);
    eventBus.emit('calendar:refresh', undefined as unknown as void);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
  completed: (deadline: FlexibleDeadline) => {
    eventBus.emit('deadline:completed', deadline);
    eventBus.emit('calendar:refresh', undefined as unknown as void);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
  rescheduled: (data: RescheduledData) => {
    eventBus.emit('deadline:rescheduled', data);
    eventBus.emit('calendar:refresh', undefined as unknown as void);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
  bulkUpdated: (deadlines: FlexibleDeadline[]) => {
    eventBus.emit('deadlines:bulk-updated', deadlines);
    eventBus.emit('calendar:refresh', undefined as unknown as void);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
};

/**
 * Convenience functions for document events
 */
export const documentEvents = {
  uploaded: (document: FlexibleDocument) => {
    eventBus.emit('document:uploaded', document);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
  analyzed: (document: FlexibleDocument) => {
    eventBus.emit('document:analyzed', document);
    eventBus.emit('calendar:refresh', undefined as unknown as void);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
};

/**
 * Convenience functions for chat events
 */
export const chatEvents = {
  messageSent: (message: ChatMessage) => eventBus.emit('chat:message-sent', message),
  actionTaken: (action: ChatAction) => {
    eventBus.emit('chat:action-taken', action);
    eventBus.emit('calendar:refresh', undefined as unknown as void);
    eventBus.emit('insights:refresh', undefined as unknown as void);
  },
};

/**
 * Convenience functions for filter events (Terminal -> Data Grid)
 */
export const filterEvents = {
  showAll: () => eventBus.emit('filter:apply', { type: 'show', value: 'all' }),
  showOverdue: () => eventBus.emit('filter:apply', { type: 'show', value: 'overdue' }),
  showPending: () => eventBus.emit('filter:apply', { type: 'show', value: 'pending' }),
  showCompleted: () => eventBus.emit('filter:apply', { type: 'show', value: 'completed' }),
  filterByPriority: (priority: string) => eventBus.emit('filter:apply', { type: 'priority', value: priority }),
  search: (query: string) => eventBus.emit('filter:apply', { type: 'search', value: query }),
  clear: () => eventBus.emit('filter:clear', undefined as unknown as void),
};

/**
 * Convenience functions for case selection events (Quick View -> AI Terminal)
 */
export const caseEvents = {
  selected: (caseData: CaseSelection) =>
    eventBus.emit('case:selected', caseData),
  deselected: () => eventBus.emit('case:selected', { id: null }),
};
