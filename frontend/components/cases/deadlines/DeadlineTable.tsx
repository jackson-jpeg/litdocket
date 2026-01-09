'use client';

/**
 * DeadlineTable - Sovereign Design System
 *
 * A strict HTML table for deadline data. Dense, professional, no-nonsense.
 * 32px row height, uppercase serif headers, monospace dates.
 *
 * "Density is Reliability"
 */

import { useState, useCallback } from 'react';
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

export default function DeadlineTable({
  deadlines,
  triggers,
  selectionMode = false,
  selectedIds = new Set(),
  onToggleSelection,
  onComplete,
  onEdit,
  onDelete,
  onReschedule,
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
    <div className="panel">
      <table className="data-table">
        <thead>
          <tr>
            {selectionMode && (
              <th style={{ width: '32px' }}>
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
            <th style={{ width: '32px' }} className="text-center font-serif">!</th>
            <th style={{ width: '100px' }} className="font-serif">DATE</th>
            <th className="font-serif">EVENT</th>
            <th style={{ width: '120px' }} className="font-serif">AUTHORITY</th>
            <th style={{ width: '80px' }} className="font-serif text-right">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {deadlines.map((deadline) => {
            const isCompleted = deadline.status === 'completed';
            const rowClass = getPriorityRowClass(deadline);

            return (
              <tr
                key={deadline.id}
                className={`${rowClass} ${isCompleted ? 'opacity-60' : ''} hover:bg-blue-50 cursor-pointer`}
                style={{ height: '32px' }}
                onClick={() => {
                  if (selectionMode && onToggleSelection) {
                    onToggleSelection(deadline.id);
                  }
                }}
              >
                {/* Selection Checkbox */}
                {selectionMode && (
                  <td className="text-center" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(deadline.id)}
                      onChange={() => onToggleSelection?.(deadline.id)}
                      className="accent-navy"
                    />
                  </td>
                )}

                {/* Status Flag */}
                <td className="text-center font-mono">
                  <StatusFlag deadline={deadline} />
                </td>

                {/* Date - Monospace */}
                <td className="font-mono text-xs" onClick={(e) => e.stopPropagation()}>
                  {editingId === deadline.id ? (
                    <input
                      type="date"
                      value={editingDate}
                      onChange={(e) => setEditingDate(e.target.value)}
                      onBlur={() => handleDateSave(deadline.id)}
                      onKeyDown={(e) => handleDateKeyDown(e, deadline.id)}
                      autoFocus
                      className="input text-xs py-0 px-1"
                      style={{ width: '120px' }}
                    />
                  ) : (
                    <button
                      onClick={() => handleDateClick(deadline)}
                      className={`hover:underline ${
                        isCompleted ? 'line-through text-ink-muted' : ''
                      }`}
                      disabled={isCompleted}
                    >
                      {deadline.deadline_date
                        ? formatDeadlineDate(deadline.deadline_date)
                        : '—'}
                    </button>
                  )}
                </td>

                {/* Event Title - Serif */}
                <td className="font-serif">
                  <div className={`truncate ${isCompleted ? 'line-through text-ink-muted' : ''}`}>
                    {deadline.title}
                  </div>
                  {deadline.trigger_event && (
                    <div className="text-xxs text-ink-muted truncate">
                      ← {getTriggerTitle(deadline.trigger_event)}
                    </div>
                  )}
                </td>

                {/* Authority/Rule - Monospace */}
                <td className="font-mono text-xs text-ink-secondary truncate">
                  {deadline.applicable_rule || '—'}
                </td>

                {/* Actions */}
                <td className="text-right" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-1">
                    {!isCompleted && onComplete && (
                      <button
                        onClick={() => onComplete(deadline.id)}
                        className="btn btn-secondary text-xs px-2 py-0.5"
                        title="Complete"
                      >
                        ✓
                      </button>
                    )}
                    {onEdit && (
                      <button
                        onClick={() => onEdit(deadline)}
                        className="btn btn-secondary text-xs px-2 py-0.5"
                        title="Edit"
                      >
                        Edit
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
