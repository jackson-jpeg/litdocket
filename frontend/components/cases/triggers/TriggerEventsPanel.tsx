'use client';

import { useState } from 'react';
import { Zap, Plus, AlertTriangle } from 'lucide-react';
import type { Trigger, Deadline } from '@/hooks/useCaseData';
import TriggerCard from './TriggerCard';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';

interface TriggerEventsPanelProps {
  triggers: Trigger[];
  deadlines: Deadline[];
  caseId: string;
  onAddTrigger?: () => void;
  onEditTrigger?: (trigger: Trigger) => void;
  onRefresh?: () => void;
}

export default function TriggerEventsPanel({
  triggers,
  deadlines,
  caseId,
  onAddTrigger,
  onEditTrigger,
  onRefresh,
}: TriggerEventsPanelProps) {
  const { showSuccess, showError, showWarning } = useToast();
  const [recalculating, setRecalculating] = useState<string | null>(null);

  // Filter to active triggers only (not completed or cancelled)
  const activeTriggers = triggers.filter(
    t => t.status !== 'completed' && t.status !== 'cancelled'
  );

  // Calculate total stats
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const triggerDeadlines = deadlines.filter(d =>
    triggers.some(t => t.trigger_type === d.trigger_event)
  );
  const overdueFromTriggers = triggerDeadlines.filter(d =>
    d.status === 'pending' &&
    d.deadline_date &&
    new Date(d.deadline_date) < today
  ).length;

  const handleRecalculate = async (triggerId: string) => {
    setRecalculating(triggerId);
    try {
      await apiClient.patch(`/api/v1/triggers/${triggerId}/recalculate`);
      showSuccess('Deadlines recalculated');
      onRefresh?.();
    } catch (err) {
      showError('Failed to recalculate deadlines');
    } finally {
      setRecalculating(null);
    }
  };

  const handleDelete = async (triggerId: string) => {
    const trigger = triggers.find(t => t.id === triggerId);
    if (!trigger) return;

    const childCount = deadlines.filter(d => d.trigger_event === trigger.trigger_type).length;

    if (!confirm(
      `Delete trigger "${trigger.title}"?\n\n` +
      `This will also delete ${childCount} associated deadline${childCount !== 1 ? 's' : ''}.\n\n` +
      `This action cannot be undone.`
    )) {
      return;
    }

    try {
      await apiClient.delete(`/api/v1/triggers/${triggerId}`);
      showSuccess('Trigger deleted');
      onRefresh?.();
    } catch (err) {
      showError('Failed to delete trigger');
    }
  };

  const handleDeadlineClick = (deadline: Deadline) => {
    // For now, just log - in future could open deadline detail modal
    console.log('Clicked deadline:', deadline);
  };

  if (activeTriggers.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-slate-800">Trigger Events</h3>
          </div>
          {onAddTrigger && (
            <button
              onClick={onAddTrigger}
              className="flex items-center gap-1 px-3 py-1.5 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Trigger
            </button>
          )}
        </div>
        <div className="text-center py-8">
          <Zap className="w-12 h-12 text-slate-200 mx-auto mb-3" />
          <p className="text-sm text-slate-600 mb-2">No trigger events yet</p>
          <p className="text-xs text-slate-500 max-w-xs mx-auto">
            Create a trigger event to automatically generate deadlines based on important dates like trial date or complaint served.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Zap className="w-5 h-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-slate-800">
            Trigger Events
            <span className="text-sm font-normal text-slate-500 ml-2">
              ({activeTriggers.length})
            </span>
          </h3>
          {overdueFromTriggers > 0 && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full">
              <AlertTriangle className="w-3 h-3" />
              {overdueFromTriggers} overdue
            </span>
          )}
        </div>
        {onAddTrigger && (
          <button
            onClick={onAddTrigger}
            className="flex items-center gap-1 px-3 py-1.5 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Add Trigger</span>
          </button>
        )}
      </div>

      {/* Trigger Cards */}
      <div className="space-y-3">
        {activeTriggers
          .sort((a, b) => new Date(a.trigger_date).getTime() - new Date(b.trigger_date).getTime())
          .map(trigger => (
            <TriggerCard
              key={trigger.id}
              trigger={trigger}
              deadlines={deadlines}
              onEdit={onEditTrigger}
              onRecalculate={handleRecalculate}
              onDelete={handleDelete}
              onDeadlineClick={handleDeadlineClick}
            />
          ))}
      </div>
    </div>
  );
}
