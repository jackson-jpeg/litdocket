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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-modal max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Keyboard className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900">Keyboard Shortcuts</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
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
                    <span className="text-slate-400">{CATEGORY_ICONS[category]}</span>
                    <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
                      {CATEGORY_LABELS[category]}
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {shortcuts.map((shortcut) => (
                      <div
                        key={shortcut.id}
                        className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                      >
                        <div>
                          <span className="text-sm font-medium text-slate-800">{shortcut.label}</span>
                          <p className="text-xs text-slate-500">{shortcut.description}</p>
                        </div>
                        <kbd className="px-3 py-1.5 text-sm font-mono font-semibold text-slate-700 bg-white border border-slate-300 rounded-md shadow-sm">
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
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">Pro Tips</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Press <kbd className="px-1.5 py-0.5 text-xs font-mono bg-white border border-blue-300 rounded">{modifierKey}/</kbd> anytime to show this help</li>
              <li>• Use <kbd className="px-1.5 py-0.5 text-xs font-mono bg-white border border-blue-300 rounded">{modifierKey}K</kbd> for quick global search</li>
              <li>• Press <kbd className="px-1.5 py-0.5 text-xs font-mono bg-white border border-blue-300 rounded">Esc</kbd> to close any modal</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50">
          <p className="text-xs text-slate-600 text-center">
            Press <kbd className="px-1.5 py-0.5 text-xs font-mono bg-white border border-slate-300 rounded">Esc</kbd> or click outside to close
          </p>
        </div>
      </div>
    </div>
  );
}
