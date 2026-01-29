'use client';

import { useState } from 'react';
import {
  CheckSquare, Square, Trash2, Edit3, Clock, X, Save, Calendar as CalendarIcon
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface Deadline {
  id: string;
  title: string;
  deadline_date: string | null;
  priority: string;
  status: string;
  description?: string;
  applicable_rule?: string;
  is_calculated?: boolean;
}

interface DeadlineActionsProps {
  deadlines: Deadline[];
  onDeadlinesUpdated: () => void;
}

export default function DeadlineActions({ deadlines, onDeadlinesUpdated }: DeadlineActionsProps) {
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkEditOpen, setBulkEditOpen] = useState(false);
  const [snoozeOpen, setSnoozeOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // Bulk edit form state
  const [bulkPriority, setBulkPriority] = useState<string>('');
  const [bulkStatus, setBulkStatus] = useState<string>('');

  // Snooze form state
  const [snoozeDays, setSnoozeDays] = useState<number>(7);
  const [snoozeReason, setSnoozeReason] = useState<string>('');

  const toggleSelection = (id: string) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  const selectAll = () => {
    setSelectedIds(new Set(deadlines.map(d => d.id)));
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
    setSelectionMode(false);
  };

  const handleBulkComplete = async () => {
    if (selectedIds.size === 0) return;

    setLoading(true);
    try {
      await Promise.all(
        Array.from(selectedIds).map(id =>
          apiClient.patch(`/api/v1/deadlines/${id}/status?status=completed`)
        )
      );
      onDeadlinesUpdated();
      clearSelection();
    } catch (err) {
      console.error('Failed to complete deadlines:', err);
      alert('Failed to complete deadlines');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} deadline(s)? This cannot be undone.`)) return;

    setLoading(true);
    try {
      await Promise.all(
        Array.from(selectedIds).map(id =>
          apiClient.delete(`/api/v1/deadlines/${id}`)
        )
      );
      onDeadlinesUpdated();
      clearSelection();
    } catch (err) {
      console.error('Failed to delete deadlines:', err);
      alert('Failed to delete deadlines');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkEdit = async () => {
    if (selectedIds.size === 0 || (!bulkPriority && !bulkStatus)) return;

    setLoading(true);
    try {
      // Note: This would require a bulk update endpoint in the backend
      // For now, we'll do individual updates
      const promises = Array.from(selectedIds).map(async (id) => {
        const updates: any = {};
        if (bulkPriority) updates.priority = bulkPriority;
        if (bulkStatus) {
          await apiClient.patch(`/api/v1/deadlines/${id}/status?status=${bulkStatus}`);
        }
        // Additional updates would go here if backend supports PATCH for other fields
      });

      await Promise.all(promises);
      onDeadlinesUpdated();
      clearSelection();
      setBulkEditOpen(false);
      setBulkPriority('');
      setBulkStatus('');
    } catch (err) {
      console.error('Failed to update deadlines:', err);
      alert('Failed to update deadlines');
    } finally {
      setLoading(false);
    }
  };

  const handleSnooze = async () => {
    if (selectedIds.size === 0 || snoozeDays <= 0) return;

    setLoading(true);
    try {
      // Call snooze endpoint for each selected deadline
      const results = await Promise.all(
        Array.from(selectedIds).map(async (id) => {
          const deadline = deadlines.find(d => d.id === id);
          if (!deadline?.deadline_date) return null;

          const response = await apiClient.post(`/api/v1/deadlines/${id}/snooze`, {
            days: snoozeDays,
            reason: snoozeReason || undefined
          });
          return response.data;
        })
      );

      const successCount = results.filter(r => r !== null).length;
      onDeadlinesUpdated();
      clearSelection();
      setSnoozeOpen(false);
      setSnoozeDays(7);
      setSnoozeReason('');
    } catch (err) {
      console.error('Failed to snooze deadlines:', err);
      alert('Failed to snooze deadlines. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderToolbar = () => {
    if (!selectionMode) {
      return (
        <button
          onClick={() => setSelectionMode(true)}
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors border border-slate-300"
        >
          <CheckSquare className="w-4 h-4" />
          Select
        </button>
      );
    }

    return (
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-medium text-slate-700">
          {selectedIds.size} selected
        </span>
        <button
          onClick={selectAll}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          Select All
        </button>
        <div className="h-4 w-px bg-slate-300" />
        <button
          onClick={handleBulkComplete}
          disabled={loading || selectedIds.size === 0}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded border border-green-200 disabled:opacity-50"
        >
          <CheckSquare className="w-3 h-3" />
          Complete
        </button>
        <button
          onClick={() => setBulkEditOpen(true)}
          disabled={loading || selectedIds.size === 0}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded border border-blue-200 disabled:opacity-50"
        >
          <Edit3 className="w-3 h-3" />
          Edit
        </button>
        <button
          onClick={() => setSnoozeOpen(true)}
          disabled={loading || selectedIds.size === 0}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 rounded border border-purple-200 disabled:opacity-50"
        >
          <Clock className="w-3 h-3" />
          Snooze
        </button>
        <button
          onClick={handleBulkDelete}
          disabled={loading || selectedIds.size === 0}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded border border-red-200 disabled:opacity-50"
        >
          <Trash2 className="w-3 h-3" />
          Delete
        </button>
        <button
          onClick={clearSelection}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded border border-slate-300"
        >
          <X className="w-3 h-3" />
          Cancel
        </button>
      </div>
    );
  };

  const renderCheckbox = (deadline: Deadline) => {
    if (!selectionMode) return null;

    const isSelected = selectedIds.has(deadline.id);
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          toggleSelection(deadline.id);
        }}
        className="flex-shrink-0"
      >
        {isSelected ? (
          <CheckSquare className="w-5 h-5 text-blue-600" />
        ) : (
          <Square className="w-5 h-5 text-slate-400 hover:text-slate-600" />
        )}
      </button>
    );
  };

  return (
    <>
      {/* Toolbar */}
      <div className="mb-4">
        {renderToolbar()}
      </div>

      {/* Export functions for use in parent component */}
      <div style={{ display: 'none' }}>
        {/* This component exports its state via props */}
      </div>

      {/* Bulk Edit Modal */}
      {bulkEditOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setBulkEditOpen(false)}>
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-800">Bulk Edit Deadlines</h3>
              <button onClick={() => setBulkEditOpen(false)} className="p-1 hover:bg-slate-100 rounded">
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Priority
                </label>
                <select
                  value={bulkPriority}
                  onChange={(e) => setBulkPriority(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Don't change</option>
                  <option value="informational">Informational</option>
                  <option value="standard">Standard</option>
                  <option value="important">Important</option>
                  <option value="critical">Critical</option>
                  <option value="fatal">Fatal</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Status
                </label>
                <select
                  value={bulkStatus}
                  onChange={(e) => setBulkStatus(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Don't change</option>
                  <option value="pending">Pending</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleBulkEdit}
                  disabled={loading || (!bulkPriority && !bulkStatus)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Save className="w-4 h-4" />
                  Update {selectedIds.size} deadline{selectedIds.size !== 1 ? 's' : ''}
                </button>
                <button
                  onClick={() => setBulkEditOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Snooze Modal */}
      {snoozeOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setSnoozeOpen(false)}>
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-800">Snooze Deadlines</h3>
              <button onClick={() => setSnoozeOpen(false)} className="p-1 hover:bg-slate-100 rounded">
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Push deadlines forward by
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={snoozeDays}
                    onChange={(e) => setSnoozeDays(parseInt(e.target.value) || 1)}
                    className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <span className="text-sm text-slate-600">days</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Common: 7 (1 week), 14 (2 weeks), 30 (1 month)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Reason (optional)
                </label>
                <textarea
                  value={snoozeReason}
                  onChange={(e) => setSnoozeReason(e.target.value)}
                  placeholder="Why are you pushing these deadlines?"
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                />
              </div>

              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <p className="text-xs text-purple-800">
                  <strong>Note:</strong> This will push {selectedIds.size} deadline{selectedIds.size !== 1 ? 's' : ''} forward by {snoozeDays} day{snoozeDays !== 1 ? 's' : ''}. The original dates will be preserved for audit purposes.
                </p>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleSnooze}
                  disabled={loading || snoozeDays <= 0}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Clock className="w-4 h-4" />
                  Snooze {selectedIds.size} deadline{selectedIds.size !== 1 ? 's' : ''}
                </button>
                <button
                  onClick={() => setSnoozeOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hidden state export for parent component */}
      <div data-selection-mode={selectionMode} data-render-checkbox={(deadline: Deadline) => renderCheckbox(deadline)} />
    </>
  );
}

// Export utilities for parent component to use
export const useDeadlineSelection = () => {
  return {
    renderCheckbox: (deadline: Deadline, selectionMode: boolean, selectedIds: Set<string>, toggleSelection: (id: string) => void) => {
      if (!selectionMode) return null;

      const isSelected = selectedIds.has(deadline.id);
      return (
        <button
          onClick={(e) => {
            e.stopPropagation();
            toggleSelection(deadline.id);
          }}
          className="flex-shrink-0"
        >
          {isSelected ? (
            <CheckSquare className="w-5 h-5 text-blue-600" />
          ) : (
            <Square className="w-5 h-5 text-slate-400 hover:text-slate-600" />
          )}
        </button>
      );
    }
  };
};
