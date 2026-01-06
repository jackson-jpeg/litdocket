'use client';

import { useState } from 'react';
import { X, Save } from 'lucide-react';
import { validateBulkEdit, formatValidationError } from '@/lib/validation';

interface BulkEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedCount: number;
  onSave: (priority: string, status: string) => Promise<void>;
}

export default function BulkEditModal({
  isOpen,
  onClose,
  selectedCount,
  onSave,
}: BulkEditModalProps) {
  const [priority, setPriority] = useState('');
  const [status, setStatus] = useState('');
  const [processing, setProcessing] = useState(false);
  const [validationError, setValidationError] = useState<string>('');

  if (!isOpen) return null;

  const handleSave = async () => {
    // Validate inputs
    const validation = validateBulkEdit(priority, status);
    if (!validation.isValid) {
      setValidationError(formatValidationError(validation));
      return;
    }

    setProcessing(true);
    setValidationError('');

    try {
      await onSave(priority, status);
      // Reset form
      setPriority('');
      setStatus('');
      onClose();
    } catch (error) {
      setValidationError('Failed to update deadlines. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const handleClose = () => {
    if (!processing) {
      setPriority('');
      setStatus('');
      setValidationError('');
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={handleClose}
    >
      <div
        className="bg-white rounded-xl p-6 max-w-md w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800">Bulk Edit Deadlines</h3>
          <button
            onClick={handleClose}
            disabled={processing}
            className="p-1 hover:bg-slate-100 rounded disabled:opacity-50"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {validationError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {validationError}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Priority
            </label>
            <select
              value={priority}
              onChange={(e) => {
                setPriority(e.target.value);
                setValidationError('');
              }}
              disabled={processing}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
            >
              <option value="">Don&apos;t change</option>
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
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setValidationError('');
              }}
              disabled={processing}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
            >
              <option value="">Don&apos;t change</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={handleSave}
              disabled={processing || (!priority && !status)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Save className="w-4 h-4" />
              {processing ? 'Updating...' : `Update ${selectedCount} deadline${selectedCount !== 1 ? 's' : ''}`}
            </button>
            <button
              onClick={handleClose}
              disabled={processing}
              className="px-4 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
