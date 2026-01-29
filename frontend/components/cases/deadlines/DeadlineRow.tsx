'use client';

/**
 * DeadlineRow - Responsive Deadline Display
 *
 * Desktop (lg+): Horizontal layout with title, badges, date on same row
 * Mobile/Vertical: Stacked layout for readability on narrow screens
 */

import { useState, useRef, useEffect } from 'react';
import {
  CheckCircle2,
  Circle,
  MoreHorizontal,
  Calendar,
  Link2,
  Edit2,
  Trash2,
  History,
  Sparkles,
  AlertTriangle,
  Shield,
  ShieldAlert,
  ShieldCheck,
  FileCheck,
  Scale,
  BookOpen,
} from 'lucide-react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';
import { formatDeadlineDate } from '@/lib/formatters';
import { IntegrityIndicator } from '@/components/audit/IntegrityBadge';

interface DeadlineRowProps {
  deadline: Deadline;
  triggers: Trigger[];
  selectionMode?: boolean;
  isSelected?: boolean;
  onToggleSelection?: (id: string) => void;
  onComplete?: (id: string) => void;
  onEdit?: (deadline: Deadline) => void;
  onDelete?: (id: string) => void;
  onReschedule?: (id: string, newDate: Date) => void;
  onViewChain?: (triggerId: string) => void;
  onClick?: (deadline: Deadline) => void;
}

const PRIORITY_COLORS: Record<string, { border: string; bg: string; text: string }> = {
  fatal: { border: 'border-l-red-600', bg: 'bg-red-50', text: 'text-red-800' },
  critical: { border: 'border-l-red-500', bg: 'bg-red-50', text: 'text-red-700' },
  high: { border: 'border-l-orange-500', bg: 'bg-orange-50', text: 'text-orange-700' },
  important: { border: 'border-l-amber-500', bg: 'bg-amber-50', text: 'text-amber-700' },
  medium: { border: 'border-l-yellow-500', bg: 'bg-yellow-50', text: 'text-yellow-700' },
  standard: { border: 'border-l-blue-500', bg: 'bg-blue-50', text: 'text-blue-700' },
  low: { border: 'border-l-slate-400', bg: 'bg-slate-50', text: 'text-slate-600' },
  informational: { border: 'border-l-gray-400', bg: 'bg-gray-50', text: 'text-gray-600' },
};

const AUTHORITY_TIER_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  federal: { bg: 'bg-purple-100', text: 'text-purple-700', icon: 'text-purple-600' },
  state: { bg: 'bg-blue-100', text: 'text-blue-700', icon: 'text-blue-600' },
  local: { bg: 'bg-green-100', text: 'text-green-700', icon: 'text-green-600' },
  standing_order: { bg: 'bg-amber-100', text: 'text-amber-700', icon: 'text-amber-600' },
  firm: { bg: 'bg-slate-100', text: 'text-slate-700', icon: 'text-slate-600' },
};

export default function DeadlineRow({
  deadline,
  triggers,
  selectionMode = false,
  isSelected = false,
  onToggleSelection,
  onComplete,
  onEdit,
  onDelete,
  onReschedule,
  onViewChain,
  onClick,
}: DeadlineRowProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingDate, setEditingDate] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);
  const dateInputRef = useRef<HTMLInputElement>(null);

  const isCompleted = deadline.status === 'completed';
  const isCancelled = deadline.status === 'cancelled';
  const isOverdue = !isCompleted && !isCancelled && deadline.deadline_date &&
    new Date(deadline.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));

  // Find parent trigger
  const parentTrigger = deadline.trigger_event
    ? triggers.find(t => t.trigger_type === deadline.trigger_event)
    : null;

  const priorityStyle = PRIORITY_COLORS[deadline.priority] || PRIORITY_COLORS.standard;

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus date input when editing
  useEffect(() => {
    if (isEditing && dateInputRef.current) {
      dateInputRef.current.focus();
    }
  }, [isEditing]);

  const handleDateClick = () => {
    if (!isCompleted && !isCancelled && deadline.deadline_date) {
      setEditingDate(deadline.deadline_date.split('T')[0]);
      setIsEditing(true);
    }
  };

  const handleDateChange = () => {
    if (editingDate && onReschedule) {
      onReschedule(deadline.id, new Date(editingDate));
    }
    setIsEditing(false);
  };

  const handleDateKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleDateChange();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
    }
  };

  // Format date for mobile display
  const formatDateShort = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const handleRowClick = (e: React.MouseEvent) => {
    // Don't trigger row click if clicking on interactive elements
    const target = e.target as HTMLElement;
    if (
      target.closest('button') ||
      target.closest('input') ||
      target.closest('a')
    ) {
      return;
    }
    onClick?.(deadline);
  };

  return (
    <div
      onClick={handleRowClick}
      className={`group relative border-l-4 ${priorityStyle.border} rounded-r-lg bg-white hover:bg-slate-50 transition-all ${
        isCompleted ? 'opacity-60' : ''
      } ${isOverdue ? 'ring-1 ring-red-200' : ''} ${onClick ? 'cursor-pointer' : ''}`}
    >
      {/* Responsive padding: more on mobile for touch targets */}
      <div className="p-3 lg:p-3">

        {/* Desktop Layout (lg+): Single row */}
        <div className="hidden lg:flex items-start gap-3">
          {/* Checkbox */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (selectionMode && onToggleSelection) {
                onToggleSelection(deadline.id);
              } else if (!isCompleted && onComplete) {
                onComplete(deadline.id);
              }
            }}
            className={`flex-shrink-0 mt-0.5 ${
              selectionMode ? 'text-blue-600' :
              isCompleted ? 'text-green-500' :
              'text-slate-300 hover:text-green-500'
            } transition-colors`}
          >
            {selectionMode ? (
              isSelected ? <CheckCircle2 className="w-5 h-5 fill-blue-600 text-white" /> : <Circle className="w-5 h-5" />
            ) : isCompleted ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : (
              <Circle className="w-5 h-5" />
            )}
          </button>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title + Date Row */}
            <div className="flex items-start justify-between gap-2">
              <h4 className={`font-medium text-sm min-w-0 ${isCompleted ? 'text-slate-500 line-through' : 'text-slate-900'}`}>
                <span className="block truncate">{deadline.title}</span>
              </h4>

              <div className="flex-shrink-0">
                {isEditing ? (
                  <input
                    ref={dateInputRef}
                    type="date"
                    value={editingDate}
                    onChange={(e) => setEditingDate(e.target.value)}
                    onBlur={handleDateChange}
                    onKeyDown={handleDateKeyDown}
                    className="text-sm px-2 py-0.5 border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                ) : (
                  <button
                    onClick={handleDateClick}
                    className={`text-sm font-medium font-mono ${
                      isOverdue ? 'text-red-600' : isCompleted ? 'text-slate-400' : 'text-slate-700 hover:text-blue-600'
                    } ${!isCompleted && !isCancelled ? 'hover:underline cursor-pointer' : ''}`}
                    disabled={isCompleted || isCancelled}
                  >
                    {deadline.deadline_date ? formatDeadlineDate(deadline.deadline_date) : 'No date'}
                  </button>
                )}
              </div>
            </div>

            {/* Meta Row */}
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <span className={`inline-flex px-1.5 py-0.5 text-xs font-medium rounded ${priorityStyle.bg} ${priorityStyle.text}`}>
                {deadline.priority}
              </span>
              {deadline.deadline_type && (
                <span className="inline-flex px-1.5 py-0.5 text-xs font-medium rounded bg-slate-100 text-slate-600">
                  {deadline.deadline_type}
                </span>
              )}
              {deadline.is_calculated && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-700">
                  <Sparkles className="w-3 h-3" />
                  Auto
                </span>
              )}
              {/* Confidence Badge */}
              {deadline.confidence_level && (
                <span
                  className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium rounded ${
                    deadline.confidence_level === 'high'
                      ? 'bg-green-100 text-green-700'
                      : deadline.confidence_level === 'medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                  title={`Confidence: ${deadline.confidence_score || 0}%`}
                >
                  {deadline.confidence_level === 'high' ? (
                    <ShieldCheck className="w-3 h-3" />
                  ) : deadline.confidence_level === 'medium' ? (
                    <Shield className="w-3 h-3" />
                  ) : (
                    <ShieldAlert className="w-3 h-3" />
                  )}
                  {deadline.confidence_score || 0}%
                </span>
              )}
              {isOverdue && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium rounded bg-red-100 text-red-700">
                  <AlertTriangle className="w-3 h-3" />
                  Overdue
                </span>
              )}
              {deadline.applicable_rule && (
                <span
                  className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium rounded cursor-help ${
                    deadline.authority_tier && AUTHORITY_TIER_COLORS[deadline.authority_tier]
                      ? `${AUTHORITY_TIER_COLORS[deadline.authority_tier].bg} ${AUTHORITY_TIER_COLORS[deadline.authority_tier].text}`
                      : 'bg-slate-100 text-slate-600'
                  }`}
                  title={deadline.rule_citation || deadline.calculation_basis || deadline.applicable_rule}
                >
                  {deadline.source_rule_id ? (
                    <Scale className="w-3 h-3" />
                  ) : (
                    <BookOpen className="w-3 h-3" />
                  )}
                  <span className="truncate max-w-[120px]">{deadline.applicable_rule}</span>
                </span>
              )}
            </div>

            {/* Chain Link */}
            {parentTrigger && (
              <button
                onClick={() => onViewChain?.(parentTrigger.id)}
                className="flex items-center gap-1 mt-2 text-xs text-purple-600 hover:text-purple-700 hover:underline"
              >
                <Link2 className="w-3 h-3" />
                <span>From: {parentTrigger.title}</span>
              </button>
            )}
          </div>

          {/* Actions (Desktop) */}
          {!selectionMode && (
            <div className="relative flex-shrink-0" ref={menuRef}>
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-1 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreHorizontal className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Mobile/Vertical Layout (< lg): Stacked */}
        <div className="lg:hidden">
          {/* Row 1: Checkbox + Title + Menu */}
          <div className="flex items-start gap-3">
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (selectionMode && onToggleSelection) {
                  onToggleSelection(deadline.id);
                } else if (!isCompleted && onComplete) {
                  onComplete(deadline.id);
                }
              }}
              className={`flex-shrink-0 mt-0.5 p-1 -m-1 ${
                selectionMode ? 'text-blue-600' :
                isCompleted ? 'text-green-500' :
                'text-slate-300 hover:text-green-500'
              } transition-colors`}
            >
              {selectionMode ? (
                isSelected ? <CheckCircle2 className="w-6 h-6 fill-blue-600 text-white" /> : <Circle className="w-6 h-6" />
              ) : isCompleted ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : (
                <Circle className="w-6 h-6" />
              )}
            </button>

            <div className="flex-1 min-w-0">
              <h4 className={`font-medium text-base leading-snug ${isCompleted ? 'text-slate-500 line-through' : 'text-slate-900'}`}>
                {deadline.title}
              </h4>
            </div>

            {!selectionMode && (
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-2 -m-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-200 flex-shrink-0"
              >
                <MoreHorizontal className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* Row 2: Date + Badges */}
          <div className="flex items-center gap-2 mt-2 ml-8 flex-wrap">
            {/* Date Badge */}
            {isEditing ? (
              <input
                ref={dateInputRef}
                type="date"
                value={editingDate}
                onChange={(e) => setEditingDate(e.target.value)}
                onBlur={handleDateChange}
                onKeyDown={handleDateKeyDown}
                className="text-sm px-2 py-1 border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            ) : (
              <button
                onClick={handleDateClick}
                disabled={isCompleted || isCancelled}
                className={`flex items-center gap-1.5 px-2 py-1 rounded text-sm font-mono font-medium ${
                  isOverdue ? 'bg-red-100 text-red-700' :
                  isCompleted ? 'bg-slate-100 text-slate-400' :
                  'bg-slate-100 text-slate-700 hover:bg-blue-100 hover:text-blue-700'
                }`}
              >
                <Calendar className="w-3.5 h-3.5" />
                {deadline.deadline_date ? formatDateShort(deadline.deadline_date) : 'No date'}
              </button>
            )}

            {/* Priority */}
            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded ${priorityStyle.bg} ${priorityStyle.text}`}>
              {deadline.priority}
            </span>

            {/* Overdue */}
            {isOverdue && (
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-700">
                <AlertTriangle className="w-3 h-3" />
                Overdue
              </span>
            )}

            {/* Auto */}
            {deadline.is_calculated && (
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-700">
                <Sparkles className="w-3 h-3" />
                Auto
              </span>
            )}

            {/* Confidence Badge (Mobile) */}
            {deadline.confidence_level && (
              <span
                className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded ${
                  deadline.confidence_level === 'high'
                    ? 'bg-green-100 text-green-700'
                    : deadline.confidence_level === 'medium'
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-red-100 text-red-700'
                }`}
                title={`Confidence: ${deadline.confidence_score || 0}%`}
              >
                {deadline.confidence_level === 'high' ? (
                  <ShieldCheck className="w-3 h-3" />
                ) : deadline.confidence_level === 'medium' ? (
                  <Shield className="w-3 h-3" />
                ) : (
                  <ShieldAlert className="w-3 h-3" />
                )}
                {deadline.confidence_score || 0}%
              </span>
            )}
          </div>

          {/* Row 3: Rule + Chain (if present) */}
          {(deadline.applicable_rule || parentTrigger) && (
            <div className="mt-2 ml-8 flex flex-wrap items-center gap-2">
              {deadline.applicable_rule && (
                <span
                  className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded cursor-help ${
                    deadline.authority_tier && AUTHORITY_TIER_COLORS[deadline.authority_tier]
                      ? `${AUTHORITY_TIER_COLORS[deadline.authority_tier].bg} ${AUTHORITY_TIER_COLORS[deadline.authority_tier].text}`
                      : 'bg-slate-100 text-slate-600'
                  }`}
                  title={deadline.rule_citation || deadline.calculation_basis || deadline.applicable_rule}
                >
                  {deadline.source_rule_id ? (
                    <Scale className="w-3 h-3" />
                  ) : (
                    <BookOpen className="w-3 h-3" />
                  )}
                  {deadline.applicable_rule}
                </span>
              )}
              {parentTrigger && (
                <button
                  onClick={() => onViewChain?.(parentTrigger.id)}
                  className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-700"
                >
                  <Link2 className="w-3 h-3" />
                  <span>{parentTrigger.title}</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Shared Dropdown Menu */}
        {showMenu && (
          <div ref={menuRef} className="absolute right-2 top-12 lg:top-8 w-44 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-20">
            {!isCompleted && onComplete && (
              <button
                onClick={() => { onComplete(deadline.id); setShowMenu(false); }}
                className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Complete
              </button>
            )}
            {onEdit && (
              <button
                onClick={() => { onEdit(deadline); setShowMenu(false); }}
                className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
              >
                <Edit2 className="w-4 h-4 text-blue-600" />
                Edit
              </button>
            )}
            {!isCompleted && (
              <button
                onClick={() => { handleDateClick(); setShowMenu(false); }}
                className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
              >
                <Calendar className="w-4 h-4 text-amber-600" />
                Reschedule
              </button>
            )}
            <button
              onClick={() => setShowMenu(false)}
              className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
            >
              <History className="w-4 h-4 text-slate-500" />
              History
            </button>
            <div className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-slate-500" />
              <span>Verify Integrity</span>
              <IntegrityIndicator recordId={deadline.id} size="sm" />
            </div>
            {onDelete && (
              <>
                <div className="border-t border-slate-100 my-1" />
                <button
                  onClick={() => { onDelete(deadline.id); setShowMenu(false); }}
                  className="w-full px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
