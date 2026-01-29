/**
 * Deadlines Feature Module
 *
 * Unified deadline management components and hooks.
 * This module consolidates deadline functionality from
 * the calendar and cases features.
 */

// Components
export { default as UnifiedDeadlineModal } from './components/UnifiedDeadlineModal';
export type { TriggerInfo } from './components/UnifiedDeadlineModal';

export { default as DeadlineCard } from './components/DeadlineCard';
export { DeadlineCard as DeadlineCardMemo } from './components/DeadlineCard';

export { default as DeadlineList } from './components/DeadlineList';

// Hooks
export { useDeadlines } from './hooks/useDeadlines';
export type {
  CaseInfo,
  DeadlineFilters,
  CreateDeadlineData,
  DeadlineStats,
} from './hooks/useDeadlines';

// Re-export types from main types file
export type { Deadline, CalendarDeadline } from '@/types';
