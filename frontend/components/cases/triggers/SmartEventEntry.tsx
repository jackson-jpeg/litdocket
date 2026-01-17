'use client';

/**
 * SmartEventEntry - cmdk-Style Command Bar for Trigger Events
 *
 * A Raycast/Spotlight-inspired command palette for entering legal events.
 * Key UX patterns:
 *   1. ⌘K style modal with instant search
 *   2. Keyboard-first navigation (↑↓ to select, Enter to confirm)
 *   3. Date picker auto-focuses on event selection
 *   4. Live deadline count preview
 *
 * Performance: Fetches from /api/v1/triggers/types (no DB queries, <10ms response)
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  X,
  Search,
  Calendar,
  Zap,
  ChevronRight,
  Loader2,
  Gavel,
  FileText,
  Scale,
  Clock,
  Users,
  ArrowUpCircle,
  Handshake,
  CheckCircle,
  FolderPlus,
  FileEdit,
  CalendarClock,
  FileSignature,
  Stamp,
  PlusCircle,
  Command,
  CornerDownLeft,
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';

// ============================================================================
// TYPES
// ============================================================================

interface TriggerType {
  id: string;
  trigger_type: string;
  name: string;
  friendly_name: string;
  description: string;
  category: string;
  icon: string;
  example: string;
  generates_approx: number;
}

interface SmartEventEntryProps {
  isOpen: boolean;
  caseId: string;
  jurisdiction: string;
  courtType: string;
  onClose: () => void;
  onSuccess: () => void;
}

// ============================================================================
// ICON MAPPING
// ============================================================================

const ICON_MAP: Record<string, React.ReactNode> = {
  'gavel': <Gavel className="w-4 h-4" />,
  'file-text': <FileText className="w-4 h-4" />,
  'check-circle': <CheckCircle className="w-4 h-4" />,
  'folder-plus': <FolderPlus className="w-4 h-4" />,
  'file-edit': <FileEdit className="w-4 h-4" />,
  'search': <Search className="w-4 h-4" />,
  'calendar-clock': <CalendarClock className="w-4 h-4" />,
  'scale': <Scale className="w-4 h-4" />,
  'file-signature': <FileSignature className="w-4 h-4" />,
  'calendar': <Calendar className="w-4 h-4" />,
  'users': <Users className="w-4 h-4" />,
  'stamp': <Stamp className="w-4 h-4" />,
  'arrow-up-circle': <ArrowUpCircle className="w-4 h-4" />,
  'handshake': <Handshake className="w-4 h-4" />,
  'plus-circle': <PlusCircle className="w-4 h-4" />,
  'clock': <Clock className="w-4 h-4" />,
};

const CATEGORY_COLORS: Record<string, string> = {
  trial: 'bg-red-100 text-red-700',
  pleading: 'bg-blue-100 text-blue-700',
  discovery: 'bg-amber-100 text-amber-700',
  motion: 'bg-purple-100 text-purple-700',
  appellate: 'bg-green-100 text-green-700',
  other: 'bg-slate-100 text-slate-700',
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function SmartEventEntry({
  isOpen,
  caseId,
  jurisdiction,
  courtType,
  onClose,
  onSuccess,
}: SmartEventEntryProps) {
  const { showSuccess, showError } = useToast();

  // Refs
  const inputRef = useRef<HTMLInputElement>(null);
  const dateInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // State
  const [query, setQuery] = useState('');
  const [triggerTypes, setTriggerTypes] = useState<TriggerType[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [selectedType, setSelectedType] = useState<TriggerType | null>(null);
  const [triggerDate, setTriggerDate] = useState('');
  const [creating, setCreating] = useState(false);
  const [step, setStep] = useState<'search' | 'date'>('search');

  // ============================================================================
  // DATA FETCHING
  // ============================================================================

  // Fetch trigger types from API
  useEffect(() => {
    if (!isOpen) return;

    const fetchTypes = async () => {
      setLoading(true);
      try {
        const response = await apiClient.get('/api/v1/triggers/types', {
          params: query ? { q: query } : undefined,
        });
        setTriggerTypes(response.data.types || []);
        setSelectedIndex(0);
      } catch (err) {
        console.error('Failed to fetch trigger types:', err);
        // Fallback to empty (API might not be deployed yet)
        setTriggerTypes([]);
      } finally {
        setLoading(false);
      }
    };

    const debounce = setTimeout(fetchTypes, query ? 100 : 0);
    return () => clearTimeout(debounce);
  }, [isOpen, query]);

  // ============================================================================
  // FILTERING (client-side for instant response)
  // ============================================================================

  const filteredTypes = useMemo(() => {
    if (!query.trim()) return triggerTypes;

    const q = query.toLowerCase();
    return triggerTypes.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.friendly_name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.category.toLowerCase().includes(q)
    );
  }, [triggerTypes, query]);

  // Group by category for visual hierarchy
  const groupedTypes = useMemo(() => {
    const groups: Record<string, TriggerType[]> = {};
    filteredTypes.forEach((t) => {
      if (!groups[t.category]) groups[t.category] = [];
      groups[t.category].push(t);
    });
    return groups;
  }, [filteredTypes]);

  // Flat list for keyboard navigation
  const flatList = useMemo(() => {
    return Object.values(groupedTypes).flat();
  }, [groupedTypes]);

  // ============================================================================
  // KEYBOARD NAVIGATION
  // ============================================================================

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (step === 'date') {
        // In date step, Escape goes back to search
        if (e.key === 'Escape') {
          e.preventDefault();
          setStep('search');
          setSelectedType(null);
          setTriggerDate('');
          setTimeout(() => inputRef.current?.focus(), 0);
          return;
        }
        // Enter on date step triggers creation
        if (e.key === 'Enter' && triggerDate) {
          e.preventDefault();
          handleCreate();
          return;
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => Math.min(prev + 1, flatList.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (flatList[selectedIndex]) {
            handleSelectType(flatList[selectedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
        case 'Tab':
          e.preventDefault();
          // Tab cycles through results
          if (e.shiftKey) {
            setSelectedIndex((prev) => Math.max(prev - 1, 0));
          } else {
            setSelectedIndex((prev) => Math.min(prev + 1, flatList.length - 1));
          }
          break;
      }
    },
    [step, flatList, selectedIndex, triggerDate, onClose]
  );

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current && flatList.length > 0) {
      const selectedEl = listRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      selectedEl?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex, flatList.length]);

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  const handleSelectType = (type: TriggerType) => {
    setSelectedType(type);
    setStep('date');
    // Auto-focus date input after a tick
    setTimeout(() => {
      dateInputRef.current?.focus();
      dateInputRef.current?.showPicker?.();
    }, 50);
  };

  const handleCreate = async () => {
    if (!selectedType || !triggerDate) return;

    setCreating(true);
    try {
      const response = await apiClient.post('/api/v1/triggers/create', {
        case_id: caseId,
        trigger_type: selectedType.trigger_type,
        trigger_date: triggerDate,
        jurisdiction: jurisdiction || 'florida_state',
        court_type: courtType || 'civil',
        service_method: 'email',
      });

      const count = response.data.dependent_deadlines_created || 0;
      showSuccess(`Created "${selectedType.name}" with ${count} deadlines`);
      onSuccess();
      handleClose();
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            'Failed to create event';
      showError(errorMessage);
    } finally {
      setCreating(false);
    }
  };

  const handleClose = () => {
    setQuery('');
    setSelectedType(null);
    setTriggerDate('');
    setSelectedIndex(0);
    setStep('search');
    onClose();
  };

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Focus input on open
  useEffect(() => {
    if (isOpen && step === 'search') {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen, step]);

  // Reset on close
  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setSelectedType(null);
      setTriggerDate('');
      setSelectedIndex(0);
      setStep('search');
    }
  }, [isOpen]);

  // ============================================================================
  // RENDER
  // ============================================================================

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-xl bg-white rounded-xl shadow-2xl overflow-hidden border border-slate-200"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Header / Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 bg-slate-50">
          {step === 'search' ? (
            <>
              <Search className="w-5 h-5 text-slate-400 flex-shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type an event... (e.g., Jury Trial, Motion to Dismiss)"
                className="flex-1 bg-transparent outline-none text-slate-800 placeholder-slate-400 text-base"
                autoFocus
              />
              {loading && <Loader2 className="w-4 h-4 animate-spin text-slate-400" />}
            </>
          ) : (
            <>
              <button
                onClick={() => {
                  setStep('search');
                  setSelectedType(null);
                  setTriggerDate('');
                }}
                className="p-1 hover:bg-slate-200 rounded transition-colors"
              >
                <ChevronRight className="w-4 h-4 text-slate-400 rotate-180" />
              </button>
              <div className="flex items-center gap-2 flex-1">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${CATEGORY_COLORS[selectedType?.category || 'other']}`}>
                  {selectedType?.category}
                </span>
                <span className="font-medium text-slate-800">{selectedType?.name}</span>
              </div>
              <span className="text-xs text-slate-500">
                ~{selectedType?.generates_approx} deadlines
              </span>
            </>
          )}
        </div>

        {/* Content Area */}
        {step === 'search' ? (
          <div ref={listRef} className="max-h-[400px] overflow-y-auto">
            {flatList.length === 0 && !loading ? (
              <div className="p-8 text-center text-slate-500">
                <Search className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                <p>No events match "{query}"</p>
              </div>
            ) : (
              Object.entries(groupedTypes).map(([category, types]) => (
                <div key={category}>
                  {/* Category Header */}
                  <div className="px-4 py-2 bg-slate-50 border-y border-slate-100 sticky top-0">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      {category}
                    </span>
                  </div>
                  {/* Items */}
                  {types.map((type) => {
                    const globalIndex = flatList.indexOf(type);
                    const isSelected = globalIndex === selectedIndex;

                    return (
                      <button
                        key={type.id}
                        data-index={globalIndex}
                        onClick={() => handleSelectType(type)}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                        className={`w-full px-4 py-3 flex items-center gap-3 text-left transition-colors ${
                          isSelected
                            ? 'bg-purple-50 border-l-2 border-purple-500'
                            : 'hover:bg-slate-50 border-l-2 border-transparent'
                        }`}
                      >
                        {/* Icon */}
                        <div className={`p-2 rounded-lg ${isSelected ? 'bg-purple-100 text-purple-600' : 'bg-slate-100 text-slate-500'}`}>
                          {ICON_MAP[type.icon] || <Zap className="w-4 h-4" />}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`font-medium ${isSelected ? 'text-purple-900' : 'text-slate-800'}`}>
                              {type.friendly_name}
                            </span>
                          </div>
                          <p className="text-sm text-slate-500 truncate">
                            {type.description}
                          </p>
                        </div>

                        {/* Badge */}
                        <div className="flex-shrink-0 flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                            +{type.generates_approx}
                          </span>
                          {isSelected && (
                            <span className="text-xs text-slate-400 flex items-center gap-1">
                              <CornerDownLeft className="w-3 h-3" />
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              ))
            )}
          </div>
        ) : (
          /* Date Selection Step */
          <div className="p-6">
            <div className="mb-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-3 bg-purple-100 rounded-xl">
                  {ICON_MAP[selectedType?.icon || 'calendar'] || <Calendar className="w-6 h-6 text-purple-600" />}
                </div>
                <div>
                  <h3 className="font-semibold text-slate-800">{selectedType?.friendly_name}</h3>
                  <p className="text-sm text-slate-500">{selectedType?.example}</p>
                </div>
              </div>

              <div className="bg-slate-50 rounded-lg p-4 mb-4">
                <p className="text-sm text-slate-600">{selectedType?.description}</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  When did this event occur?
                </label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    ref={dateInputRef}
                    type="date"
                    value={triggerDate}
                    onChange={(e) => setTriggerDate(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-base"
                    autoFocus
                  />
                </div>
              </div>

              {triggerDate && (
                <div className="bg-purple-50 rounded-lg p-4 border border-purple-100">
                  <div className="flex items-center gap-2 text-purple-700">
                    <Zap className="w-4 h-4" />
                    <span className="font-medium">
                      Will generate ~{selectedType?.generates_approx} deadlines
                    </span>
                  </div>
                  <p className="text-sm text-purple-600 mt-1">
                    Including motions, discovery, and pretrial deadlines based on {jurisdiction || 'Florida'} rules.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-4 text-xs text-slate-500">
            {step === 'search' ? (
              <>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-slate-200 rounded text-[10px] font-mono">↑↓</kbd>
                  Navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-slate-200 rounded text-[10px] font-mono">↵</kbd>
                  Select
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-slate-200 rounded text-[10px] font-mono">esc</kbd>
                  Close
                </span>
              </>
            ) : (
              <>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-slate-200 rounded text-[10px] font-mono">esc</kbd>
                  Back
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-slate-200 rounded text-[10px] font-mono">↵</kbd>
                  Create
                </span>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleClose}
              disabled={creating}
              className="px-3 py-1.5 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors text-sm"
            >
              Cancel
            </button>
            {step === 'date' && (
              <button
                onClick={handleCreate}
                disabled={creating || !triggerDate}
                className="flex items-center gap-2 px-4 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
              >
                {creating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Create Deadlines
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
