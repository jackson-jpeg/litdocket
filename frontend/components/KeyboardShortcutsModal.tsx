'use client';

import { X, Command } from 'lucide-react';
import { useKeyboardShortcutsHelp } from '@/hooks/useKeyboardShortcuts';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  const shortcuts = useKeyboardShortcutsHelp();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-modal max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Command className="w-5 h-5 text-white" />
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
          <div className="space-y-3">
            {shortcuts.map((shortcut, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <span className="text-sm text-slate-700">{shortcut.description}</span>
                <div className="flex items-center gap-1">
                  {shortcut.keys.map((key, keyIndex) => (
                    <span key={keyIndex} className="flex items-center gap-1">
                      <kbd className="px-2 py-1 text-xs font-semibold text-slate-800 bg-white border border-slate-300 rounded shadow-sm">
                        {key}
                      </kbd>
                      {keyIndex < shortcut.keys.length - 1 && (
                        <span className="text-slate-400 text-xs">+</span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Tips */}
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">Pro Tips</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Press <kbd className="px-1 py-0.5 text-xs bg-white border border-blue-300 rounded">?</kbd> anytime to show this help</li>
              <li>• Use <kbd className="px-1 py-0.5 text-xs bg-white border border-blue-300 rounded">⌘</kbd> + <kbd className="px-1 py-0.5 text-xs bg-white border border-blue-300 rounded">K</kbd> for quick search</li>
              <li>• Press <kbd className="px-1 py-0.5 text-xs bg-white border border-blue-300 rounded">Esc</kbd> to close any modal</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50">
          <p className="text-xs text-slate-600 text-center">
            Press <kbd className="px-1 py-0.5 text-xs bg-white border border-slate-300 rounded">Esc</kbd> or click outside to close
          </p>
        </div>
      </div>
    </div>
  );
}
