'use client';

/**
 * JurisdictionSelector - Sovereign Edition
 *
 * CompuLaw-Grade Authority Selector with cascading dropdowns.
 * Implements the "Sovereign Selector" pattern:
 * - Level 1: System (Federal vs State)
 * - Level 2: Jurisdiction (11th Circuit / Florida)
 * - Level 3: Court (M.D. Florida / 13th Circuit)
 * - Level 4: Judge (Optional)
 *
 * AI Detection:
 * - Auto-fills dropdowns based on document analysis
 * - Highlights AI suggestions in GOLD
 * - Requires user confirmation ("Confirm Authority")
 */

import { useState, useEffect, useCallback } from 'react';
import { Scale, ChevronDown, Sparkles, Check, AlertTriangle, RefreshCw } from 'lucide-react';
import apiClient from '@/lib/api-client';

// Types
interface HierarchyNode {
  id: string;
  code: string;
  name: string;
  level: number;
  level_name: string;
  parent_id: string | null;
  children: HierarchyNode[];
  metadata?: Record<string, unknown>;
  rule_set_codes: string[];
}

interface JurisdictionHierarchy {
  systems: HierarchyNode[];
  last_updated: string;
}

interface AIDetection {
  system?: string;
  jurisdiction_id?: string;
  court_id?: string;
  judge?: string;
  confidence: number;
  source: string; // "case_number" | "document_text" | "court_name"
  matched_patterns: string[];
}

interface JurisdictionSelection {
  system: string | null;
  jurisdiction_id: string | null;
  court_id: string | null;
  judge: string | null;
  confirmed: boolean;
}

interface JurisdictionSelectorProps {
  caseId: string;
  initialSelection?: Partial<JurisdictionSelection>;
  aiDetection?: AIDetection | null;
  onSelectionChange?: (selection: JurisdictionSelection) => void;
  onConfirm?: (selection: JurisdictionSelection) => void;
  disabled?: boolean;
  compact?: boolean;
}

export default function JurisdictionSelector({
  caseId,
  initialSelection,
  aiDetection,
  onSelectionChange,
  onConfirm,
  disabled = false,
  compact = false,
}: JurisdictionSelectorProps) {
  const [hierarchy, setHierarchy] = useState<JurisdictionHierarchy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Selection state
  const [selection, setSelection] = useState<JurisdictionSelection>({
    system: initialSelection?.system || null,
    jurisdiction_id: initialSelection?.jurisdiction_id || null,
    court_id: initialSelection?.court_id || null,
    judge: initialSelection?.judge || null,
    confirmed: initialSelection?.confirmed || false,
  });

  // Track which fields were AI-suggested
  const [aiSuggested, setAiSuggested] = useState<Set<string>>(new Set());

  // Fetch hierarchy on mount
  useEffect(() => {
    const fetchHierarchy = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get('/api/v1/jurisdictions/hierarchy');
        setHierarchy(response.data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch jurisdiction hierarchy:', err);
        setError('Failed to load jurisdictions');
      } finally {
        setLoading(false);
      }
    };

    fetchHierarchy();
  }, []);

  // Apply AI detection as suggestions (highlighted, not confirmed)
  useEffect(() => {
    if (aiDetection && hierarchy && !selection.confirmed) {
      const suggested = new Set<string>();
      const newSelection = { ...selection };

      if (aiDetection.system) {
        newSelection.system = aiDetection.system;
        suggested.add('system');
      }

      if (aiDetection.jurisdiction_id) {
        newSelection.jurisdiction_id = aiDetection.jurisdiction_id;
        suggested.add('jurisdiction');
      }

      if (aiDetection.court_id) {
        newSelection.court_id = aiDetection.court_id;
        suggested.add('court');
      }

      if (aiDetection.judge) {
        newSelection.judge = aiDetection.judge;
        suggested.add('judge');
      }

      setAiSuggested(suggested);
      setSelection(newSelection);
      onSelectionChange?.(newSelection);
    }
  }, [aiDetection, hierarchy]);

  // Get available options for each level
  const getSystemOptions = useCallback(() => {
    if (!hierarchy) return [];
    return hierarchy.systems;
  }, [hierarchy]);

  const getJurisdictionOptions = useCallback(() => {
    if (!hierarchy || !selection.system) return [];
    const system = hierarchy.systems.find(s => s.code === selection.system);
    return system?.children || [];
  }, [hierarchy, selection.system]);

  const getCourtOptions = useCallback(() => {
    if (!hierarchy || !selection.jurisdiction_id) return [];
    const jurisdictionOptions = getJurisdictionOptions();
    const jurisdiction = jurisdictionOptions.find(j => j.id === selection.jurisdiction_id);
    return jurisdiction?.children || [];
  }, [hierarchy, selection.jurisdiction_id, getJurisdictionOptions]);

  // Handle selection changes
  const handleSystemChange = (value: string) => {
    const newSelection = {
      system: value || null,
      jurisdiction_id: null,
      court_id: null,
      judge: null,
      confirmed: false,
    };
    setSelection(newSelection);
    setAiSuggested(prev => {
      const next = new Set(prev);
      next.delete('system');
      next.delete('jurisdiction');
      next.delete('court');
      next.delete('judge');
      return next;
    });
    onSelectionChange?.(newSelection);
  };

  const handleJurisdictionChange = (value: string) => {
    const newSelection = {
      ...selection,
      jurisdiction_id: value || null,
      court_id: null,
      judge: null,
      confirmed: false,
    };
    setSelection(newSelection);
    setAiSuggested(prev => {
      const next = new Set(prev);
      next.delete('jurisdiction');
      next.delete('court');
      next.delete('judge');
      return next;
    });
    onSelectionChange?.(newSelection);
  };

  const handleCourtChange = (value: string) => {
    const newSelection = {
      ...selection,
      court_id: value || null,
      judge: null,
      confirmed: false,
    };
    setSelection(newSelection);
    setAiSuggested(prev => {
      const next = new Set(prev);
      next.delete('court');
      next.delete('judge');
      return next;
    });
    onSelectionChange?.(newSelection);
  };

  const handleJudgeChange = (value: string) => {
    const newSelection = {
      ...selection,
      judge: value || null,
      confirmed: false,
    };
    setSelection(newSelection);
    setAiSuggested(prev => {
      const next = new Set(prev);
      next.delete('judge');
      return next;
    });
    onSelectionChange?.(newSelection);
  };

  // Confirm the selection (lock it in)
  const handleConfirm = async () => {
    if (!selection.system) return;

    setSaving(true);
    try {
      // Call the Retroactive Ripple endpoint
      await apiClient.patch(`/api/v1/jurisdictions/cases/${caseId}/jurisdiction`, {
        jurisdiction_id: selection.jurisdiction_id,
        court_location_id: selection.court_id,
        judge: selection.judge,
        recalculate_deadlines: true,
      });

      const confirmedSelection = { ...selection, confirmed: true };
      setSelection(confirmedSelection);
      setAiSuggested(new Set());
      onConfirm?.(confirmedSelection);
    } catch (err) {
      console.error('Failed to update jurisdiction:', err);
      setError('Failed to save jurisdiction');
    } finally {
      setSaving(false);
    }
  };

  // Dropdown component with AI suggestion styling
  const SelectField = ({
    label,
    value,
    options,
    onChange,
    placeholder,
    isAiSuggested,
    disabled: fieldDisabled,
  }: {
    label: string;
    value: string | null;
    options: HierarchyNode[];
    onChange: (value: string) => void;
    placeholder: string;
    isAiSuggested: boolean;
    disabled?: boolean;
  }) => (
    <div className="flex-1 min-w-0">
      <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
        {label}
      </label>
      <div className="relative">
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={fieldDisabled || disabled || options.length === 0}
          className={`
            w-full appearance-none px-3 py-2 pr-8
            border text-sm font-mono
            focus:outline-none focus:ring-2 focus:ring-blue-500
            disabled:opacity-50 disabled:cursor-not-allowed
            ${isAiSuggested && !selection.confirmed
              ? 'border-amber-400 bg-amber-50 ring-2 ring-amber-200'
              : 'border-slate-300 bg-white'
            }
          `}
        >
          <option value="">{placeholder}</option>
          {options.map((opt) => (
            <option key={opt.id} value={opt.id === opt.code ? opt.code : opt.id}>
              {opt.code} - {opt.name}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        {isAiSuggested && !selection.confirmed && (
          <Sparkles className="absolute right-8 top-1/2 -translate-y-1/2 w-4 h-4 text-amber-500" />
        )}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="border border-slate-300 bg-slate-50 p-4">
        <div className="flex items-center gap-2 text-slate-500">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading jurisdictions...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-red-300 bg-red-50 p-4">
        <div className="flex items-center gap-2 text-red-700">
          <AlertTriangle className="w-4 h-4" />
          <span className="text-sm">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-slate-300 bg-white">
      {/* Header */}
      <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-slate-600" />
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Authority Selection
          </span>
          {selection.confirmed && (
            <span className="bg-green-100 text-green-700 text-[10px] font-bold px-1.5 py-0.5 border border-green-200 uppercase">
              Confirmed
            </span>
          )}
        </div>
        {aiSuggested.size > 0 && !selection.confirmed && (
          <div className="flex items-center gap-1 text-amber-600 text-xs">
            <Sparkles className="w-3 h-3" />
            <span className="font-medium">AI Detected</span>
            {aiDetection?.source && (
              <span className="text-amber-500">
                ({aiDetection.source.replace('_', ' ')})
              </span>
            )}
          </div>
        )}
      </div>

      {/* Cascading Dropdowns */}
      <div className={`p-4 ${compact ? 'space-y-3' : 'space-y-4'}`}>
        <div className={`flex ${compact ? 'flex-col space-y-3' : 'flex-row gap-4'}`}>
          {/* System */}
          <SelectField
            label="System"
            value={selection.system}
            options={getSystemOptions()}
            onChange={handleSystemChange}
            placeholder="Select system..."
            isAiSuggested={aiSuggested.has('system')}
          />

          {/* Jurisdiction */}
          <SelectField
            label="Jurisdiction"
            value={selection.jurisdiction_id}
            options={getJurisdictionOptions()}
            onChange={handleJurisdictionChange}
            placeholder={selection.system ? 'Select jurisdiction...' : 'Select system first'}
            isAiSuggested={aiSuggested.has('jurisdiction')}
            disabled={!selection.system}
          />
        </div>

        <div className={`flex ${compact ? 'flex-col space-y-3' : 'flex-row gap-4'}`}>
          {/* Court */}
          <SelectField
            label="Court / Venue"
            value={selection.court_id}
            options={getCourtOptions()}
            onChange={handleCourtChange}
            placeholder={selection.jurisdiction_id ? 'Select court...' : 'Select jurisdiction first'}
            isAiSuggested={aiSuggested.has('court')}
            disabled={!selection.jurisdiction_id}
          />

          {/* Judge */}
          <div className="flex-1 min-w-0">
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
              Judge (Optional)
            </label>
            <input
              type="text"
              value={selection.judge || ''}
              onChange={(e) => handleJudgeChange(e.target.value)}
              placeholder="Enter judge name..."
              disabled={disabled}
              className={`
                w-full px-3 py-2 border text-sm
                focus:outline-none focus:ring-2 focus:ring-blue-500
                disabled:opacity-50 disabled:cursor-not-allowed
                ${aiSuggested.has('judge') && !selection.confirmed
                  ? 'border-amber-400 bg-amber-50 ring-2 ring-amber-200'
                  : 'border-slate-300 bg-white'
                }
              `}
            />
          </div>
        </div>

        {/* AI Suggestion Banner */}
        {aiSuggested.size > 0 && !selection.confirmed && (
          <div className="bg-amber-50 border border-amber-200 p-3">
            <div className="flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-amber-800">
                  AI Detected: {aiDetection?.matched_patterns?.[0] || 'Document analysis'}
                </p>
                <p className="text-xs text-amber-600 mt-1">
                  Review the highlighted fields and click "Confirm Authority" to lock in your selection.
                  This will recalculate all deadlines using the selected jurisdiction's rules.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Confirm Button */}
        {!selection.confirmed && selection.system && (
          <div className="flex justify-end pt-2 border-t border-slate-200">
            <button
              onClick={handleConfirm}
              disabled={saving || disabled}
              className={`
                flex items-center gap-2 px-4 py-2 text-sm font-medium
                transition-colors
                ${saving
                  ? 'bg-slate-300 text-slate-500 cursor-wait'
                  : 'bg-slate-900 text-white hover:bg-slate-800'
                }
              `}
            >
              {saving ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  CONFIRM AUTHORITY
                </>
              )}
            </button>
          </div>
        )}

        {/* Confirmed State */}
        {selection.confirmed && (
          <div className="bg-green-50 border border-green-200 p-3">
            <div className="flex items-center gap-2 text-green-700">
              <Check className="w-4 h-4" />
              <span className="text-sm font-medium">
                Authority confirmed. Deadlines calculated using {selection.system} rules.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
