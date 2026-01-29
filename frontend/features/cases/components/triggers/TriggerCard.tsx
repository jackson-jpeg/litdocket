'use client';

/**
 * TriggerCard - Responsive Trigger Event Display
 *
 * Desktop (lg+): Single row layout
 * Mobile/Vertical: Stacked card layout for readability
 */

import { useState } from 'react';
import {
  ChevronRight,
  ChevronDown,
  MoreHorizontal,
  Edit2,
  RefreshCw,
  Trash2,
  AlertTriangle,
  Clock,
  Check,
  CornerDownRight,
  Calendar
} from 'lucide-react';
import type { Trigger } from '@/features/cases/hooks/useCaseData';

interface TriggerCardProps {
  trigger: Trigger;
  onEdit?: (trigger: Trigger) => void;
  onRecalculate?: (triggerId: string) => void;
  onDelete?: (triggerId: string) => void;
  isRecalculating?: boolean;
}

export default function TriggerCard({
  trigger,
  onEdit,
  onRecalculate,
  onDelete,
  isRecalculating
}: TriggerCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  // V2: Use pre-calculated nested data from API (no client-side filtering)
  const childDeadlines = trigger.child_deadlines || [];
  const overdueCount = trigger.status_summary?.overdue || 0;

  // Strict Date Formatting
  const formatDate = (d: string) => new Date(d).toLocaleDateString('en-US', {
    month: '2-digit', day: '2-digit', year: 'numeric'
  });

  const formatDateShort = (d: string) => new Date(d).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric'
  });

  return (
    <div className={`group ${isExpanded ? 'bg-slate-50' : 'bg-white hover:bg-slate-50'}`}>

      {/* 1. MASTER ROW - Responsive: stacked on mobile, horizontal on desktop */}
      <div className="px-3 py-3 lg:px-4 lg:py-3">
        {/* Desktop Layout (lg+) */}
        <div className="hidden lg:flex items-center gap-4">
          {/* Expand Toggle */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-slate-400 hover:text-slate-700 transition-colors flex-shrink-0"
          >
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>

          {/* Date Badge (Monospace) */}
          <div className="flex flex-col items-center justify-center border border-slate-300 px-2 py-1 bg-white min-w-[80px] flex-shrink-0">
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">DATE</span>
            <span className="font-mono text-sm font-medium text-slate-900">
              {formatDate(trigger.trigger_date)}
            </span>
          </div>

          {/* Title & Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="font-serif text-slate-900 font-medium truncate">
                {trigger.title}
              </h4>
              {overdueCount > 0 && (
                <span className="bg-red-100 text-red-700 text-[10px] font-bold px-1.5 py-0.5 border border-red-200 uppercase tracking-wide flex-shrink-0">
                  {overdueCount} Critical
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 mt-1">
              <span className="text-xs text-slate-500 font-mono truncate">
                {trigger.trigger_type}
              </span>
              <span className="text-xs text-slate-500 flex-shrink-0">
                {childDeadlines.length} events
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="relative flex-shrink-0">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded"
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile/Vertical Layout (< lg) - Stacked Card */}
        <div className="lg:hidden">
          {/* Row 1: Expand + Title */}
          <div className="flex items-start gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-slate-400 hover:text-slate-700 transition-colors flex-shrink-0 mt-1"
            >
              {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>

            <div className="flex-1 min-w-0">
              <h4 className="font-serif text-slate-900 font-medium text-base leading-snug">
                {trigger.title}
              </h4>
              <span className="text-xs text-slate-500 font-mono">
                {trigger.trigger_type}
              </span>
            </div>

            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded flex-shrink-0"
            >
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>

          {/* Row 2: Date + Badges */}
          <div className="flex items-center gap-2 mt-2 ml-7 flex-wrap">
            <div className="flex items-center gap-1.5 text-sm text-slate-700 bg-slate-100 px-2 py-1 rounded">
              <Calendar className="w-3.5 h-3.5" />
              <span className="font-mono font-medium">{formatDate(trigger.trigger_date)}</span>
            </div>

            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded">
              {childDeadlines.length} events
            </span>

            {overdueCount > 0 && (
              <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-1 rounded flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {overdueCount} overdue
              </span>
            )}
          </div>
        </div>

        {/* Dropdown Menu (shared) */}
        {showMenu && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setShowMenu(false)}
            />
            <div className="absolute right-2 lg:right-4 mt-1 w-48 bg-white border border-slate-300 shadow-lg z-20 text-sm rounded-lg overflow-hidden">
              <button
                onClick={() => { onEdit?.(trigger); setShowMenu(false); }}
                className="w-full text-left px-4 py-3 hover:bg-slate-100 flex items-center gap-2"
              >
                <Edit2 className="w-4 h-4" /> Edit Date
              </button>
              <button
                onClick={() => { onRecalculate?.(trigger.id); setShowMenu(false); }}
                className="w-full text-left px-4 py-3 hover:bg-slate-100 flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${isRecalculating ? 'animate-spin' : ''}`} />
                Recalculate
              </button>
              <div className="border-t border-slate-200"></div>
              <button
                onClick={() => { onDelete?.(trigger.id); setShowMenu(false); }}
                className="w-full text-left px-4 py-3 hover:bg-red-50 text-red-700 flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" /> Delete
              </button>
            </div>
          </>
        )}
      </div>

      {/* 2. DETAIL CASCADE - Responsive */}
      {isExpanded && (
        <div className="px-3 pb-4 lg:pl-8 lg:pr-4">
          <div className="border-l-2 border-slate-300 pl-3 lg:pl-4 space-y-1">

            {/* Header for Cascade */}
            <div className="flex items-center gap-2 text-xs text-slate-400 font-medium uppercase tracking-wider mb-2 pt-2">
              <CornerDownRight className="w-3 h-3" />
              Generated Deadlines
            </div>

            {childDeadlines.length === 0 ? (
              <div className="text-sm text-slate-400 italic py-2">No deadlines generated yet.</div>
            ) : (
              <>
                {/* Desktop Table View (lg+) */}
                <table className="hidden lg:table w-full text-sm border-collapse">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b border-slate-200">
                      <th className="py-1 font-normal w-8"></th>
                      <th className="py-1 font-normal w-24">Due Date</th>
                      <th className="py-1 font-normal">Action</th>
                      <th className="py-1 font-normal w-24 text-right">Rule</th>
                    </tr>
                  </thead>
                  <tbody className="font-mono text-xs">
                    {childDeadlines.map(dl => {
                      const isOverdue = dl.is_overdue;
                      const isDone = dl.status === 'completed';

                      return (
                        <tr key={dl.id} className={`group hover:bg-white transition-colors ${isDone ? 'opacity-50' : ''}`}>
                          <td className="py-2 align-top">
                            {isOverdue ? (
                              <AlertTriangle className="w-3 h-3 text-red-600" />
                            ) : isDone ? (
                              <Check className="w-3 h-3 text-green-600" />
                            ) : (
                              <div className="w-1.5 h-1.5 rounded-full bg-slate-300 mt-1"></div>
                            )}
                          </td>
                          <td className={`py-2 align-top font-medium ${isOverdue ? 'text-red-700' : 'text-slate-700'}`}>
                            {dl.deadline_date ? formatDate(dl.deadline_date) : 'TBD'}
                          </td>
                          <td className="py-2 align-top font-sans text-slate-800 pr-4 min-w-0">
                            <span className="block truncate">{dl.title}</span>
                          </td>
                          <td className="py-2 align-top text-right text-slate-400 truncate max-w-[150px]" title={dl.applicable_rule}>
                            {dl.applicable_rule?.split(' ')[0] || 'RULE'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {/* Mobile Card View (< lg) */}
                <div className="lg:hidden space-y-2">
                  {childDeadlines.map(dl => {
                    const isOverdue = dl.is_overdue;
                    const isDone = dl.status === 'completed';

                    return (
                      <div
                        key={dl.id}
                        className={`p-3 bg-white rounded border-l-4 ${
                          isOverdue ? 'border-red-500' :
                          isDone ? 'border-green-500 opacity-60' :
                          'border-slate-300'
                        }`}
                      >
                        {/* Row 1: Status + Title */}
                        <div className="flex items-start gap-2">
                          <div className="flex-shrink-0 mt-0.5">
                            {isOverdue ? (
                              <AlertTriangle className="w-4 h-4 text-red-600" />
                            ) : isDone ? (
                              <Check className="w-4 h-4 text-green-600" />
                            ) : (
                              <Clock className="w-4 h-4 text-slate-400" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-medium ${isDone ? 'line-through text-slate-500' : 'text-slate-800'}`}>
                              {dl.title}
                            </p>
                          </div>
                        </div>

                        {/* Row 2: Date + Rule */}
                        <div className="flex items-center justify-between mt-2 ml-6">
                          <span className={`text-sm font-mono font-medium ${isOverdue ? 'text-red-600' : 'text-slate-600'}`}>
                            {dl.deadline_date ? formatDateShort(dl.deadline_date) : 'TBD'}
                          </span>
                          <span className="text-xs text-slate-400 truncate max-w-[120px]" title={dl.applicable_rule}>
                            {dl.applicable_rule?.split(' ')[0] || ''}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
