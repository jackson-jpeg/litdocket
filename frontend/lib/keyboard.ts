/**
 * Keyboard Shortcuts - Centralized Configuration
 *
 * Handles cross-platform keyboard shortcuts (Mac ⌘ vs Windows Ctrl)
 * All shortcuts should be defined here for consistency.
 */

export type Platform = 'mac' | 'windows' | 'unknown';

/**
 * Detect the user's platform
 */
export function detectPlatform(): Platform {
  if (typeof window === 'undefined') return 'unknown';

  const userAgent = window.navigator.userAgent.toLowerCase();
  const platform = window.navigator.platform?.toLowerCase() || '';

  if (platform.includes('mac') || userAgent.includes('mac')) {
    return 'mac';
  }
  if (platform.includes('win') || userAgent.includes('win')) {
    return 'windows';
  }
  return 'windows'; // Default to Windows conventions
}

/**
 * Get the modifier key for the current platform
 */
export function getModifierKey(): string {
  return detectPlatform() === 'mac' ? '⌘' : 'Ctrl';
}

/**
 * Get the alt/option key for the current platform
 */
export function getAltKey(): string {
  return detectPlatform() === 'mac' ? '⌥' : 'Alt';
}

/**
 * Get the shift key symbol
 */
export function getShiftKey(): string {
  return detectPlatform() === 'mac' ? '⇧' : 'Shift';
}

export interface KeyboardShortcut {
  /** Unique identifier for the shortcut */
  id: string;
  /** Human-readable label */
  label: string;
  /** Description of what the shortcut does */
  description: string;
  /** Key code (e.g., 'k', 'n', 'Escape') */
  key: string;
  /** Whether Cmd/Ctrl is required */
  meta?: boolean;
  /** Whether Shift is required */
  shift?: boolean;
  /** Whether Alt/Option is required */
  alt?: boolean;
  /** Category for grouping in UI */
  category: ShortcutCategory;
}

export type ShortcutCategory = 'navigation' | 'actions' | 'editing' | 'views';

/**
 * All keyboard shortcuts defined centrally
 */
export const KEYBOARD_SHORTCUTS: KeyboardShortcut[] = [
  // Navigation
  {
    id: 'global-search',
    label: 'Global Search',
    description: 'Open search modal',
    key: 'k',
    meta: true,
    category: 'navigation',
  },
  {
    id: 'go-dashboard',
    label: 'Dashboard',
    description: 'Go to dashboard',
    key: 'h',
    meta: true,
    category: 'navigation',
  },
  {
    id: 'go-cases',
    label: 'Cases',
    description: 'Go to cases list',
    key: 'c',
    meta: true,
    shift: true,
    category: 'navigation',
  },
  {
    id: 'go-calendar',
    label: 'Calendar',
    description: 'Go to calendar view',
    key: 'd',
    meta: true,
    category: 'navigation',
  },

  // Actions
  {
    id: 'new-case',
    label: 'New Case',
    description: 'Create a new case',
    key: 'n',
    meta: true,
    category: 'actions',
  },
  {
    id: 'new-deadline',
    label: 'New Deadline',
    description: 'Add a new deadline',
    key: 'n',
    meta: true,
    shift: true,
    category: 'actions',
  },
  {
    id: 'save',
    label: 'Save',
    description: 'Save current item',
    key: 's',
    meta: true,
    category: 'actions',
  },
  {
    id: 'ai-assistant',
    label: 'AI Assistant',
    description: 'Open AI command bar',
    key: 'j',
    meta: true,
    category: 'actions',
  },

  // Views
  {
    id: 'toggle-sidebar',
    label: 'Toggle Sidebar',
    description: 'Show/hide sidebar',
    key: 'b',
    meta: true,
    category: 'views',
  },
  {
    id: 'shortcuts-help',
    label: 'Shortcuts Help',
    description: 'Show keyboard shortcuts',
    key: '/',
    meta: true,
    category: 'views',
  },

  // Editing
  {
    id: 'escape',
    label: 'Close/Cancel',
    description: 'Close modal or cancel action',
    key: 'Escape',
    category: 'editing',
  },
];

/**
 * Format a shortcut for display
 */
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = [];

  if (shortcut.meta) parts.push(getModifierKey());
  if (shortcut.shift) parts.push(getShiftKey());
  if (shortcut.alt) parts.push(getAltKey());

  // Format the key
  const keyDisplay = shortcut.key.length === 1
    ? shortcut.key.toUpperCase()
    : shortcut.key === 'Escape'
      ? 'Esc'
      : shortcut.key;

  parts.push(keyDisplay);

  return detectPlatform() === 'mac'
    ? parts.join('')
    : parts.join('+');
}

/**
 * Check if an event matches a shortcut
 */
export function matchesShortcut(event: KeyboardEvent, shortcut: KeyboardShortcut): boolean {
  const key = event.key.toLowerCase();
  const shortcutKey = shortcut.key.toLowerCase();

  // Check key match
  if (key !== shortcutKey) return false;

  // Check modifiers
  const metaOrCtrl = event.metaKey || event.ctrlKey;
  if (shortcut.meta && !metaOrCtrl) return false;
  if (!shortcut.meta && metaOrCtrl) return false;

  if (shortcut.shift && !event.shiftKey) return false;
  if (!shortcut.shift && event.shiftKey) return false;

  if (shortcut.alt && !event.altKey) return false;
  if (!shortcut.alt && event.altKey) return false;

  return true;
}

/**
 * Get shortcuts grouped by category
 */
export function getShortcutsByCategory(): Record<ShortcutCategory, KeyboardShortcut[]> {
  const grouped: Record<ShortcutCategory, KeyboardShortcut[]> = {
    navigation: [],
    actions: [],
    editing: [],
    views: [],
  };

  KEYBOARD_SHORTCUTS.forEach((shortcut) => {
    grouped[shortcut.category].push(shortcut);
  });

  return grouped;
}

/**
 * Category labels for display
 */
export const CATEGORY_LABELS: Record<ShortcutCategory, string> = {
  navigation: 'Navigation',
  actions: 'Actions',
  editing: 'Editing',
  views: 'Views',
};
