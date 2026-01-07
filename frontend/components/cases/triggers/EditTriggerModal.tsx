'use client';

import { useState, useEffect, useMemo } from 'react';
import { X, Calendar, AlertTriangle, ArrowRight, Loader2, CheckCircle2, Clock, Lock } from 'lucide-react';
import type { Trigger, Deadline } from '@/hooks/useCaseData';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';

interface EditTriggerModalProps {
  isOpen: boolean;
  trigger: Trigger | null;
  deadlines: Deadline[];
  onClose: () => void;
  onSuccess: () => void;
}

interface CascadePreview {
  deadline_id: string;
  title: string;
  current_date: string | null;
  new_date: string | null;
  days_changed: number;
  is_manually_overridden: boolean;
  will_update: boolean;
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

export default function EditTriggerModal({
  isOpen,
  trigger,
  deadlines,
  onClose,
  onSuccess,
}: EditTriggerModalProps) {
  const { showSuccess, showError } = useToast();

  const [newDate, setNewDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [preview, setPreview] = useState<CascadePreview[]>([]);

  // Get child deadlines that belong to this trigger
  const childDeadlines = useMemo(() => {
    if (!trigger) return [];
    return deadlines.filter(d => d.trigger_event === trigger.trigger_type);
  }, [trigger, deadlines]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen && trigger) {
      setNewDate(trigger.trigger_date.split('T')[0]);
      setPreview([]);
    }
  }, [isOpen, trigger]);

  // Generate cascade preview when date changes
  useEffect(() => {
    if (!trigger || !newDate) return;

    const currentDate = trigger.trigger_date.split('T')[0];
    if (newDate === currentDate) {
      setPreview([]);
      return;
    }

    const fetchPreview = async () => {
      setPreviewLoading(true);
      try {
        // Try to fetch preview from backend
        const response = await apiClient.get(
          `/api/v1/triggers/${trigger.id}/preview-cascade?new_date=${newDate}`
        );
        setPreview(response.data);
      } catch (err) {
        // Fallback: calculate preview client-side
        const currentTriggerDate = new Date(trigger.trigger_date);
        const newTriggerDate = new Date(newDate);
        const daysDiff = Math.round(
          (newTriggerDate.getTime() - currentTriggerDate.getTime()) / (1000 * 60 * 60 * 24)
        );

        const clientPreview: CascadePreview[] = childDeadlines
          .filter(d => d.status === 'pending')
          .map(d => {
            const currentDeadlineDate = d.deadline_date ? new Date(d.deadline_date) : null;
            const newDeadlineDate = currentDeadlineDate
              ? new Date(currentDeadlineDate.getTime() + daysDiff * 24 * 60 * 60 * 1000)
              : null;

            // Check if manually overridden (simplified check)
            const isManuallyOverridden = d.is_calculated === false;

            return {
              deadline_id: d.id,
              title: d.title,
              current_date: d.deadline_date?.split('T')[0] || null,
              new_date: newDeadlineDate?.toISOString().split('T')[0] || null,
              days_changed: daysDiff,
              is_manually_overridden: isManuallyOverridden,
              will_update: !isManuallyOverridden && d.status === 'pending',
            };
          });

        setPreview(clientPreview);
      } finally {
        setPreviewLoading(false);
      }
    };

    const debounce = setTimeout(fetchPreview, 300);
    return () => clearTimeout(debounce);
  }, [trigger, newDate, childDeadlines]);

  const handleSubmit = async () => {
    if (!trigger || !newDate) return;

    setLoading(true);
    try {
      await apiClient.patch(`/api/v1/triggers/${trigger.id}/update-date`, {
        new_date: newDate,
      });
      showSuccess('Trigger date updated');
      onSuccess();
      onClose();
    } catch (err: any) {
      showError(err.response?.data?.detail || 'Failed to update trigger');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'No date';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (!isOpen || !trigger) return null;

  const triggerLabel = TRIGGER_TYPE_LABELS[trigger.trigger_type] || trigger.trigger_type;
  const currentDate = trigger.trigger_date.split('T')[0];
  const hasChanges = newDate !== currentDate;
  const willUpdateCount = preview.filter(p => p.will_update).length;
  const lockedCount = preview.filter(p => p.is_manually_overridden).length;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-purple-50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">
                Edit Trigger: {trigger.title || triggerLabel}
              </h2>
              <p className="text-sm text-slate-600 mt-0.5">
                Update the trigger date to recalculate dependent deadlines
              </p>
            </div>
            <button
              onClick={onClose}
              disabled={loading}
              className="p-1.5 rounded-lg hover:bg-purple-200 transition-colors"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Date Input */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Current Date
              </label>
              <div className="flex items-center gap-2 px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-600">
                <Calendar className="w-4 h-4" />
                <span>{formatDate(currentDate)}</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                New Date
              </label>
              <input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
          </div>

          {/* Cascade Preview */}
          {hasChanges && (
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <div className="bg-slate-50 px-4 py-2 border-b border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span className="font-medium text-slate-700">
                      Cascade Preview
                    </span>
                  </div>
                  {previewLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                  ) : (
                    <span className="text-sm text-slate-500">
                      {willUpdateCount} will update
                      {lockedCount > 0 && `, ${lockedCount} locked`}
                    </span>
                  )}
                </div>
              </div>

              {preview.length > 0 ? (
                <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto">
                  {preview.map((item) => (
                    <div
                      key={item.deadline_id}
                      className={`px-4 py-2 flex items-center justify-between gap-4 ${
                        item.is_manually_overridden ? 'bg-slate-50 opacity-60' : ''
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        {item.will_update ? (
                          <Clock className="w-4 h-4 text-blue-500 flex-shrink-0" />
                        ) : item.is_manually_overridden ? (
                          <Lock className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                        )}
                        <span className="text-sm text-slate-700 truncate">
                          {item.title}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-sm flex-shrink-0">
                        <span className="text-slate-500">
                          {formatDate(item.current_date)}
                        </span>
                        {item.will_update && (
                          <>
                            <ArrowRight className="w-4 h-4 text-slate-400" />
                            <span className={`font-medium ${
                              item.days_changed > 0 ? 'text-amber-600' : 'text-blue-600'
                            }`}>
                              {formatDate(item.new_date)}
                            </span>
                            <span className="text-xs text-slate-400">
                              ({item.days_changed > 0 ? '+' : ''}{item.days_changed}d)
                            </span>
                          </>
                        )}
                        {item.is_manually_overridden && (
                          <span className="text-xs text-slate-400 italic">
                            Locked
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-4 py-8 text-center text-slate-500 text-sm">
                  No dependent deadlines to update
                </div>
              )}
            </div>
          )}

          {/* Warning for locked deadlines */}
          {lockedCount > 0 && (
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm">
              <Lock className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-amber-800">
                <span className="font-medium">{lockedCount} deadline{lockedCount !== 1 ? 's' : ''}</span> have been
                manually edited and will not be updated. This preserves your custom changes.
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !hasChanges}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Updating...
              </>
            ) : (
              <>
                Update {willUpdateCount > 0 ? `${willUpdateCount} Deadline${willUpdateCount !== 1 ? 's' : ''}` : 'Trigger'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
