'use client';

/**
 * DeadlineCard - Single Deadline Display Component
 *
 * A dense, information-rich card for displaying a single deadline.
 * Used in lists, sidebars, and search results.
 *
 * Features:
 * - Priority-based color coding
 * - Overdue visual treatment
 * - Quick actions (complete, expand)
 * - Case context display
 */

import { memo } from 'react';
import {
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import type { Deadline, CalendarDeadline } from '@/types';
import { formatDeadlineDate } from '@/lib/formatters';

interface DeadlineCardProps {
  deadline: Deadline | CalendarDeadline;
  onClick?: () => void;
  onComplete?: (id: string) => void;
  showCase?: boolean;
  compact?: boolean;
  className?: string;
}

function DeadlineCardComponent({
  deadline,
  onClick,
  onComplete,
  showCase = true,
  compact = false,
  className = '',
}: DeadlineCardProps) {
  const isCompleted = deadline.status === 'completed';
  const isCancelled = deadline.status === 'cancelled';
  const isOverdue = !isCompleted && !isCancelled && deadline.deadline_date &&
    new Date(deadline.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));

  const hasCase = 'case_number' in deadline && deadline.case_number;

  const getPriorityStyles = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case 'fatal':
        return {
          border: 'border-l-red-600',
          badge: 'bg-red-100 text-red-800 border-red-200',
          text: 'text-red-700',
        };
      case 'critical':
        return {
          border: 'border-l-red-500',
          badge: 'bg-red-50 text-red-700 border-red-200',
          text: 'text-red-600',
        };
      case 'important':
        return {
          border: 'border-l-amber-500',
          badge: 'bg-amber-50 text-amber-700 border-amber-200',
          text: 'text-amber-600',
        };
      case 'standard':
        return {
          border: 'border-l-blue-500',
          badge: 'bg-blue-50 text-blue-700 border-blue-200',
          text: 'text-blue-600',
        };
      default:
        return {
          border: 'border-l-slate-400',
          badge: 'bg-slate-100 text-slate-600 border-slate-200',
          text: 'text-slate-500',
        };
    }
  };

  const priorityStyles = getPriorityStyles(deadline.priority);

  const handleComplete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onComplete && !isCompleted && !isCancelled) {
      onComplete(deadline.id);
    }
  };

  if (compact) {
    return (
      <div
        onClick={onClick}
        className={`
          flex items-center gap-3 px-3 py-2 bg-white border border-slate-200
          hover:bg-slate-50 cursor-pointer transition-colors
          border-l-4 ${priorityStyles.border}
          ${isCompleted ? 'opacity-60' : ''}
          ${isOverdue ? 'bg-red-50/50' : ''}
          ${className}
        `}
      >
        {/* Checkbox */}
        <button
          onClick={handleComplete}
          disabled={isCompleted || isCancelled}
          className={`
            flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center
            ${isCompleted
              ? 'bg-green-500 border-green-500 text-white'
              : 'border-slate-300 hover:border-green-500 text-transparent hover:text-green-500'
            }
            transition-colors disabled:cursor-default
          `}
        >
          <CheckCircle2 className="w-3 h-3" />
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium truncate ${isCompleted ? 'line-through text-slate-500' : 'text-slate-800'}`}>
            {deadline.title}
          </p>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {deadline.deadline_date && (
              <span className={`font-mono ${isOverdue ? 'text-red-600 font-bold' : ''}`}>
                {formatDeadlineDate(deadline.deadline_date)}
              </span>
            )}
            {hasCase && showCase && (
              <>
                <span className="text-slate-300">|</span>
                <span className="truncate">{(deadline as CalendarDeadline).case_number}</span>
              </>
            )}
          </div>
        </div>

        {/* Priority Badge (compact) */}
        <span className={`px-1.5 py-0.5 text-[10px] font-mono font-bold border ${priorityStyles.badge}`}>
          {deadline.priority?.toUpperCase().slice(0, 4) || 'STD'}
        </span>

        {/* Arrow */}
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={`
        group bg-white border border-slate-200 hover:border-slate-300
        hover:shadow-sm cursor-pointer transition-all
        border-l-4 ${priorityStyles.border}
        ${isCompleted ? 'opacity-70' : ''}
        ${isOverdue ? 'bg-red-50/30 border-red-200 hover:border-red-300' : ''}
        ${className}
      `}
    >
      {/* Main Content */}
      <div className="px-4 py-3">
        <div className="flex items-start gap-3">
          {/* Checkbox */}
          <button
            onClick={handleComplete}
            disabled={isCompleted || isCancelled}
            className={`
              flex-shrink-0 w-5 h-5 mt-0.5 rounded border-2 flex items-center justify-center
              ${isCompleted
                ? 'bg-green-500 border-green-500 text-white'
                : 'border-slate-300 hover:border-green-500 text-transparent hover:text-green-500'
              }
              transition-colors disabled:cursor-default
            `}
          >
            <CheckCircle2 className="w-3 h-3" />
          </button>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title Row */}
            <div className="flex items-center justify-between gap-2">
              <h4 className={`font-medium ${isCompleted ? 'line-through text-slate-500' : 'text-slate-800'}`}>
                {deadline.title}
              </h4>
              <span className={`flex-shrink-0 px-2 py-0.5 text-xs font-mono font-bold border ${priorityStyles.badge}`}>
                {deadline.priority?.toUpperCase() || 'STANDARD'}
              </span>
            </div>

            {/* Meta Row */}
            <div className="flex items-center gap-3 mt-1.5 text-sm">
              {/* Date */}
              <div className={`flex items-center gap-1 ${isOverdue ? 'text-red-600' : 'text-slate-600'}`}>
                {isOverdue ? (
                  <AlertTriangle className="w-3.5 h-3.5" />
                ) : (
                  <Calendar className="w-3.5 h-3.5" />
                )}
                <span className={`font-mono ${isOverdue ? 'font-bold' : ''}`}>
                  {deadline.deadline_date ? formatDeadlineDate(deadline.deadline_date) : 'No date'}
                </span>
              </div>

              {/* Case Info */}
              {hasCase && showCase && (
                <div className="flex items-center gap-1 text-slate-500">
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span className="truncate max-w-[200px]">
                    {(deadline as CalendarDeadline).case_number}
                  </span>
                </div>
              )}

              {/* Auto-calculated indicator */}
              {deadline.is_calculated && (
                <div className="flex items-center gap-1 text-cyan-600">
                  <Clock className="w-3.5 h-3.5" />
                  <span className="text-xs">Auto</span>
                </div>
              )}
            </div>

            {/* Description (if present) */}
            {deadline.description && (
              <p className="mt-2 text-sm text-slate-600 line-clamp-2">
                {deadline.description}
              </p>
            )}

            {/* Action Required */}
            {deadline.action_required && (
              <p className="mt-2 text-sm text-blue-700 bg-blue-50 px-2 py-1 border border-blue-100 inline-block">
                {deadline.action_required}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Rule Citation Footer */}
      {deadline.applicable_rule && (
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 text-xs text-slate-500 font-mono">
          {deadline.applicable_rule}
        </div>
      )}
    </div>
  );
}

export const DeadlineCard = memo(DeadlineCardComponent);
export default DeadlineCard;
