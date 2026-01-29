'use client';

import { useState } from 'react';
import { Zap, Plus, AlertTriangle, RefreshCw } from 'lucide-react';
import type { Trigger } from '@/hooks/useCaseData';
import TriggerCard from './TriggerCard';
import apiClient from '@/lib/api-client';
import { useToast } from '@/components/Toast';

interface TriggerEventsPanelProps {
  triggers: Trigger[];
  caseId: string;
  onAddTrigger?: () => void;
  onEditTrigger?: (trigger: Trigger) => void;
  onRefresh?: () => void;
}

export default function TriggerEventsPanel({
  triggers,
  caseId,
  onAddTrigger,
  onEditTrigger,
  onRefresh,
}: TriggerEventsPanelProps) {
  const { showSuccess, showError } = useToast();
  const [recalculating, setRecalculating] = useState<string | null>(null);

  // Filter active
  const activeTriggers = triggers.filter(
    t => t.status !== 'completed' && t.status !== 'cancelled'
  );

  const handleRecalculate = async (triggerId: string) => {
    setRecalculating(triggerId);
    try {
      await apiClient.patch(`/api/v1/triggers/${triggerId}/recalculate`);
      showSuccess('Deadlines recalculated');
      onRefresh?.();
    } catch (err) {
      showError('Failed to recalculate');
    } finally {
      setRecalculating(null);
    }
  };

  const handleDelete = async (triggerId: string) => {
    if (!confirm('CONFIRM DELETION: This will purge all associated deadlines.')) return;
    try {
      await apiClient.delete(`/api/v1/triggers/${triggerId}`);
      showSuccess('Trigger deleted');
      onRefresh?.();
    } catch (err) {
      showError('Failed to delete trigger');
    }
  };

  // SOVEREIGN UI: Empty State
  if (activeTriggers.length === 0) {
    return (
      <div className="border border-slate-300 bg-slate-50 p-8 text-center">
        <div className="font-mono text-xs text-slate-500 mb-2 uppercase tracking-widest">System Status</div>
        <h3 className="text-slate-900 font-serif text-lg mb-4">No Active Triggers</h3>
        {onAddTrigger && (
          <button
            onClick={onAddTrigger}
            className="bg-[#2C3E50] text-white px-4 py-2 hover:bg-[#1A1A1A] transition-colors text-sm font-medium flex items-center gap-2 mx-auto uppercase tracking-wide"
          >
            <Plus className="w-4 h-4" />
            Initialize Trigger
          </button>
        )}
      </div>
    );
  }

  // SOVEREIGN UI: Main Panel
  return (
    <div className="border border-slate-300 bg-white">
      {/* Control Header */}
      <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-slate-600" />
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Active Triggers ({activeTriggers.length})
          </span>
        </div>
        {onAddTrigger && (
          <button
            onClick={onAddTrigger}
            className="text-xs font-bold text-blue-700 hover:text-blue-900 hover:underline flex items-center gap-1 uppercase tracking-wide"
          >
            <Plus className="w-3 h-3" />
            Add Event
          </button>
        )}
      </div>

      {/* Trigger List - No Spacing, Strict Dividers */}
      <div className="divide-y divide-slate-200">
        {activeTriggers
          .sort((a, b) => new Date(a.trigger_date).getTime() - new Date(b.trigger_date).getTime())
          .map(trigger => (
            <TriggerCard
              key={trigger.id}
              trigger={trigger}
              onEdit={onEditTrigger}
              onRecalculate={handleRecalculate}
              onDelete={handleDelete}
              isRecalculating={recalculating === trigger.id}
            />
          ))}
      </div>
    </div>
  );
}
