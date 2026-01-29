'use client';

/**
 * UnifiedDeadlineModal - Consolidated Deadline Detail & Edit Modal
 *
 * Merges functionality from:
 * - /features/cases/components/deadlines/DeadlineDetailModal.tsx (editing, trigger chain)
 * - /features/calendar/components/DeadlineDetailModal.tsx (animations, navigation)
 *
 * Features:
 * - View all deadline details with trigger chain context
 * - Inline editing for date, priority, description
 * - Mark complete / Delete actions
 * - Navigate to case
 * - Framer Motion animations
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle,
  Scale,
  FileText,
  Edit2,
  Trash2,
  Save,
  Link,
  User,
  ExternalLink,
} from 'lucide-react';
import type { Deadline, CalendarDeadline } from '@/types';
import { formatDeadlineDate, formatDateTime } from '@/lib/formatters';
import apiClient from '@/lib/api-client';

// Trigger info for displaying chain context
export interface TriggerInfo {
  id?: string;
  title: string;
  trigger_type: string;
  trigger_date?: string;
}

interface UnifiedDeadlineModalProps {
  isOpen: boolean;
  deadline: Deadline | CalendarDeadline | null;
  triggers?: TriggerInfo[];
  onClose: () => void;
  onUpdate?: () => void;
  onComplete?: (id: string) => void | Promise<void>;
  onDelete?: (id: string) => void | Promise<void>;
  showCaseLink?: boolean;
}

export default function UnifiedDeadlineModal({
  isOpen,
  deadline,
  triggers = [],
  onClose,
  onUpdate,
  onComplete,
  onDelete,
  showCaseLink = true,
}: UnifiedDeadlineModalProps) {
  const router = useRouter();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [editedDeadline, setEditedDeadline] = useState<Partial<Deadline>>({});

  // Reset edit state when deadline changes
  useEffect(() => {
    if (deadline) {
      setEditedDeadline({
        title: deadline.title,
        description: deadline.description,
        deadline_date: deadline.deadline_date?.split('T')[0],
        priority: deadline.priority,
        action_required: deadline.action_required,
      });
      setIsEditing(false);
      setShowDeleteConfirm(false);
    }
  }, [deadline]);

  if (!isOpen || !deadline) return null;

  const isCompleted = deadline.status === 'completed';
  const isCancelled = deadline.status === 'cancelled';
  const isOverdue = !isCompleted && !isCancelled && deadline.deadline_date &&
    new Date(deadline.deadline_date) < new Date(new Date().setHours(0, 0, 0, 0));

  // Find parent trigger
  const parentTrigger = deadline.trigger_event
    ? triggers.find(t => t.trigger_type === deadline.trigger_event)
    : null;

  // Check if deadline has case info (CalendarDeadline type)
  const hasCase = 'case_number' in deadline && deadline.case_number;

  const getPriorityColor = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case 'fatal': return 'text-red-700 bg-red-100 border-red-300';
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'high':
      case 'important': return 'text-amber-700 bg-amber-50 border-amber-200';
      case 'standard': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-slate-600 bg-slate-100 border-slate-200';
    }
  };

  const getStatusColor = () => {
    if (isCompleted) return 'bg-green-50 border-green-200 text-green-800';
    if (isCancelled) return 'bg-slate-100 border-slate-300 text-slate-500';
    if (isOverdue) return 'bg-red-50 border-red-200 text-red-800';
    return 'bg-blue-50 border-blue-200 text-blue-800';
  };

  const getStatusText = () => {
    if (isCompleted) return 'COMPLETED';
    if (isCancelled) return 'CANCELLED';
    if (isOverdue) return 'OVERDUE';
    return 'PENDING';
  };

  const handleSave = async () => {
    if (!deadline) return;

    setIsSaving(true);
    try {
      await apiClient.patch(`/api/v1/deadlines/${deadline.id}`, {
        title: editedDeadline.title,
        description: editedDeadline.description,
        deadline_date: editedDeadline.deadline_date,
        priority: editedDeadline.priority,
        action_required: editedDeadline.action_required,
      });
      setIsEditing(false);
      onUpdate?.();
    } catch (err) {
      console.error('Failed to update deadline:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleComplete = async () => {
    if (!onComplete) return;
    setIsCompleting(true);
    try {
      await onComplete(deadline.id);
      onClose();
    } finally {
      setIsCompleting(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    setIsDeleting(true);
    try {
      await onDelete(deadline.id);
      onClose();
    } catch (error) {
      console.error('Failed to delete deadline:', error);
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const goToCase = () => {
    router.push(`/cases/${deadline.case_id}`);
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="bg-white w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-slate-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className={`px-4 py-3 flex items-center justify-between border-b-2 ${
              isOverdue ? 'bg-red-50 border-red-300' : 'bg-slate-50 border-slate-300'
            }`}>
              <div className="flex items-center gap-3">
                <Calendar className={`w-5 h-5 ${isOverdue ? 'text-red-600' : 'text-slate-600'}`} />
                <div>
                  <span className="font-mono text-sm uppercase tracking-wide text-slate-700">
                    Deadline Details
                  </span>
                  {hasCase && (
                    <p className="text-xs text-slate-500 mt-0.5">
                      {(deadline as CalendarDeadline).case_number} - {(deadline as CalendarDeadline).case_title}
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-slate-600 transition-colors p-1 rounded hover:bg-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Status Banner */}
            <div className={`px-4 py-2 border-b flex items-center justify-between ${getStatusColor()}`}>
              <div className="flex items-center gap-2">
                {isCompleted ? (
                  <CheckCircle className="w-4 h-4" />
                ) : isOverdue ? (
                  <AlertTriangle className="w-4 h-4" />
                ) : (
                  <Clock className="w-4 h-4" />
                )}
                <span className="font-mono text-sm font-bold">{getStatusText()}</span>
              </div>
              <span className={`px-2 py-0.5 text-xs font-mono border ${getPriorityColor(deadline.priority)}`}>
                {deadline.priority?.toUpperCase() || 'STANDARD'}
              </span>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Title */}
              <div>
                <label className="text-xs text-slate-500 uppercase font-mono mb-1 block">
                  Event Title
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={editedDeadline.title || ''}
                    onChange={(e) => setEditedDeadline(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full border border-slate-300 px-3 py-2 text-lg font-serif focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                ) : (
                  <p className={`text-lg font-serif ${isCompleted ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                    {deadline.title}
                  </p>
                )}
              </div>

              {/* Date & Priority Row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-500 uppercase font-mono mb-1 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    Due Date
                  </label>
                  {isEditing ? (
                    <input
                      type="date"
                      value={editedDeadline.deadline_date || ''}
                      onChange={(e) => setEditedDeadline(prev => ({ ...prev, deadline_date: e.target.value }))}
                      className="w-full border border-slate-300 px-3 py-2 font-mono focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  ) : (
                    <p className={`font-mono text-lg ${isOverdue ? 'text-red-600 font-bold' : ''}`}>
                      {deadline.deadline_date ? formatDeadlineDate(deadline.deadline_date) : 'No date set'}
                    </p>
                  )}
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase font-mono mb-1 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Priority
                  </label>
                  {isEditing ? (
                    <select
                      value={editedDeadline.priority || 'standard'}
                      onChange={(e) => setEditedDeadline(prev => ({ ...prev, priority: e.target.value }))}
                      className="w-full border border-slate-300 px-3 py-2 font-mono focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="fatal">FATAL</option>
                      <option value="critical">CRITICAL</option>
                      <option value="important">IMPORTANT</option>
                      <option value="standard">STANDARD</option>
                      <option value="informational">INFORMATIONAL</option>
                    </select>
                  ) : (
                    <p className={`font-mono ${
                      deadline.priority === 'fatal' || deadline.priority === 'critical' ? 'text-red-600 font-bold' :
                      deadline.priority === 'important' ? 'text-amber-600' : 'text-slate-700'
                    }`}>
                      {deadline.priority?.toUpperCase() || 'STANDARD'}
                    </p>
                  )}
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="text-xs text-slate-500 uppercase font-mono mb-1 flex items-center gap-1">
                  <FileText className="w-3 h-3" />
                  Description / Notes
                </label>
                {isEditing ? (
                  <textarea
                    value={editedDeadline.description || ''}
                    onChange={(e) => setEditedDeadline(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                    placeholder="Add notes about this deadline..."
                    className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-sm text-slate-700 bg-slate-50 p-3 border border-slate-200 min-h-[60px]">
                    {deadline.description || 'No description'}
                  </p>
                )}
              </div>

              {/* Action Required */}
              {(deadline.action_required || isEditing) && (
                <div>
                  <label className="text-xs text-slate-500 uppercase font-mono mb-1 flex items-center gap-1">
                    <User className="w-3 h-3" />
                    Action Required
                  </label>
                  {isEditing ? (
                    <input
                      type="text"
                      value={editedDeadline.action_required || ''}
                      onChange={(e) => setEditedDeadline(prev => ({ ...prev, action_required: e.target.value }))}
                      placeholder="What action is needed?"
                      className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  ) : (
                    <div className="p-3 bg-blue-50 border border-blue-200">
                      <p className="text-sm text-blue-800">{deadline.action_required}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Legal Authority */}
              {deadline.applicable_rule && (
                <div>
                  <label className="text-xs text-slate-500 uppercase font-mono mb-1 flex items-center gap-1">
                    <Scale className="w-3 h-3" />
                    Legal Authority
                  </label>
                  <p className="font-mono text-sm bg-purple-50 border border-purple-200 px-3 py-2 text-purple-800">
                    {deadline.applicable_rule}
                  </p>
                </div>
              )}

              {/* Calculation Basis */}
              {deadline.calculation_basis && (
                <div>
                  <label className="text-xs text-slate-500 uppercase font-mono mb-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Calculation
                  </label>
                  <p className="text-sm text-slate-600 bg-slate-50 border border-slate-200 px-3 py-2">
                    {deadline.calculation_basis}
                  </p>
                </div>
              )}

              {/* Trigger Chain */}
              {parentTrigger && (
                <div className="border-t border-slate-200 pt-4 mt-4">
                  <label className="text-xs text-slate-500 uppercase font-mono mb-2 flex items-center gap-1">
                    <Link className="w-3 h-3" />
                    Trigger Chain
                  </label>
                  <div className="bg-cyan-50 border border-cyan-200 p-3">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-cyan-700 font-mono font-bold">FROM:</span>
                      <span className="font-medium text-slate-800">{parentTrigger.title}</span>
                    </div>
                    {parentTrigger.trigger_date && (
                      <div className="text-xs text-slate-500 mt-1 font-mono">
                        Trigger Date: {formatDeadlineDate(parentTrigger.trigger_date)}
                      </div>
                    )}
                    {deadline.is_calculated && (
                      <div className="text-xs text-cyan-700 mt-1 font-medium">
                        Auto-calculated from trigger event
                      </div>
                    )}
                    {deadline.is_manually_overridden && (
                      <div className="text-xs text-orange-600 mt-1 font-medium">
                        Manually adjusted (won't auto-recalculate)
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Metadata */}
              {deadline.created_at && (
                <div className="border-t border-slate-200 pt-4 mt-4 text-xs text-slate-400 font-mono">
                  <div className="flex justify-between">
                    <span>Created: {formatDateTime(deadline.created_at)}</span>
                    <span>ID: {deadline.id.slice(0, 8)}...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Footer Actions */}
            <div className="border-t border-slate-200 px-4 py-3 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {showCaseLink && (
                  <button
                    onClick={goToCase}
                    className="flex items-center gap-2 px-3 py-2 text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded transition-colors text-sm"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Go to Case
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    disabled={isDeleting}
                    className="flex items-center gap-2 px-3 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors text-sm disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                )}
              </div>
              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-4 py-2 border border-slate-300 text-slate-600 font-mono text-sm hover:bg-slate-100 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={isSaving}
                      className="px-4 py-2 bg-blue-600 text-white font-mono text-sm hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                      <Save className="w-4 h-4" />
                      {isSaving ? 'Saving...' : 'Save'}
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => setIsEditing(true)}
                      className="px-4 py-2 border border-slate-300 text-slate-700 font-mono text-sm hover:bg-slate-100 transition-colors flex items-center gap-2"
                    >
                      <Edit2 className="w-4 h-4" />
                      Edit
                    </button>
                    {!isCompleted && !isCancelled && onComplete && (
                      <button
                        onClick={handleComplete}
                        disabled={isCompleting}
                        className="px-4 py-2 bg-green-600 text-white font-mono text-sm hover:bg-green-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                      >
                        <CheckCircle className="w-4 h-4" />
                        {isCompleting ? 'Completing...' : 'Complete'}
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          </motion.div>

          {/* Delete Confirmation Modal */}
          <AnimatePresence>
            {showDeleteConfirm && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="fixed inset-0 bg-black/60 flex items-center justify-center z-[60]"
                onClick={() => setShowDeleteConfirm(false)}
              >
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.15 }}
                  className="bg-white shadow-2xl max-w-md w-full mx-4 p-6 border border-slate-200"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-red-100 rounded-full">
                      <AlertTriangle className="w-6 h-6 text-red-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-800">
                      Delete Deadline?
                    </h3>
                  </div>
                  <p className="text-sm text-slate-600 mb-6">
                    Are you sure you want to delete <span className="font-medium text-slate-800">"{deadline.title}"</span>? This action cannot be undone.
                  </p>
                  <div className="flex items-center justify-end gap-3">
                    <button
                      onClick={() => setShowDeleteConfirm(false)}
                      disabled={isDeleting}
                      className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded transition-colors disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleDelete}
                      disabled={isDeleting}
                      className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors disabled:opacity-50"
                    >
                      <Trash2 className="w-4 h-4" />
                      {isDeleting ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
