'use client';

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
  CornerDownRight
} from 'lucide-react';
import type { Trigger } from '@/hooks/useCaseData';

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

  return (
    <div className={`group ${isExpanded ? 'bg-slate-50' : 'bg-white hover:bg-slate-50'}`}>

      {/* 1. MASTER ROW */}
      <div className="flex items-center px-4 py-3 gap-4">
        {/* Expand Toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-slate-400 hover:text-slate-700 transition-colors"
        >
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {/* Date Badge (Monospace) */}
        <div className="flex flex-col items-center justify-center border border-slate-300 px-2 py-1 bg-white min-w-[80px]">
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
              <span className="bg-red-100 text-red-700 text-[10px] font-bold px-1.5 py-0.5 border border-red-200 uppercase tracking-wide">
                {overdueCount} Critical
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 mt-1">
            <span className="text-xs text-slate-500 font-mono">
              ID: {trigger.trigger_type}
            </span>
            <span className="text-xs text-slate-500">
              {childDeadlines.length} downstream events
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {/* Strict Menu (No Shadow, Just Border) */}
          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-400 z-20 text-sm">
                <button
                  onClick={() => { onEdit?.(trigger); setShowMenu(false); }}
                  className="w-full text-left px-4 py-2 hover:bg-slate-100 flex items-center gap-2"
                >
                  <Edit2 className="w-3 h-3" /> Edit Date
                </button>
                <button
                  onClick={() => { onRecalculate?.(trigger.id); setShowMenu(false); }}
                  className="w-full text-left px-4 py-2 hover:bg-slate-100 flex items-center gap-2"
                >
                  <RefreshCw className={`w-3 h-3 ${isRecalculating ? 'animate-spin' : ''}`} />
                  Recalculate Cascade
                </button>
                <div className="border-t border-slate-200 my-1"></div>
                <button
                  onClick={() => { onDelete?.(trigger.id); setShowMenu(false); }}
                  className="w-full text-left px-4 py-2 hover:bg-red-50 text-red-700 flex items-center gap-2"
                >
                  <Trash2 className="w-3 h-3" /> Delete Trigger
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 2. DETAIL CASCADE (The "Thread" View) */}
      {isExpanded && (
        <div className="pl-8 pr-4 pb-4">
          <div className="border-l-2 border-slate-300 pl-4 space-y-1">

            {/* Header for Cascade */}
            <div className="flex items-center gap-2 text-xs text-slate-400 font-medium uppercase tracking-wider mb-2 pt-2">
              <CornerDownRight className="w-3 h-3" />
              Generated Deadlines
            </div>

            {childDeadlines.length === 0 ? (
              <div className="text-sm text-slate-400 italic py-2">No deadlines generated yet.</div>
            ) : (
              <table className="w-full text-sm border-collapse">
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
                    // V2: Use pre-calculated is_overdue from API
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
                        <td className="py-2 align-top font-sans text-slate-800 pr-4">
                          {dl.title}
                        </td>
                        <td className="py-2 align-top text-right text-slate-400 truncate max-w-[150px]" title={dl.applicable_rule}>
                          {dl.applicable_rule?.split(' ')[0] || 'RULE'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
