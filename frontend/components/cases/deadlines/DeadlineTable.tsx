'use client';

/**
 * DeadlineTable - Sovereign Design System
 *
 * A strict HTML table for deadline data. Dense, professional, no-nonsense.
 * 32px row height, uppercase serif headers, monospace dates.
 *
 * "Density is Reliability"
 *
 * Features:
 * - table-fixed layout (no horizontal scroll)
 * - Legal Pad yellow zebra stripes
 * - Tabular numerals for aligned dates
 * - "DONE" stamp effect on completed items
 */

import { useState } from 'react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';
import { formatDeadlineDate } from '@/lib/formatters';

interface DeadlineTableProps {
  deadlines: Deadline[];
  triggers: Trigger[];
  selectionMode?: boolean;
  selectedIds?: Set<string>;
  onToggleSelection?: (id: string) => void;
  onComplete?: (id: string) => void;
  onEdit?: (deadline: Deadline) => void;
  onDelete?: (id: string) => void;
  onReschedule?: (id: string, newDate: Date) => void;
  onViewDeadline?: (deadline: Deadline) => void;
}

// Status flag indicator
const StatusFlag = ({ deadline }: { deadline: Deadline }) => {
  const isCompleted = deadline.status === 'completed';
  const isCancelled = deadline.status === 'cancelled';
  const isOverdue = !isCompleted && !isCancelled && deadline.deadline_date &&
    new Date(deadline.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));

  if (isCompleted) return <span className="text-green-600">✓</span>;
  if (isCancelled) return <span className="text-gray-400">—</span>;
  if (isOverdue) return <span className="text-alert font-bold">!</span>;

  // Priority-based flag
  switch (deadline.priority) {
    case 'fatal':
    case 'critical':
      return <span className="text-alert font-bold">!!</span>;
    case 'high':
    case 'important':
      return <span className="text-amber font-bold">!</span>;
    default:
      return <span className="text-ink-muted">·</span>;
  }
};

// Priority row class
const getPriorityRowClass = (deadline: Deadline): string => {
  const isCompleted = deadline.status === 'completed';
  const isCancelled = deadline.status === 'cancelled';
  const isOverdue = !isCompleted && !isCancelled && deadline.deadline_date &&
    new Date(deadline.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));

  if (isCompleted) return '';
  if (isCancelled) return 'opacity-50';
  if (isOverdue) return 'status-critical';

  switch (deadline.priority) {
    case 'fatal':
    case 'critical':
      return 'status-critical';
    case 'high':
    case 'important':
      return 'status-warning';
    default:
      return '';
  }
};

// DONE stamp component for completed items
const DoneStamp = () => (
  <div
    className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden"
    aria-hidden="true"
  >
    <span
      className="text-green-600/20 font-bold text-2xl tracking-widest select-none"
      style={{
        transform: 'rotate(-12deg)',
        fontFamily: 'Impact, Haettenschweiler, sans-serif',
        letterSpacing: '0.2em'
      }}
    >
      DONE
    </span>
  </div>
);

export default function DeadlineTable({
  deadlines,
  triggers,
  selectionMode = false,
  selectedIds = new Set(),
  onToggleSelection,
  onComplete,
  onDelete,
  onReschedule,
  onViewDeadline,
}: DeadlineTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingDate, setEditingDate] = useState('');

  // Find trigger by type
  const getTriggerTitle = (triggerEvent: string | undefined): string => {
    if (!triggerEvent) return '';
    const trigger = triggers.find(t => t.trigger_type === triggerEvent);
    return trigger ? trigger.title : triggerEvent;
  };

  const handleDateClick = (deadline: Deadline) => {
    if (deadline.status !== 'completed' && deadline.status !== 'cancelled' && deadline.deadline_date) {
      setEditingDate(deadline.deadline_date.split('T')[0]);
      setEditingId(deadline.id);
    }
  };

  const handleDateSave = (id: string) => {
    if (editingDate && onReschedule) {
      onReschedule(id, new Date(editingDate));
    }
    setEditingId(null);
  };

  const handleDateKeyDown = (e: React.KeyboardEvent, id: string) => {
    if (e.key === 'Enter') handleDateSave(id);
    if (e.key === 'Escape') setEditingId(null);
  };

  if (deadlines.length === 0) {
    return (
      <div className="panel">
        <div className="panel-body text-center py-8">
          <p className="text-ink-muted">No deadlines</p>
        </div>
      </div>
    );
  }

  return (
    <div className="panel overflow-hidden">
      <table className="data-table table-fixed w-full border-collapse">
        <thead>
          <tr className="border-b-2 border-gray-300">
            {selectionMode && (
              <th className="w-10 py-2 px-1 border-r border-gray-200 bg-gray-50">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    if (e.target.checked) {
                      deadlines.forEach(d => onToggleSelection?.(d.id));
                    }
                  }}
                  className="accent-navy"
                />
              </th>
            )}
            <th className="w-10 py-2 px-1 text-center font-serif border-r border-gray-200 bg-gray-50">!</th>
            <th className="w-[120px] py-2 px-1 font-serif border-r border-gray-200 bg-gray-50">DATE</th>
            <th className="py-2 px-1 font-serif border-r border-gray-200 bg-gray-50">EVENT</th>
            <th className="w-[100px] py-2 px-1 font-serif border-r border-gray-200 bg-gray-50">AUTHORITY</th>
            <th className="w-20 py-2 px-1 font-serif text-right bg-gray-50">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {deadlines.map((deadline, index) => {
            const isCompleted = deadline.status === 'completed';
            const rowClass = getPriorityRowClass(deadline);
            // Legal pad yellow stripe for even rows
            const zebraClass = index % 2 === 1 ? 'bg-[#FEFCE8]/50' : '';

            return (
              <tr
                key={deadline.id}
                className={`
                  ${rowClass}
                  ${isCompleted ? 'bg-gray-100' : zebraClass}
                  hover:bg-blue-50
                  cursor-pointer
                  border-b border-gray-200
                  relative
                `}
                onClick={() => {
                  if (selectionMode && onToggleSelection) {
                    onToggleSelection(deadline.id);
                  } else if (onViewDeadline) {
                    onViewDeadline(deadline);
                  }
                }}
              >
                {/* Selection Checkbox */}
                {selectionMode && (
                  <td className="py-2 px-1 text-center border-r border-gray-200" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(deadline.id)}
                      onChange={() => onToggleSelection?.(deadline.id)}
                      className="accent-navy"
                    />
                  </td>
                )}

                {/* Status Flag */}
                <td className="py-2 px-1 text-center font-mono border-r border-gray-200">
                  <StatusFlag deadline={deadline} />
                </td>

                {/* Date - Monospace with Tabular Nums */}
                <td
                  className="py-2 px-1 font-mono text-xs border-r border-gray-200"
                  style={{ fontVariantNumeric: 'tabular-nums' }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {editingId === deadline.id ? (
                    <input
                      type="date"
                      value={editingDate}
                      onChange={(e) => setEditingDate(e.target.value)}
                      onBlur={() => handleDateSave(deadline.id)}
                      onKeyDown={(e) => handleDateKeyDown(e, deadline.id)}
                      autoFocus
                      className="input text-xs py-0 px-1 w-full"
                    />
                  ) : (
                    <button
                      onClick={() => handleDateClick(deadline)}
                      className={`hover:underline ${
                        isCompleted ? 'line-through text-ink-muted' : ''
                      }`}
                      disabled={isCompleted}
                      style={{ fontVariantNumeric: 'tabular-nums' }}
                    >
                      {deadline.deadline_date
                        ? formatDeadlineDate(deadline.deadline_date)
                        : '—'}
                    </button>
                  )}
                </td>

                {/* Event Title - Serif with text wrapping + DONE stamp */}
                <td className="py-2 px-1 font-serif text-sm leading-tight whitespace-normal break-words border-r border-gray-200 relative">
                  {/* DONE Stamp overlay for completed items */}
                  {isCompleted && <DoneStamp />}

                  <div className={`${isCompleted ? 'line-through text-ink-muted' : ''}`}>
                    {deadline.title}
                  </div>
                  {deadline.trigger_event && (
                    <div className="text-xxs text-ink-muted">
                      ← {getTriggerTitle(deadline.trigger_event)}
                    </div>
                  )}
                </td>

                {/* Authority/Rule - Monospace with truncate + hover tooltip */}
                <td
                  className="py-2 px-1 font-mono text-xs text-ink-secondary truncate border-r border-gray-200"
                  title={deadline.applicable_rule || undefined}
                >
                  {/* E-Service badge */}
                  {deadline.service_method === 'electronic' && (
                    <span className="text-blue-500 mr-1" title="E-Service">@</span>
                  )}
                  {deadline.applicable_rule || '—'}
                </td>

                {/* Actions - Sovereign Design */}
                <td className="py-2 px-1 text-right" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-2">
                    {/* Sovereign Checkbox - Mark Complete */}
                    {onComplete && (
                      <button
                        onClick={() => onComplete(deadline.id)}
                        className={`w-5 h-5 border border-gray-400 flex items-center justify-center cursor-pointer transition-colors ${
                          isCompleted
                            ? 'bg-green-600 border-green-600 text-white'
                            : 'bg-white hover:border-navy hover:bg-gray-50'
                        }`}
                        title={isCompleted ? 'Completed' : 'Mark Complete'}
                        style={{ borderRadius: 0 }}
                      >
                        {isCompleted && <span className="text-xs font-bold">✓</span>}
                      </button>
                    )}
                    {/* Trash Button - Delete */}
                    {onDelete && !isCompleted && (
                      <button
                        onClick={() => {
                          if (confirm(`Delete deadline "${deadline.title}"? This action cannot be undone.`)) {
                            onDelete(deadline.id);
                          }
                        }}
                        className="w-5 h-5 border border-gray-400 flex items-center justify-center cursor-pointer bg-white hover:border-red-600 hover:bg-red-50 hover:text-red-600 transition-colors text-gray-500"
                        title="Delete"
                        style={{ borderRadius: 0 }}
                      >
                        <span className="text-xs">×</span>
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
