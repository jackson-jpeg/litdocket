'use client';

import { useState } from 'react';
import { CheckSquare, Square, Sparkles, Check, Clock, Edit2, Trash2, CheckCircle2 } from 'lucide-react';
import { formatDeadlineDate } from '@/lib/formatters';
import type { Deadline } from '@/hooks/useCaseData';

interface DeadlineCardProps {
  deadline: Deadline;
  selectionMode: boolean;
  isSelected: boolean;
  onToggleSelection: (id: string) => void;
  onQuickComplete?: (id: string) => void;
  onQuickEdit?: (id: string) => void;
  onQuickDelete?: (id: string) => void;
}

export default function DeadlineCard({
  deadline,
  selectionMode,
  isSelected,
  onToggleSelection,
  onQuickComplete,
  onQuickEdit,
  onQuickDelete,
}: DeadlineCardProps) {
  const [showActions, setShowActions] = useState(false);
  const [justCompleted, setJustCompleted] = useState(false);

  const isCompleted = deadline.status === 'completed';
  const isCancelled = deadline.status === 'cancelled';

  const getPriorityStyles = () => {
    // Completed deadlines get muted, calm styling
    if (isCompleted) {
      return 'border-green-300 bg-green-50/30';
    }
    if (isCancelled) {
      return 'border-gray-300 bg-gray-50/30';
    }

    // Active deadlines use priority colors
    switch (deadline.priority) {
      case 'high':
      case 'critical':
      case 'fatal':
        return 'border-red-500 bg-red-50';
      case 'medium':
      case 'important':
        return 'border-yellow-500 bg-yellow-50';
      default:
        return 'border-blue-500 bg-blue-50';
    }
  };

  const getStatusStyles = () => {
    switch (deadline.status) {
      case 'completed':
        return 'bg-green-100 text-green-700 font-medium';
      case 'cancelled':
        return 'bg-gray-100 text-gray-600';
      default:
        return 'bg-blue-100 text-blue-700';
    }
  };

  const handleQuickComplete = (id: string) => {
    if (onQuickComplete) {
      setJustCompleted(true);
      setTimeout(() => setJustCompleted(false), 1000);
      onQuickComplete(id);
    }
  };

  return (
    <div
      className={`group relative border-l-4 ${getPriorityStyles()} rounded-r-lg p-4 ${
        selectionMode ? 'cursor-pointer hover:opacity-80' : 'hover:shadow-md'
      } transition-all duration-300 ${
        isCompleted ? 'opacity-60 hover:opacity-75' : 'opacity-100'
      } ${justCompleted ? 'scale-[0.98] animate-pulse' : 'scale-100'}`}
      onClick={() => selectionMode && onToggleSelection(deadline.id)}
      onMouseEnter={() => !selectionMode && setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Header: Date and Status */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3 flex-1">
          {/* Selection Checkbox */}
          {selectionMode && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleSelection(deadline.id);
              }}
              className="flex-shrink-0"
            >
              {isSelected ? (
                <CheckSquare className="w-5 h-5 text-blue-600" />
              ) : (
                <Square className="w-5 h-5 text-slate-400 hover:text-slate-600" />
              )}
            </button>
          )}

          {/* Date and Title */}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <p className={`text-sm font-bold ${isCompleted ? 'text-slate-500 line-through' : 'text-slate-900'}`}>
                {formatDeadlineDate(deadline.deadline_date)}
              </p>
              {deadline.is_calculated && (
                <span
                  className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded"
                  title="Auto-calculated from trigger"
                >
                  <Sparkles className="w-3 h-3" />
                  Auto
                </span>
              )}
            </div>
            <p className={`text-sm font-medium mt-1 ${isCompleted ? 'text-slate-500 line-through' : 'text-slate-800'}`}>
              {deadline.title}
            </p>
          </div>
        </div>

        {/* Status Badge */}
        <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusStyles()}`}>
          {deadline.status}
        </span>
      </div>

      {/* Description */}
      {deadline.description && (
        <div className={`text-xs mt-2 whitespace-pre-line ${isCompleted ? 'text-slate-400' : 'text-slate-600'}`}>
          {deadline.description}
        </div>
      )}

      {/* Applicable Rule */}
      {deadline.applicable_rule && (
        <div className={`mt-2 pt-2 border-t ${isCompleted ? 'border-slate-100' : 'border-slate-200'}`}>
          <p className={`text-xs ${isCompleted ? 'text-slate-400' : 'text-slate-500'}`}>
            <span className="font-medium">Rule:</span> {deadline.applicable_rule}
          </p>
        </div>
      )}

      {/* Quick Actions (appears on hover) */}
      {!selectionMode && showActions && deadline.status !== 'completed' && (
        <div className="absolute top-2 right-2 flex items-center gap-1 bg-white rounded-lg shadow-lg border border-gray-200 p-1">
          {onQuickComplete && deadline.status === 'pending' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleQuickComplete(deadline.id);
              }}
              className="p-1.5 hover:bg-green-50 rounded transition-colors group/btn"
              title="Mark as complete"
            >
              <Check className="w-4 h-4 text-green-600" />
            </button>
          )}
          {onQuickEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onQuickEdit(deadline.id);
              }}
              className="p-1.5 hover:bg-blue-50 rounded transition-colors group/btn"
              title="Edit deadline"
            >
              <Edit2 className="w-4 h-4 text-blue-600" />
            </button>
          )}
          {onQuickDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onQuickDelete(deadline.id);
              }}
              className="p-1.5 hover:bg-red-50 rounded transition-colors group/btn"
              title="Delete deadline"
            >
              <Trash2 className="w-4 h-4 text-red-600" />
            </button>
          )}
        </div>
      )}

      {/* Large Checkmark Overlay for Completed Deadlines */}
      {isCompleted && (
        <div className="absolute top-2 right-2 pointer-events-none">
          <div className="relative">
            <CheckCircle2 className="w-8 h-8 text-green-500 drop-shadow-lg" />
            <div className="absolute inset-0 bg-green-400 rounded-full blur-md opacity-30 animate-pulse" />
          </div>
        </div>
      )}
    </div>
  );
}
