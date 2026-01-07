'use client';

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
} from 'lucide-react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';
import { formatDeadlineDate } from '@/lib/formatters';

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

  return (
    <div
      className={`group relative border-l-4 ${priorityStyle.border} rounded-r-lg bg-white hover:bg-slate-50 transition-all ${
        isCompleted ? 'opacity-60' : ''
      } ${isOverdue ? 'ring-1 ring-red-200' : ''}`}
    >
      <div className="p-3">
        {/* Main Row */}
        <div className="flex items-start gap-3">
          {/* Selection/Complete Checkbox */}
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
              selectionMode
                ? 'text-blue-600'
                : isCompleted
                ? 'text-green-500'
                : 'text-slate-300 hover:text-green-500'
            } transition-colors`}
            title={selectionMode ? (isSelected ? 'Deselect' : 'Select') : (isCompleted ? 'Completed' : 'Mark complete')}
          >
            {selectionMode ? (
              isSelected ? (
                <CheckCircle2 className="w-5 h-5 fill-blue-600 text-white" />
              ) : (
                <Circle className="w-5 h-5" />
              )
            ) : isCompleted ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : (
              <Circle className="w-5 h-5" />
            )}
          </button>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title Row */}
            <div className="flex items-start justify-between gap-2">
              <h4 className={`font-medium text-sm ${
                isCompleted ? 'text-slate-500 line-through' : 'text-slate-900'
              }`}>
                {deadline.title}
              </h4>

              {/* Date */}
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
                    className={`text-sm font-medium ${
                      isOverdue
                        ? 'text-red-600'
                        : isCompleted
                        ? 'text-slate-400'
                        : 'text-slate-700 hover:text-blue-600'
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
              {/* Priority Badge */}
              <span className={`inline-flex px-1.5 py-0.5 text-xs font-medium rounded ${priorityStyle.bg} ${priorityStyle.text}`}>
                {deadline.priority}
              </span>

              {/* Type Badge */}
              {deadline.deadline_type && (
                <span className="inline-flex px-1.5 py-0.5 text-xs font-medium rounded bg-slate-100 text-slate-600">
                  {deadline.deadline_type}
                </span>
              )}

              {/* Auto-calculated Badge */}
              {deadline.is_calculated && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-700">
                  <Sparkles className="w-3 h-3" />
                  Auto
                </span>
              )}

              {/* Overdue Badge */}
              {isOverdue && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium rounded bg-red-100 text-red-700">
                  <AlertTriangle className="w-3 h-3" />
                  Overdue
                </span>
              )}

              {/* Rule Citation */}
              {deadline.applicable_rule && (
                <span className="text-xs text-slate-500 truncate max-w-[150px]" title={deadline.applicable_rule}>
                  {deadline.applicable_rule}
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

          {/* Actions Menu */}
          {!selectionMode && (
            <div className="relative flex-shrink-0" ref={menuRef}>
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-1 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreHorizontal className="w-4 h-4" />
              </button>

              {showMenu && (
                <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-20">
                  {!isCompleted && onComplete && (
                    <button
                      onClick={() => {
                        onComplete(deadline.id);
                        setShowMenu(false);
                      }}
                      className="w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                    >
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                      Mark Complete
                    </button>
                  )}
                  {onEdit && (
                    <button
                      onClick={() => {
                        onEdit(deadline);
                        setShowMenu(false);
                      }}
                      className="w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                    >
                      <Edit2 className="w-4 h-4 text-blue-600" />
                      Edit
                    </button>
                  )}
                  {!isCompleted && (
                    <button
                      onClick={() => {
                        handleDateClick();
                        setShowMenu(false);
                      }}
                      className="w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                    >
                      <Calendar className="w-4 h-4 text-amber-600" />
                      Reschedule
                    </button>
                  )}
                  <button
                    onClick={() => setShowMenu(false)}
                    className="w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                  >
                    <History className="w-4 h-4 text-slate-500" />
                    View History
                  </button>
                  {onDelete && (
                    <>
                      <div className="border-t border-slate-100 my-1" />
                      <button
                        onClick={() => {
                          onDelete(deadline.id);
                          setShowMenu(false);
                        }}
                        className="w-full px-3 py-1.5 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
