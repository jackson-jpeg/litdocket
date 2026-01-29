/**
 * Triggers Feature Module
 *
 * Unified trigger management components and hooks.
 * Triggers are the core of the deadline calculation system -
 * one trigger event generates 20-50+ dependent deadlines.
 */

// Components
export { default as TriggerTimeline } from './components/TriggerTimeline';
export type { TriggerData } from './components/TriggerTimeline';

// Re-export existing components that remain useful
// These can be imported from their original location or from here
// export { default as SmartEventEntry } from '@/features/cases/components/triggers/SmartEventEntry';
// export { default as TriggerEventsPanel } from '@/features/cases/components/triggers/TriggerEventsPanel';

// Hooks
export { useTriggers } from './hooks/useTriggers';
export type {
  Trigger,
  TriggerDeadline,
  TriggerType,
  CreateTriggerData,
  UpdateTriggerDateData,
} from './hooks/useTriggers';
