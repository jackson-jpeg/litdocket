'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  X,
  Calendar,
  Clock,
  CheckCircle2,
  ExternalLink,
  AlertTriangle,
  Edit,
  Scale,
  User,
  FileText,
  Trash2,
} from 'lucide-react';
import { CalendarDeadline } from '@/hooks/useCalendarDeadlines';

interface DeadlineDetailModalProps {
  deadline: CalendarDeadline | null;
  onClose: () => void;
  onComplete: (deadlineId: string) => Promise<void>;
  onDelete?: (deadlineId: string) => Promise<void>;
}

export default function DeadlineDetailModal({
  deadline,
  onClose,
  onComplete,
  onDelete,
}: DeadlineDetailModalProps) {
  const router = useRouter();
  const [completing, setCompleting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  if (!deadline) return null;

  const isOverdue = (() => {
    if (!deadline.deadline_date || deadline.status !== 'pending') return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const deadlineDate = new Date(deadline.deadline_date);
    deadlineDate.setHours(0, 0, 0, 0);
    return deadlineDate < today;
  })();

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'fatal':
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'important':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'standard':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'cancelled':
        return 'bg-slate-100 text-slate-500';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const handleComplete = async () => {
    setCompleting(true);
    try {
      await onComplete(deadline.id);
      onClose();
    } finally {
      setCompleting(false);
    }
  };

  const goToCase = () => {
    router.push(`/cases/${deadline.case_id}`);
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    setDeleting(true);
    try {
      await onDelete(deadline.id);
      onClose();
    } catch (error) {
      console.error('Failed to delete deadline:', error);
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`p-4 border-b ${isOverdue ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200'}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0 pr-4">
              {isOverdue && (
                <div className="flex items-center gap-1 text-red-600 text-sm font-medium mb-1">
                  <AlertTriangle className="w-4 h-4" />
                  <span>OVERDUE</span>
                </div>
              )}
              <h2 className="text-lg font-semibold text-slate-800 break-words">
                {deadline.title}
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                {deadline.case_number} - {deadline.case_title}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-slate-200 transition-colors"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Status & Priority Badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getPriorityColor(deadline.priority)}`}>
              {deadline.priority}
            </span>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(deadline.status)}`}>
              {deadline.status}
            </span>
            {deadline.is_calculated && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                Auto-calculated
              </span>
            )}
            {deadline.is_manually_overridden && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-orange-100 text-orange-800">
                Manually adjusted
              </span>
            )}
          </div>

          {/* Date */}
          {deadline.deadline_date && (
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <Calendar className={`w-5 h-5 ${isOverdue ? 'text-red-500' : 'text-blue-500'}`} />
              <div>
                <p className="text-sm font-medium text-slate-500">Due Date</p>
                <p className={`text-base ${isOverdue ? 'text-red-600 font-medium' : 'text-slate-800'}`}>
                  {formatDate(deadline.deadline_date)}
                </p>
              </div>
            </div>
          )}

          {/* Description */}
          {deadline.description && (
            <div>
              <p className="text-sm font-medium text-slate-500 mb-1">Description</p>
              <p className="text-sm text-slate-700 whitespace-pre-line bg-slate-50 p-3 rounded-lg">
                {deadline.description}
              </p>
            </div>
          )}

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-4">
            {deadline.party_role && (
              <div className="flex items-start gap-2">
                <User className="w-4 h-4 text-slate-400 mt-0.5" />
                <div>
                  <p className="text-xs font-medium text-slate-500">Responsible Party</p>
                  <p className="text-sm text-slate-800">{deadline.party_role}</p>
                </div>
              </div>
            )}

            {deadline.deadline_type && (
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 text-slate-400 mt-0.5" />
                <div>
                  <p className="text-xs font-medium text-slate-500">Type</p>
                  <p className="text-sm text-slate-800 capitalize">{deadline.deadline_type}</p>
                </div>
              </div>
            )}
          </div>

          {/* Action Required */}
          {deadline.action_required && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm font-medium text-blue-800 mb-1">Action Required</p>
              <p className="text-sm text-blue-700">{deadline.action_required}</p>
            </div>
          )}

          {/* Applicable Rule */}
          {deadline.applicable_rule && (
            <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
              <div className="flex items-center gap-2 mb-1">
                <Scale className="w-4 h-4 text-purple-600" />
                <p className="text-sm font-medium text-purple-800">Applicable Rule</p>
              </div>
              <p className="text-sm text-purple-700">{deadline.applicable_rule}</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={goToCase}
              className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              <span className="text-sm font-medium">Go to Case</span>
            </button>

            {onDelete && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={deleting}
                className="flex items-center gap-2 px-4 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
                <span className="text-sm font-medium">Delete</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Close
            </button>

            {deadline.status === 'pending' && (
              <button
                onClick={handleComplete}
                disabled={completing}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-sm font-medium">
                  {completing ? 'Completing...' : 'Mark Complete'}
                </span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div
          className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-[60]"
          onClick={() => setShowDeleteConfirm(false)}
        >
          <div
            className="bg-white rounded-lg shadow-2xl max-w-md w-full mx-4 p-6"
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
                disabled={deleting}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
                <span className="text-sm font-medium">
                  {deleting ? 'Deleting...' : 'Delete Deadline'}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
