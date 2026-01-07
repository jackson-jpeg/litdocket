'use client';

import { useState, useRef, useEffect } from 'react';
import {
  Zap,
  Calendar,
  ChevronDown,
  ChevronRight,
  Edit2,
  RefreshCw,
  Trash2,
  MoreHorizontal,
  CheckCircle2,
  AlertTriangle,
  Clock,
} from 'lucide-react';
import type { Trigger, Deadline } from '@/hooks/useCaseData';

interface TriggerCardProps {
  trigger: Trigger;
  deadlines: Deadline[];
  onEdit?: (trigger: Trigger) => void;
  onRecalculate?: (triggerId: string) => void;
  onDelete?: (triggerId: string) => void;
  onDeadlineClick?: (deadline: Deadline) => void;
}

const TRIGGER_TYPE_LABELS: Record<string, string> = {
  TRIAL_DATE: 'Trial Date',
  COMPLAINT_SERVED: 'Complaint Served',
  ANSWER_FILED: 'Answer Filed',
  DISCOVERY_CUTOFF: 'Discovery Cutoff',
  MOTION_FILED: 'Motion Filed',
  ORDER_ENTERED: 'Order Entered',
  DEPOSITION_NOTICED: 'Deposition Noticed',
  EXPERT_DISCLOSURE: 'Expert Disclosure',
  MEDIATION_SCHEDULED: 'Mediation Scheduled',
  HEARING_SCHEDULED: 'Hearing Scheduled',
  APPEAL_FILED: 'Appeal Filed',
  REMAND_DATE: 'Remand Date',
  CASE_MANAGEMENT: 'Case Management Conference',
  PRETRIAL_CONFERENCE: 'Pretrial Conference',
};

export default function TriggerCard({
  trigger,
  deadlines,
  onEdit,
  onRecalculate,
  onDelete,
  onDeadlineClick,
}: TriggerCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Filter deadlines that belong to this trigger
  const childDeadlines = deadlines.filter(d => d.trigger_event === trigger.trigger_type);

  // Calculate stats
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const completedCount = childDeadlines.filter(d => d.status === 'completed').length;
  const overdueCount = childDeadlines.filter(d =>
    d.status === 'pending' &&
    d.deadline_date &&
    new Date(d.deadline_date) < today
  ).length;
  const pendingCount = childDeadlines.filter(d => d.status === 'pending').length;

  const triggerLabel = TRIGGER_TYPE_LABELS[trigger.trigger_type] || trigger.trigger_type;

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

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          {/* Left side - expand button and info */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-start gap-2 flex-1 text-left"
          >
            <div className="mt-0.5">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-purple-600" />
              ) : (
                <ChevronRight className="w-4 h-4 text-purple-600" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-purple-600 flex-shrink-0" />
                <span className="font-medium text-purple-900 truncate">
                  {trigger.title || triggerLabel}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-1 text-xs text-purple-700">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {formatDate(trigger.trigger_date)}
                </span>
                <span>
                  {childDeadlines.length} deadline{childDeadlines.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </button>

          {/* Right side - stats and menu */}
          <div className="flex items-center gap-2">
            {/* Stats Badges */}
            <div className="flex items-center gap-1">
              {overdueCount > 0 && (
                <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded">
                  <AlertTriangle className="w-3 h-3" />
                  {overdueCount}
                </span>
              )}
              {pendingCount > 0 && (
                <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                  <Clock className="w-3 h-3" />
                  {pendingCount}
                </span>
              )}
              {completedCount > 0 && (
                <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded">
                  <CheckCircle2 className="w-3 h-3" />
                  {completedCount}
                </span>
              )}
            </div>

            {/* Menu */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(!showMenu);
                }}
                className="p-1 rounded hover:bg-purple-200 text-purple-600 transition-colors"
              >
                <MoreHorizontal className="w-4 h-4" />
              </button>

              {showMenu && (
                <div className="absolute right-0 top-full mt-1 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-20">
                  {onEdit && (
                    <button
                      onClick={() => {
                        onEdit(trigger);
                        setShowMenu(false);
                      }}
                      className="w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                    >
                      <Edit2 className="w-4 h-4 text-blue-600" />
                      Edit Date
                    </button>
                  )}
                  {onRecalculate && (
                    <button
                      onClick={() => {
                        onRecalculate(trigger.id);
                        setShowMenu(false);
                      }}
                      className="w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                    >
                      <RefreshCw className="w-4 h-4 text-amber-600" />
                      Recalculate
                    </button>
                  )}
                  {onDelete && (
                    <>
                      <div className="border-t border-slate-100 my-1" />
                      <button
                        onClick={() => {
                          onDelete(trigger.id);
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
          </div>
        </div>
      </div>

      {/* Expanded Content - Child Deadlines */}
      {isExpanded && childDeadlines.length > 0 && (
        <div className="border-t border-purple-200 bg-white/50 px-3 py-2">
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {childDeadlines
              .sort((a, b) => {
                if (!a.deadline_date) return 1;
                if (!b.deadline_date) return -1;
                return new Date(a.deadline_date).getTime() - new Date(b.deadline_date).getTime();
              })
              .map(deadline => {
                const isOverdue = deadline.status === 'pending' &&
                  deadline.deadline_date &&
                  new Date(deadline.deadline_date) < today;
                const isCompleted = deadline.status === 'completed';

                return (
                  <button
                    key={deadline.id}
                    onClick={() => onDeadlineClick?.(deadline)}
                    className={`w-full text-left p-2 rounded-md hover:bg-purple-100 transition-colors ${
                      isCompleted ? 'opacity-60' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        {isCompleted ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                        ) : isOverdue ? (
                          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        ) : (
                          <Clock className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        )}
                        <span className={`text-sm truncate ${
                          isCompleted ? 'text-slate-500 line-through' :
                          isOverdue ? 'text-red-700' : 'text-slate-700'
                        }`}>
                          {deadline.title}
                        </span>
                      </div>
                      <span className={`text-xs flex-shrink-0 ${
                        isOverdue ? 'text-red-600 font-medium' : 'text-slate-500'
                      }`}>
                        {deadline.deadline_date ? formatDate(deadline.deadline_date) : 'No date'}
                      </span>
                    </div>
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
