'use client';

/**
 * DeadlineDetailModal - Sovereign Design System
 *
 * Full detail view and edit modal for deadlines.
 * Dense data display with inline editing capabilities.
 *
 * Features:
 * - View all deadline details
 * - Edit date, notes, status
 * - Mark complete/incomplete
 * - Delete deadline
 * - View trigger chain info
 */

import { useState, useEffect } from 'react';
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
} from 'lucide-react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';
import { formatDeadlineDate, formatDateTime } from '@/lib/formatters';
import apiClient from '@/lib/api-client';

interface DeadlineDetailModalProps {
  isOpen: boolean;
  deadline: Deadline | null;
  triggers: Trigger[];
  onClose: () => void;
  onUpdate: () => void;
  onComplete: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function DeadlineDetailModal({
  isOpen,
  deadline,
  triggers,
  onClose,
  onUpdate,
  onComplete,
  onDelete,
}: DeadlineDetailModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
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

  const getPriorityColor = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case 'fatal': return 'text-red-600 bg-red-100 border-red-300';
      case 'critical': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'high':
      case 'important': return 'text-amber-600 bg-amber-50 border-amber-200';
      case 'standard': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-100 border-gray-200';
    }
  };

  const getStatusColor = () => {
    if (isCompleted) return 'text-green-600 bg-green-100 border-green-300';
    if (isCancelled) return 'text-gray-500 bg-gray-100 border-gray-300';
    if (isOverdue) return 'text-red-600 bg-red-100 border-red-300';
    return 'text-blue-600 bg-blue-50 border-blue-200';
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
      onUpdate();
    } catch (err) {
      console.error('Failed to update deadline:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = () => {
    if (confirm(`Delete deadline "${deadline.title}"? This action cannot be undone.`)) {
      onDelete(deadline.id);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="case-deadline-detail-title"
        className="bg-white w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-xl border border-gray-300"
      >
        {/* Header */}
        <div className="bg-slate-800 text-white px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calendar className="w-5 h-5 text-cyan-400" />
            <span id="case-deadline-detail-title" className="font-mono text-sm uppercase tracking-wide">Deadline Details</span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close deadline details"
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
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

          {/* Main Content */}
          <div className="p-4 space-y-4">
            {/* Title */}
            <div>
              <label className="text-xs text-gray-500 uppercase font-mono mb-1 block">Event Title</label>
              {isEditing ? (
                <input
                  type="text"
                  value={editedDeadline.title || ''}
                  onChange={(e) => setEditedDeadline(prev => ({ ...prev, title: e.target.value }))}
                  className="w-full border border-gray-300 px-3 py-2 text-lg font-serif focus:outline-none focus:border-blue-500"
                />
              ) : (
                <p className={`text-lg font-serif ${isCompleted ? 'line-through text-gray-500' : ''}`}>
                  {deadline.title}
                </p>
              )}
            </div>

            {/* Date & Priority Row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 uppercase font-mono mb-1 block">
                  <Calendar className="w-3 h-3 inline mr-1" />
                  Due Date
                </label>
                {isEditing ? (
                  <input
                    type="date"
                    value={editedDeadline.deadline_date || ''}
                    onChange={(e) => setEditedDeadline(prev => ({ ...prev, deadline_date: e.target.value }))}
                    className="w-full border border-gray-300 px-3 py-2 font-mono focus:outline-none focus:border-blue-500"
                  />
                ) : (
                  <p className="font-mono text-lg">
                    {deadline.deadline_date ? formatDeadlineDate(deadline.deadline_date) : 'No date set'}
                  </p>
                )}
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase font-mono mb-1 block">
                  <AlertTriangle className="w-3 h-3 inline mr-1" />
                  Priority
                </label>
                {isEditing ? (
                  <select
                    value={editedDeadline.priority || 'standard'}
                    onChange={(e) => setEditedDeadline(prev => ({ ...prev, priority: e.target.value as 'informational' | 'standard' | 'important' | 'critical' | 'fatal' }))}
                    className="w-full border border-gray-300 px-3 py-2 font-mono focus:outline-none focus:border-blue-500"
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
                    deadline.priority === 'important' ? 'text-amber-600' : ''
                  }`}>
                    {deadline.priority?.toUpperCase() || 'STANDARD'}
                  </p>
                )}
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="text-xs text-gray-500 uppercase font-mono mb-1 block">
                <FileText className="w-3 h-3 inline mr-1" />
                Description / Notes
              </label>
              {isEditing ? (
                <textarea
                  value={editedDeadline.description || ''}
                  onChange={(e) => setEditedDeadline(prev => ({ ...prev, description: e.target.value }))}
                  rows={3}
                  placeholder="Add notes about this deadline..."
                  className="w-full border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                />
              ) : (
                <p className="text-sm text-gray-700 bg-gray-50 p-3 border border-gray-200 min-h-[60px]">
                  {deadline.description || 'No description'}
                </p>
              )}
            </div>

            {/* Action Required */}
            <div>
              <label className="text-xs text-gray-500 uppercase font-mono mb-1 block">
                <User className="w-3 h-3 inline mr-1" />
                Action Required
              </label>
              {isEditing ? (
                <input
                  type="text"
                  value={editedDeadline.action_required || ''}
                  onChange={(e) => setEditedDeadline(prev => ({ ...prev, action_required: e.target.value }))}
                  placeholder="What action is needed?"
                  className="w-full border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                />
              ) : (
                <p className="text-sm">
                  {deadline.action_required || 'Not specified'}
                </p>
              )}
            </div>

            {/* Rule/Authority */}
            {deadline.applicable_rule && (
              <div>
                <label className="text-xs text-gray-500 uppercase font-mono mb-1 block">
                  <Scale className="w-3 h-3 inline mr-1" />
                  Legal Authority
                </label>
                <p className="font-mono text-sm bg-blue-50 border border-blue-200 px-3 py-2">
                  {deadline.applicable_rule}
                </p>
              </div>
            )}

            {/* Calculation Basis */}
            {deadline.calculation_basis && (
              <div>
                <label className="text-xs text-gray-500 uppercase font-mono mb-1 block">
                  <Clock className="w-3 h-3 inline mr-1" />
                  Calculation
                </label>
                <p className="text-sm text-gray-600">
                  {deadline.calculation_basis}
                </p>
              </div>
            )}

            {/* Trigger Chain */}
            {parentTrigger && (
              <div className="border-t border-gray-200 pt-4 mt-4">
                <label className="text-xs text-gray-500 uppercase font-mono mb-2 block">
                  <Link className="w-3 h-3 inline mr-1" />
                  Trigger Chain
                </label>
                <div className="bg-cyan-50 border border-cyan-200 p-3">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-cyan-600 font-mono">FROM:</span>
                    <span className="font-medium">{parentTrigger.title}</span>
                  </div>
                  {parentTrigger.trigger_date && (
                    <div className="text-xs text-gray-500 mt-1 font-mono">
                      Trigger Date: {formatDeadlineDate(parentTrigger.trigger_date)}
                    </div>
                  )}
                  {deadline.is_calculated && (
                    <div className="text-xs text-cyan-600 mt-1">
                      Auto-calculated from event
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Service Method */}
            {deadline.service_method && (
              <div>
                <label className="text-xs text-gray-500 uppercase font-mono mb-1 block">
                  Service Method
                </label>
                <p className="text-sm capitalize">
                  {deadline.service_method === 'electronic' && '@ '}
                  {deadline.service_method.replace('_', ' ')}
                </p>
              </div>
            )}

            {/* Metadata */}
            <div className="border-t border-gray-200 pt-4 mt-4 text-xs text-gray-400 font-mono">
              <div className="flex justify-between">
                <span>Created: {deadline.created_at ? formatDateTime(deadline.created_at) : 'N/A'}</span>
                <span>ID: {deadline.id.slice(0, 8)}...</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="border-t border-gray-300 px-4 py-3 bg-gray-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {!isCompleted && !isCancelled && (
              <button
                onClick={() => {
                  onComplete(deadline.id);
                  onClose();
                }}
                className="px-4 py-2 bg-green-600 text-white font-mono text-sm hover:bg-green-700 transition-colors flex items-center gap-2"
              >
                <CheckCircle className="w-4 h-4" />
                Mark Complete
              </button>
            )}
            <button
              onClick={handleDelete}
              className="px-4 py-2 border border-red-300 text-red-600 font-mono text-sm hover:bg-red-50 transition-colors flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
          <div className="flex items-center gap-2">
            {isEditing ? (
              <>
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-600 font-mono text-sm hover:bg-gray-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-4 py-2 bg-blue-600 text-white font-mono text-sm hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 bg-slate-700 text-white font-mono text-sm hover:bg-slate-600 transition-colors flex items-center gap-2"
              >
                <Edit2 className="w-4 h-4" />
                Edit
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
