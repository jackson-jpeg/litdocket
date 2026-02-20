'use client';

import { X, Command, Keyboard, Navigation, Pencil, Layout } from 'lucide-react';
import {
  getShortcutsByCategory,
  formatShortcut,
  getModifierKey,
  CATEGORY_LABELS,
  type ShortcutCategory,
} from '@/lib/keyboard';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const CATEGORY_ICONS: Record<ShortcutCategory, React.ReactNode> = {
  navigation: <Navigation className="w-4 h-4" />,
  actions: <Command className="w-4 h-4" />,
  editing: <Pencil className="w-4 h-4" />,
  views: <Layout className="w-4 h-4" />,
};

export default function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  const shortcutsByCategory = getShortcutsByCategory();
  const modifierKey = getModifierKey();

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-shortcuts-modal-title"
        className="bg-paper border-2 border-ink shadow-modal max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-ink flex items-center justify-between bg-surface">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-steel border border-ink">
              <Keyboard className="w-5 h-5 text-white" />
            </div>
            <h2 id="keyboard-shortcuts-modal-title" className="text-xl font-heading font-semibold text-ink">Keyboard Shortcuts</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close keyboard shortcuts"
            className="p-2 hover:bg-surface transition-transform hover:translate-x-0.5"
          >
            <X className="w-5 h-5 text-ink-muted" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          <div className="space-y-6">
            {(Object.keys(shortcutsByCategory) as ShortcutCategory[]).map((category) => {
              const shortcuts = shortcutsByCategory[category];
              if (shortcuts.length === 0) return null;

              return (
                <div key={category}>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-ink-muted">{CATEGORY_ICONS[category]}</span>
                    <h3 className="text-sm font-mono font-semibold text-ink uppercase tracking-wider">
                      {CATEGORY_LABELS[category]}
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {shortcuts.map((shortcut) => (
                      <div
                        key={shortcut.id}
                        className="flex items-center justify-between p-3 bg-surface border border-ink/20 hover:translate-x-0.5 transition-transform"
                      >
                        <div>
                          <span className="text-sm font-medium text-ink">{shortcut.label}</span>
                          <p className="text-xs text-ink-secondary">{shortcut.description}</p>
                        </div>
                        <kbd className="px-3 py-1.5 text-sm font-mono font-semibold text-ink bg-paper border border-ink">
                          {formatShortcut(shortcut)}
                        </kbd>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Tips */}
          <div className="mt-6 p-4 bg-steel/10 border border-steel/30">
            <h3 className="text-sm font-mono font-semibold text-ink uppercase tracking-wide mb-2">Pro Tips</h3>
            <ul className="text-sm text-ink-secondary space-y-1">
              <li>• Press <kbd className="px-1.5 py-0.5 text-xs font-mono bg-paper border border-ink">{modifierKey}/</kbd> anytime to show this help</li>
              <li>• Use <kbd className="px-1.5 py-0.5 text-xs font-mono bg-paper border border-ink">{modifierKey}K</kbd> for quick global search</li>
              <li>• Press <kbd className="px-1.5 py-0.5 text-xs font-mono bg-paper border border-ink">Esc</kbd> to close any modal</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-ink bg-surface">
          <p className="text-xs text-ink-secondary text-center font-mono">
            Press <kbd className="px-1.5 py-0.5 text-xs font-mono bg-paper border border-ink">Esc</kbd> or click outside to close
          </p>
        </div>
      </div>
    </div>
  );
}
