import { useEffect, useCallback } from 'react';

interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  action: () => void;
  description: string;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[], enabled = true) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger shortcuts if user is typing in an input
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // Allow some shortcuts even in inputs (like Cmd+K for search)
        if (!event.metaKey && !event.ctrlKey) {
          return;
        }
      }

      for (const shortcut of shortcuts) {
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const altMatch = shortcut.alt ? event.altKey : !event.altKey;
        const metaMatch = shortcut.meta ? event.metaKey : !event.metaKey && !event.ctrlKey;

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          event.preventDefault();
          shortcut.action();
          break;
        }
      }
    },
    [shortcuts, enabled]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

// Common keyboard shortcuts for the app
export const commonShortcuts = {
  search: { key: 'k', ctrl: true, description: 'Open search' },
  newCase: { key: 'n', ctrl: true, description: 'Create new case' },
  newDeadline: { key: 'd', ctrl: true, description: 'Create new deadline' },
  save: { key: 's', ctrl: true, description: 'Save current form' },
  undo: { key: 'z', ctrl: true, description: 'Undo last action' },
  redo: { key: 'z', ctrl: true, shift: true, description: 'Redo last action' },
  help: { key: '?', description: 'Show keyboard shortcuts' },
  escape: { key: 'Escape', description: 'Close modal/cancel action' },
};

// Hook to show keyboard shortcuts help
export function useKeyboardShortcutsHelp() {
  const shortcuts = [
    { keys: ['⌘', 'K'], description: 'Open search' },
    { keys: ['⌘', 'N'], description: 'Create new case' },
    { keys: ['⌘', 'D'], description: 'Create new deadline' },
    { keys: ['⌘', 'S'], description: 'Save current form' },
    { keys: ['Esc'], description: 'Close modal' },
    { keys: ['?'], description: 'Show this help' },
    { keys: ['↑', '↓'], description: 'Navigate list' },
    { keys: ['Enter'], description: 'Select item' },
  ];

  return shortcuts;
}
