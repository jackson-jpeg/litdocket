'use client';

/**
 * KeyboardShortcutsProvider - Global keyboard shortcut management
 *
 * Registers all application-wide keyboard shortcuts with collision detection.
 * Shortcuts are disabled when focus is in input/textarea elements.
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { eventBus } from '@/lib/eventBus';

interface Shortcut {
  key: string;
  modifiers: ('meta' | 'ctrl' | 'alt' | 'shift')[];
  description: string;
  action: () => void;
  category: 'navigation' | 'tools' | 'actions' | 'system';
}

interface KeyboardShortcutsContextValue {
  shortcuts: Shortcut[];
  showShortcutsModal: boolean;
  setShowShortcutsModal: (show: boolean) => void;
  registerShortcut: (shortcut: Shortcut) => () => void;
}

const KeyboardShortcutsContext = createContext<KeyboardShortcutsContextValue | null>(null);

export function useKeyboardShortcuts() {
  const context = useContext(KeyboardShortcutsContext);
  if (!context) {
    throw new Error('useKeyboardShortcuts must be used within KeyboardShortcutsProvider');
  }
  return context;
}

interface KeyboardShortcutsProviderProps {
  children: ReactNode;
}

export function KeyboardShortcutsProvider({ children }: KeyboardShortcutsProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [shortcuts, setShortcuts] = useState<Shortcut[]>([]);
  const [showShortcutsModal, setShowShortcutsModal] = useState(false);

  // Register a shortcut and return an unregister function
  const registerShortcut = useCallback((shortcut: Shortcut) => {
    setShortcuts(prev => {
      // Check for collision
      const existing = prev.find(s =>
        s.key === shortcut.key &&
        s.modifiers.length === shortcut.modifiers.length &&
        s.modifiers.every(m => shortcut.modifiers.includes(m))
      );
      if (existing) {
        console.warn(`Shortcut collision: ${shortcut.modifiers.join('+')}+${shortcut.key} already registered for "${existing.description}"`);
        return prev;
      }
      return [...prev, shortcut];
    });

    return () => {
      setShortcuts(prev => prev.filter(s => s !== shortcut));
    };
  }, []);

  // Register default shortcuts
  useEffect(() => {
    const defaultShortcuts: Shortcut[] = [
      // Navigation shortcuts
      {
        key: 'd',
        modifiers: ['meta'],
        description: 'Go to Dashboard',
        category: 'navigation',
        action: () => router.push('/dashboard'),
      },
      {
        key: '1',
        modifiers: ['meta'],
        description: 'Go to Cases',
        category: 'navigation',
        action: () => router.push('/cases'),
      },
      {
        key: '2',
        modifiers: ['meta'],
        description: 'Go to Docket/Calendar',
        category: 'navigation',
        action: () => router.push('/calendar'),
      },
      {
        key: 'n',
        modifiers: ['meta'],
        description: 'Create New Case',
        category: 'actions',
        action: () => router.push('/cases?action=new'),
      },
      // Tool shortcuts (Alt key)
      {
        key: 'c',
        modifiers: ['alt'],
        description: 'Deadline Calculator',
        category: 'tools',
        action: () => router.push('/tools/deadline-calculator'),
      },
      {
        key: 'j',
        modifiers: ['alt'],
        description: 'Jurisdiction Navigator',
        category: 'tools',
        action: () => router.push('/tools/jurisdiction-selector'),
      },
      {
        key: 'd',
        modifiers: ['alt'],
        description: 'Document Analyzer',
        category: 'tools',
        action: () => router.push('/tools/document-analyzer'),
      },
      {
        key: 'a',
        modifiers: ['alt'],
        description: 'Authority Core',
        category: 'tools',
        action: () => router.push('/tools/authority-core'),
      },
      // System shortcuts
      {
        key: '/',
        modifiers: ['meta'],
        description: 'Show All Shortcuts',
        category: 'system',
        action: () => setShowShortcutsModal(true),
      },
    ];

    // Note: ⌘K is handled by AITerminal component directly
    // to avoid conflicts with its modal state

    const unregisterFns = defaultShortcuts.map(s => registerShortcut(s));

    return () => {
      unregisterFns.forEach(fn => fn());
    };
  }, [router, registerShortcut]);

  // Global keyboard event handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip if focus is in input, textarea, or contenteditable
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // Allow Escape to blur
        if (e.key === 'Escape') {
          target.blur();
        }
        return;
      }

      // Find matching shortcut
      const matchingShortcut = shortcuts.find(s => {
        const keyMatch = s.key.toLowerCase() === e.key.toLowerCase();
        const metaMatch = s.modifiers.includes('meta') === (e.metaKey || e.ctrlKey);
        const altMatch = s.modifiers.includes('alt') === e.altKey;
        const shiftMatch = s.modifiers.includes('shift') === e.shiftKey;
        const ctrlMatch = !s.modifiers.includes('ctrl') || e.ctrlKey;

        // For meta shortcuts, don't trigger if alt is pressed (and vice versa)
        if (s.modifiers.includes('meta') && !s.modifiers.includes('alt') && e.altKey) {
          return false;
        }
        if (s.modifiers.includes('alt') && !s.modifiers.includes('meta') && (e.metaKey || e.ctrlKey)) {
          return false;
        }

        return keyMatch && metaMatch && altMatch && shiftMatch && ctrlMatch;
      });

      if (matchingShortcut) {
        e.preventDefault();
        e.stopPropagation();
        matchingShortcut.action();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);

  // Close modal on Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showShortcutsModal) {
        setShowShortcutsModal(false);
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [showShortcutsModal]);

  return (
    <KeyboardShortcutsContext.Provider
      value={{
        shortcuts,
        showShortcutsModal,
        setShowShortcutsModal,
        registerShortcut,
      }}
    >
      {children}

      {/* Shortcuts Help Modal */}
      {showShortcutsModal && (
        <div
          className="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4"
          onClick={() => setShowShortcutsModal(false)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Keyboard Shortcuts</h2>
              <button
                onClick={() => setShowShortcutsModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" />
                </svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
              {/* Navigation */}
              <div className="mb-6">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Navigation</h3>
                <div className="space-y-2">
                  <ShortcutRow keys={['⌘', 'K']} description="Open AI Terminal" />
                  <ShortcutRow keys={['⌘', 'D']} description="Go to Dashboard" />
                  <ShortcutRow keys={['⌘', '1']} description="Go to Cases" />
                  <ShortcutRow keys={['⌘', '2']} description="Go to Docket/Calendar" />
                  <ShortcutRow keys={['⌘', 'N']} description="Create New Case" />
                </div>
              </div>

              {/* Tools */}
              <div className="mb-6">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Tools</h3>
                <div className="space-y-2">
                  <ShortcutRow keys={['Alt', 'C']} description="Deadline Calculator" />
                  <ShortcutRow keys={['Alt', 'J']} description="Jurisdiction Navigator" />
                  <ShortcutRow keys={['Alt', 'D']} description="Document Analyzer" />
                  <ShortcutRow keys={['Alt', 'A']} description="Authority Core" />
                </div>
              </div>

              {/* System */}
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">System</h3>
                <div className="space-y-2">
                  <ShortcutRow keys={['⌘', '/']} description="Show this help" />
                  <ShortcutRow keys={['Esc']} description="Close modal / Cancel" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </KeyboardShortcutsContext.Provider>
  );
}

function ShortcutRow({ keys, description }: { keys: string[]; description: string }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-slate-700">{description}</span>
      <div className="flex items-center gap-1">
        {keys.map((key, idx) => (
          <React.Fragment key={idx}>
            <kbd className="px-2 py-1 bg-slate-100 border border-slate-300 rounded text-xs font-mono text-slate-700 min-w-[24px] text-center">
              {key}
            </kbd>
            {idx < keys.length - 1 && <span className="text-slate-400 text-xs">+</span>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

export default KeyboardShortcutsProvider;
