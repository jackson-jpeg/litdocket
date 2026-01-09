'use client';

/**
 * SmartEventEntry - Unified Event Entry with Live Cascade Preview
 *
 * Replaces the basic "Add Trigger" modal with a CompuLaw-style interface:
 * 1. Smart search input with event type badges
 * 2. Live cascade preview showing all calculated deadlines
 * 3. Individual date overrides before saving
 * 4. Rules source selector
 *
 * "The Power User feel of legacy software with modern UI patterns"
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  X,
  Search,
  Calendar,
  Zap,
  ChevronRight,
  ChevronDown,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Scale,
  FileText,
  Gavel,
  Clock,
  Edit2,
  Info,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';

interface SmartEventEntryProps {
  isOpen: boolean;
  caseId: string;
  jurisdiction: string;
  courtType: string;
  onClose: () => void;
  onSuccess: () => void;
}

interface EventType {
  id: string;
  name: string;
  description: string;
  trigger_type: string;
  citation: string;
  deadline_count: number;
  category: 'trial' | 'pleading' | 'discovery' | 'motion' | 'other';
}

interface PreviewDeadline {
  id: string;
  title: string;
  calculated_date: string;
  override_date: string | null;
  priority: string;
  rule_citation: string;
  days_from_trigger: number;
  is_overridden: boolean;
  include: boolean;
}

interface RulesSource {
  id: string;
  name: string;
  description: string;
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  trial: <Gavel className="w-4 h-4" />,
  pleading: <FileText className="w-4 h-4" />,
  discovery: <Search className="w-4 h-4" />,
  motion: <Scale className="w-4 h-4" />,
  other: <Clock className="w-4 h-4" />,
};

const PRIORITY_COLORS: Record<string, string> = {
  fatal: 'bg-red-100 text-red-700 border-red-200',
  critical: 'bg-red-50 text-red-600 border-red-200',
  important: 'bg-amber-50 text-amber-700 border-amber-200',
  standard: 'bg-blue-50 text-blue-700 border-blue-200',
  informational: 'bg-slate-50 text-slate-600 border-slate-200',
};

const MOCK_EVENT_TYPES: EventType[] = [
  { id: 'trial_date', name: 'Trial Date', description: 'Set trial date and generate all pretrial deadlines', trigger_type: 'trial_date', citation: 'Fla. R. Civ. P. 1.440', deadline_count: 47, category: 'trial' },
  { id: 'complaint_served', name: 'Complaint Served', description: 'Service of process on defendant', trigger_type: 'complaint_served', citation: 'Fla. R. Civ. P. 1.140', deadline_count: 23, category: 'pleading' },
  { id: 'answer_filed', name: 'Answer Filed', description: 'Defendant files answer to complaint', trigger_type: 'answer_filed', citation: 'Fla. R. Civ. P. 1.140', deadline_count: 12, category: 'pleading' },
  { id: 'discovery_commenced', name: 'Discovery Commenced', description: 'Start of discovery period', trigger_type: 'discovery_commenced', citation: 'Fla. R. Civ. P. 1.280', deadline_count: 18, category: 'discovery' },
  { id: 'motion_filed', name: 'Motion Filed', description: 'Motion served on opposing party', trigger_type: 'motion_filed', citation: 'Fla. R. Civ. P. 1.160', deadline_count: 5, category: 'motion' },
  { id: 'order_entered', name: 'Order Entered', description: 'Court order issued', trigger_type: 'order_entered', citation: 'Fla. R. Jud. Admin. 2.514', deadline_count: 3, category: 'other' },
  { id: 'hearing_scheduled', name: 'Hearing Scheduled', description: 'Motion hearing set', trigger_type: 'hearing_scheduled', citation: 'Fla. R. Civ. P. 1.090', deadline_count: 4, category: 'motion' },
  { id: 'deposition_noticed', name: 'Deposition Noticed', description: 'Deposition notice served', trigger_type: 'deposition_noticed', citation: 'Fla. R. Civ. P. 1.310', deadline_count: 6, category: 'discovery' },
  { id: 'expert_disclosure', name: 'Expert Disclosure', description: 'Expert witness disclosure deadline', trigger_type: 'expert_disclosure', citation: 'Fla. R. Civ. P. 1.280(b)(5)', deadline_count: 8, category: 'discovery' },
  { id: 'mediation_scheduled', name: 'Mediation Scheduled', description: 'Mediation conference date', trigger_type: 'mediation_scheduled', citation: 'Fla. R. Civ. P. 1.720', deadline_count: 4, category: 'other' },
];

const RULES_SOURCES: RulesSource[] = [
  { id: 'florida_state', name: 'Florida State Rules', description: 'Fla. R. Civ. P., Fla. R. Jud. Admin.' },
  { id: 'federal', name: 'Federal Rules (FRCP)', description: 'Federal Rules of Civil Procedure' },
  { id: 'flsd_local', name: 'S.D. Fla. Local Rules', description: 'Southern District of Florida Local Rules' },
  { id: 'flmd_local', name: 'M.D. Fla. Local Rules', description: 'Middle District of Florida Local Rules' },
];

export default function SmartEventEntry({
  isOpen,
  caseId,
  jurisdiction,
  courtType,
  onClose,
  onSuccess,
}: SmartEventEntryProps) {
  const { showSuccess, showError } = useToast();

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<EventType | null>(null);
  const [triggerDate, setTriggerDate] = useState('');
  const [rulesSource, setRulesSource] = useState(jurisdiction || 'florida_state');
  const [serviceMethod, setServiceMethod] = useState<'email' | 'mail' | 'personal'>('email');
  const [previewDeadlines, setPreviewDeadlines] = useState<PreviewDeadline[]>([]);
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['trial', 'pleading']));

  // Filter event types based on search
  const filteredEvents = useMemo(() => {
    if (!searchQuery) return MOCK_EVENT_TYPES;
    const query = searchQuery.toLowerCase();
    return MOCK_EVENT_TYPES.filter(
      e => e.name.toLowerCase().includes(query) ||
           e.description.toLowerCase().includes(query) ||
           e.trigger_type.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  // Group events by category
  const groupedEvents = useMemo(() => {
    const groups: Record<string, EventType[]> = {};
    filteredEvents.forEach(event => {
      if (!groups[event.category]) groups[event.category] = [];
      groups[event.category].push(event);
    });
    return groups;
  }, [filteredEvents]);

  // Generate preview when event + date is set
  useEffect(() => {
    if (!selectedEvent || !triggerDate) {
      setPreviewDeadlines([]);
      return;
    }

    const generatePreview = async () => {
      setPreviewLoading(true);
      try {
        // Call backend to get preview
        const response = await apiClient.get('/api/v1/triggers/preview', {
          params: {
            trigger_type: selectedEvent.trigger_type,
            trigger_date: triggerDate,
            jurisdiction: rulesSource,
            court_type: courtType,
            service_method: serviceMethod,
          },
        });

        const deadlines = response.data.map((d: any, index: number) => ({
          id: `preview-${index}`,
          title: d.title,
          calculated_date: d.deadline_date,
          override_date: null,
          priority: d.priority,
          rule_citation: d.rule_citation,
          days_from_trigger: d.days_from_trigger,
          is_overridden: false,
          include: true,
        }));

        setPreviewDeadlines(deadlines);
      } catch (err) {
        // Fallback: generate mock preview
        const mockDeadlines: PreviewDeadline[] = [];
        const triggerDateObj = new Date(triggerDate);

        // Generate some mock deadlines based on the event type
        const offsets = selectedEvent.category === 'trial'
          ? [-90, -60, -45, -30, -21, -14, -7, -3, 0]
          : selectedEvent.category === 'pleading'
          ? [20, 30, 45, 60]
          : [10, 14, 21, 30];

        offsets.slice(0, Math.min(offsets.length, selectedEvent.deadline_count)).forEach((offset, index) => {
          const deadlineDate = new Date(triggerDateObj);
          deadlineDate.setDate(deadlineDate.getDate() + offset);

          mockDeadlines.push({
            id: `preview-${index}`,
            title: `${offset < 0 ? 'Pre-' : ''}${selectedEvent.name} Deadline ${index + 1}`,
            calculated_date: deadlineDate.toISOString().split('T')[0],
            override_date: null,
            priority: offset <= -30 ? 'critical' : offset <= 0 ? 'important' : 'standard',
            rule_citation: selectedEvent.citation,
            days_from_trigger: offset,
            is_overridden: false,
            include: true,
          });
        });

        setPreviewDeadlines(mockDeadlines);
      } finally {
        setPreviewLoading(false);
      }
    };

    const debounce = setTimeout(generatePreview, 300);
    return () => clearTimeout(debounce);
  }, [selectedEvent, triggerDate, rulesSource, serviceMethod, courtType]);

  // Toggle deadline override
  const handleToggleOverride = (id: string) => {
    setPreviewDeadlines(prev => prev.map(d =>
      d.id === id
        ? { ...d, is_overridden: !d.is_overridden, override_date: d.is_overridden ? null : d.calculated_date }
        : d
    ));
  };

  // Update override date
  const handleOverrideDateChange = (id: string, newDate: string) => {
    setPreviewDeadlines(prev => prev.map(d =>
      d.id === id ? { ...d, override_date: newDate } : d
    ));
  };

  // Toggle include/exclude deadline
  const handleToggleInclude = (id: string) => {
    setPreviewDeadlines(prev => prev.map(d =>
      d.id === id ? { ...d, include: !d.include } : d
    ));
  };

  // Create trigger with overrides
  const handleCreate = async () => {
    if (!selectedEvent || !triggerDate) return;

    setCreating(true);
    try {
      // Build overrides map
      const overrides: Record<string, string> = {};
      previewDeadlines.forEach(d => {
        if (d.is_overridden && d.override_date) {
          overrides[d.title] = d.override_date;
        }
      });

      // Build exclusions list
      const exclusions = previewDeadlines
        .filter(d => !d.include)
        .map(d => d.title);

      const response = await apiClient.post('/api/v1/triggers/create', {
        case_id: caseId,
        trigger_type: selectedEvent.trigger_type,
        trigger_date: triggerDate,
        jurisdiction: rulesSource,
        court_type: courtType,
        service_method: serviceMethod,
        overrides: Object.keys(overrides).length > 0 ? overrides : undefined,
        exclusions: exclusions.length > 0 ? exclusions : undefined,
      });

      const count = response.data.dependent_deadlines_created;
      showSuccess(`Created ${selectedEvent.name} with ${count} deadlines`);
      onSuccess();
      onClose();
    } catch (err: any) {
      showError(err.response?.data?.detail || 'Failed to create event');
    } finally {
      setCreating(false);
    }
  };

  // Reset state when closing
  useEffect(() => {
    if (!isOpen) {
      setSearchQuery('');
      setSelectedEvent(null);
      setTriggerDate('');
      setPreviewDeadlines([]);
      setShowDropdown(false);
    }
  }, [isOpen]);

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatDays = (days: number) => {
    if (days === 0) return 'Day of';
    if (days > 0) return `+${days} days`;
    return `${days} days`;
  };

  // Stats
  const includedCount = previewDeadlines.filter(d => d.include).length;
  const overriddenCount = previewDeadlines.filter(d => d.is_overridden).length;

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-gradient-to-r from-purple-50 to-blue-50 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Zap className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-800">
                  Smart Event Entry
                </h2>
                <p className="text-sm text-slate-600">
                  {selectedEvent
                    ? `${selectedEvent.name} - ${previewDeadlines.length} deadlines`
                    : 'Search for an event type to get started'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              disabled={creating}
              className="p-2 rounded-lg hover:bg-slate-200 transition-colors"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden flex flex-col lg:flex-row">
          {/* Left Panel: Event Selection */}
          <div className="w-full lg:w-80 flex-shrink-0 border-b lg:border-b-0 lg:border-r border-slate-200 flex flex-col">
            {/* Search Input */}
            <div className="p-4 border-b border-slate-100">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setShowDropdown(true);
                  }}
                  onFocus={() => setShowDropdown(true)}
                  placeholder="Search events (e.g., 'Trial', 'Motion')"
                  className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm"
                />
              </div>
            </div>

            {/* Event List */}
            <div className="flex-1 overflow-y-auto p-2">
              {Object.entries(groupedEvents).map(([category, events]) => (
                <div key={category} className="mb-2">
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider hover:bg-slate-50 rounded"
                  >
                    {expandedCategories.has(category) ? (
                      <ChevronDown className="w-3 h-3" />
                    ) : (
                      <ChevronRight className="w-3 h-3" />
                    )}
                    {EVENT_ICONS[category]}
                    {category}
                    <span className="ml-auto text-slate-400">({events.length})</span>
                  </button>

                  {expandedCategories.has(category) && (
                    <div className="mt-1 space-y-1">
                      {events.map(event => (
                        <button
                          key={event.id}
                          onClick={() => {
                            setSelectedEvent(event);
                            setShowDropdown(false);
                          }}
                          className={`w-full p-3 text-left rounded-lg border transition-colors ${
                            selectedEvent?.id === event.id
                              ? 'border-purple-300 bg-purple-50 ring-2 ring-purple-200'
                              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="font-medium text-sm text-slate-800 truncate">
                                {event.name}
                              </div>
                              <div className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                                {event.citation}
                              </div>
                            </div>
                            <span className="flex-shrink-0 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                              {event.deadline_count}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Configuration */}
            {selectedEvent && (
              <div className="p-4 border-t border-slate-200 space-y-4 bg-slate-50">
                {/* Trigger Date */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">
                    Event Date *
                  </label>
                  <input
                    type="date"
                    value={triggerDate}
                    onChange={(e) => setTriggerDate(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
                  />
                </div>

                {/* Rules Source */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">
                    Rules Authority
                  </label>
                  <select
                    value={rulesSource}
                    onChange={(e) => setRulesSource(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm bg-white"
                  >
                    {RULES_SOURCES.map(source => (
                      <option key={source.id} value={source.id}>
                        {source.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Service Method */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">
                    Service Method
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['email', 'mail', 'personal'] as const).map(method => (
                      <button
                        key={method}
                        onClick={() => setServiceMethod(method)}
                        className={`px-2 py-1.5 text-xs font-medium rounded border transition-colors ${
                          serviceMethod === method
                            ? 'border-purple-500 bg-purple-50 text-purple-700'
                            : 'border-slate-300 text-slate-600 hover:border-slate-400'
                        }`}
                      >
                        {method === 'email' ? 'Email' : method === 'mail' ? 'Mail' : 'Hand'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel: Live Cascade Preview */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {!selectedEvent || !triggerDate ? (
              <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center">
                  <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500 text-sm">
                    Select an event and date to preview deadlines
                  </p>
                </div>
              </div>
            ) : previewLoading ? (
              <div className="flex-1 flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
              </div>
            ) : (
              <>
                {/* Preview Header */}
                <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex-shrink-0">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium text-slate-800">
                        Proposed Docket
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {includedCount} of {previewDeadlines.length} deadlines
                        {overriddenCount > 0 && ` • ${overriddenCount} manual overrides`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-purple-500" />
                        Calculated
                      </span>
                      <span className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-amber-500" />
                        Override
                      </span>
                    </div>
                  </div>
                </div>

                {/* Preview List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                  {previewDeadlines.map((deadline) => (
                    <div
                      key={deadline.id}
                      className={`p-3 rounded-lg border transition-all ${
                        !deadline.include
                          ? 'bg-slate-50 border-slate-200 opacity-50'
                          : deadline.is_overridden
                          ? 'bg-amber-50 border-amber-200'
                          : 'bg-white border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Include Checkbox */}
                        <button
                          onClick={() => handleToggleInclude(deadline.id)}
                          className={`flex-shrink-0 mt-0.5 ${
                            deadline.include ? 'text-green-500' : 'text-slate-300'
                          }`}
                        >
                          {deadline.include ? (
                            <CheckCircle2 className="w-5 h-5" />
                          ) : (
                            <X className="w-5 h-5" />
                          )}
                        </button>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <h4 className={`font-medium text-sm ${
                                deadline.include ? 'text-slate-800' : 'text-slate-500 line-through'
                              }`}>
                                {deadline.title}
                              </h4>
                              <div className="flex items-center gap-2 mt-1 flex-wrap">
                                <span className={`text-xs px-1.5 py-0.5 rounded border ${PRIORITY_COLORS[deadline.priority] || PRIORITY_COLORS.standard}`}>
                                  {deadline.priority}
                                </span>
                                <span className="text-xs text-slate-400">
                                  {deadline.rule_citation}
                                </span>
                                <span className="text-xs text-purple-600 font-mono">
                                  {formatDays(deadline.days_from_trigger)}
                                </span>
                              </div>
                            </div>

                            {/* Date Display/Edit */}
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {deadline.is_overridden ? (
                                <input
                                  type="date"
                                  value={deadline.override_date || deadline.calculated_date}
                                  onChange={(e) => handleOverrideDateChange(deadline.id, e.target.value)}
                                  className="text-sm px-2 py-1 border border-amber-300 rounded bg-amber-50 focus:outline-none focus:ring-2 focus:ring-amber-500"
                                />
                              ) : (
                                <span className="text-sm font-mono text-slate-700">
                                  {formatDate(deadline.calculated_date)}
                                </span>
                              )}

                              {/* Override Toggle */}
                              <button
                                onClick={() => handleToggleOverride(deadline.id)}
                                className={`p-1.5 rounded transition-colors ${
                                  deadline.is_overridden
                                    ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                                    : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
                                }`}
                                title={deadline.is_overridden ? 'Using manual date' : 'Override date'}
                              >
                                <Edit2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between flex-shrink-0">
          <button
            onClick={onClose}
            disabled={creating}
            className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Cancel
          </button>

          <div className="flex items-center gap-3">
            {selectedEvent && triggerDate && previewDeadlines.length > 0 && (
              <div className="text-sm text-slate-500">
                <span className="font-medium text-purple-600">{includedCount}</span> deadlines
                {overriddenCount > 0 && (
                  <span className="ml-2">
                    (<span className="text-amber-600">{overriddenCount}</span> custom)
                  </span>
                )}
              </div>
            )}

            <button
              onClick={handleCreate}
              disabled={creating || !selectedEvent || !triggerDate || includedCount === 0}
              className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {creating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Create {includedCount} Deadlines
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
