/**
 * Event Bus - Centralized event system for component communication
 * Enables loose coupling between components while maintaining reactivity
 */

type EventCallback = (data?: any) => void;

export type AppEvent =
  | 'deadline:created'
  | 'deadline:updated'
  | 'deadline:deleted'
  | 'deadline:completed'
  | 'deadline:rescheduled'
  | 'deadlines:bulk-updated'
  | 'document:uploaded'
  | 'document:analyzed'
  | 'document:updated'
  | 'case:updated'
  | 'chat:message-sent'
  | 'chat:action-taken'
  | 'trigger:created'
  | 'trigger:deleted'
  | 'calendar:refresh'
  | 'insights:refresh'
  | 'ui:show-success'
  | 'ui:show-error'
  | 'ui:show-warning'
  | 'ui:show-info'
  | 'toast:show';

class EventBus {
  private events: Map<AppEvent, Set<EventCallback>> = new Map();

  /**
   * Subscribe to an event
   * Returns unsubscribe function
   */
  on(event: AppEvent, callback: EventCallback): () => void {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }

    this.events.get(event)!.add(callback);

    // Return unsubscribe function
    return () => this.off(event, callback);
  }

  /**
   * Unsubscribe from an event
   */
  off(event: AppEvent, callback: EventCallback): void {
    const callbacks = this.events.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }

  /**
   * Emit an event to all subscribers
   */
  emit(event: AppEvent, data?: any): void {
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
  once(event: AppEvent, callback: EventCallback): () => void {
    const onceCallback = (data?: any) => {
      callback(data);
      this.off(event, onceCallback);
    };

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
  emitChain(events: Array<{ event: AppEvent; data?: any }>, delay = 0): void {
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

export function useEventBus(event: AppEvent, callback: EventCallback) {
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
  created: (deadline: any) => {
    eventBus.emit('deadline:created', deadline);
    eventBus.emit('calendar:refresh');
    eventBus.emit('insights:refresh');
  },
  updated: (deadline: any) => {
    eventBus.emit('deadline:updated', deadline);
    eventBus.emit('calendar:refresh');
    eventBus.emit('insights:refresh');
  },
  deleted: (deadlineId: string) => {
    eventBus.emit('deadline:deleted', deadlineId);
    eventBus.emit('calendar:refresh');
    eventBus.emit('insights:refresh');
  },
  completed: (deadline: any) => {
    eventBus.emit('deadline:completed', deadline);
    eventBus.emit('calendar:refresh');
    eventBus.emit('insights:refresh');
  },
  rescheduled: (data: { deadlineId: string; oldDate: string; newDate: string }) => {
    eventBus.emit('deadline:rescheduled', data);
    eventBus.emit('calendar:refresh');
    eventBus.emit('insights:refresh');
  },
  bulkUpdated: (deadlines: any[]) => {
    eventBus.emit('deadlines:bulk-updated', deadlines);
    eventBus.emit('calendar:refresh');
    eventBus.emit('insights:refresh');
  },
};

/**
 * Convenience functions for document events
 */
export const documentEvents = {
  uploaded: (document: any) => {
    eventBus.emit('document:uploaded', document);
    eventBus.emit('insights:refresh');
  },
  analyzed: (document: any) => {
    eventBus.emit('document:analyzed', document);
    eventBus.emit('calendar:refresh');
    eventBus.emit('insights:refresh');
  },
};

/**
 * Convenience functions for chat events
 */
export const chatEvents = {
  messageSent: (message: any) => eventBus.emit('chat:message-sent', message),
  actionTaken: (action: any) => {
    eventBus.emit('chat:action-taken', action);
    eventBus.emit('calendar:refresh');
    eventBus.emit('insights:refresh');
  },
};
