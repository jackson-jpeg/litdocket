'use client';

import { useState } from 'react';
import { X, Clock, AlertCircle } from 'lucide-react';
import { validateSnoozeDays, formatValidationError } from '@/lib/validation';

interface SnoozeModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedCount: number;
  onSnooze: (days: number, reason: string) => Promise<void>;
}

export default function SnoozeModal({
  isOpen,
  onClose,
  selectedCount,
  onSnooze,
}: SnoozeModalProps) {
  const [days, setDays] = useState(7);
  const [reason, setReason] = useState('');
  const [processing, setProcessing] = useState(false);
  const [validationError, setValidationError] = useState<string>('');

  if (!isOpen) return null;

  const handleSnooze = async () => {
    // Validate input
    const validation = validateSnoozeDays(days);
    if (!validation.isValid) {
      setValidationError(formatValidationError(validation));
      return;
    }

    setProcessing(true);
    setValidationError('');

    try {
      await onSnooze(days, reason);
      // Reset form
      setDays(7);
      setReason('');
      onClose();
    } catch (error) {
      setValidationError('Failed to snooze deadlines. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const handleClose = () => {
    if (!processing) {
      setDays(7);
      setReason('');
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
          <h3 className="text-lg font-semibold text-slate-800">Snooze Deadlines</h3>
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
              Push deadlines forward by
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="365"
                value={days}
                onChange={(e) => {
                  const value = parseInt(e.target.value) || 1;
                  setDays(value);
                  setValidationError('');
                }}
                disabled={processing}
                className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:bg-slate-100"
              />
              <span className="text-sm text-slate-600 font-medium">days</span>
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
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why are you pushing these deadlines?"
              rows={3}
              disabled={processing}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none disabled:bg-slate-100"
            />
          </div>

          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-purple-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-purple-800">
                This will push {selectedCount} deadline{selectedCount !== 1 ? 's' : ''} forward by{' '}
                {days} day{days !== 1 ? 's' : ''}. The original dates will be preserved for audit
                purposes.
              </p>
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={handleSnooze}
              disabled={processing || days <= 0}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Clock className="w-4 h-4" />
              {processing
                ? 'Snoozing...'
                : `Snooze ${selectedCount} deadline${selectedCount !== 1 ? 's' : ''}`}
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
