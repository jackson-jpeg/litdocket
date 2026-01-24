'use client';

import { useState } from 'react';
import {
  PlusIcon,
  TrashIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';

interface Deadline {
  id: string;
  title: string;
  offset_days: number;
  offset_direction: 'before' | 'after';
  priority: 'FATAL' | 'CRITICAL' | 'IMPORTANT' | 'STANDARD' | 'INFORMATIONAL';
  description?: string;
  applicable_rule?: string;
  add_service_days?: boolean;
}

interface TimelineRuleBuilderProps {
  triggerType: string;
  onChange?: (deadlines: Deadline[]) => void;
}

export default function TimelineRuleBuilder({
  triggerType,
  onChange
}: TimelineRuleBuilderProps) {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);

  const addDeadline = (deadline: Deadline) => {
    const updated = [...deadlines, deadline];
    setDeadlines(updated);
    onChange?.(updated);
    setShowAddForm(false);
  };

  const removeDeadline = (id: string) => {
    const updated = deadlines.filter(d => d.id !== id);
    setDeadlines(updated);
    onChange?.(updated);
  };

  const updateDeadline = (id: string, updates: Partial<Deadline>) => {
    const updated = deadlines.map(d => d.id === id ? { ...d, ...updates } : d);
    setDeadlines(updated);
    onChange?.(updated);
  };

  // Sort deadlines by absolute position on timeline
  const sortedDeadlines = [...deadlines].sort((a, b) => {
    const aPos = a.offset_direction === 'before' ? -a.offset_days : a.offset_days;
    const bPos = b.offset_direction === 'before' ? -b.offset_days : b.offset_days;
    return aPos - bPos;
  });

  const priorityColors = {
    FATAL: 'bg-red-600 text-white',
    CRITICAL: 'bg-orange-600 text-white',
    IMPORTANT: 'bg-yellow-600 text-white',
    STANDARD: 'bg-blue-600 text-white',
    INFORMATIONAL: 'bg-gray-600 text-white'
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Deadline Timeline</h3>
          <p className="text-sm text-gray-500 mt-1">
            Add deadlines relative to trigger: <span className="font-medium">{triggerType}</span>
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center gap-2"
        >
          <PlusIcon className="h-5 w-5" />
          Add Deadline
        </button>
      </div>

      {/* Timeline Visualization */}
      <div className="relative">
        {/* Timeline Line */}
        <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-gray-200 -translate-x-1/2" />

        {/* Trigger Point */}
        <div className="relative mb-8">
          <div className="flex items-center justify-center">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-lg shadow-lg font-semibold">
              {triggerType}
              <div className="text-xs text-blue-100 mt-1">Day 0 (Trigger)</div>
            </div>
          </div>
        </div>

        {/* Before Trigger Deadlines */}
        {sortedDeadlines.filter(d => d.offset_direction === 'before').map((deadline, idx) => (
          <TimelineDeadlineItem
            key={deadline.id}
            deadline={deadline}
            position="before"
            onUpdate={(updates) => updateDeadline(deadline.id, updates)}
            onRemove={() => removeDeadline(deadline.id)}
            priorityColors={priorityColors}
          />
        ))}

        {/* After Trigger Deadlines */}
        {sortedDeadlines.filter(d => d.offset_direction === 'after').map((deadline, idx) => (
          <TimelineDeadlineItem
            key={deadline.id}
            deadline={deadline}
            position="after"
            onUpdate={(updates) => updateDeadline(deadline.id, updates)}
            onRemove={() => removeDeadline(deadline.id)}
            priorityColors={priorityColors}
          />
        ))}
      </div>

      {/* Empty State */}
      {deadlines.length === 0 && (
        <div className="text-center py-16 border-2 border-dashed border-gray-200 rounded-lg">
          <ClockIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 mb-4">No deadlines added yet</p>
          <button
            onClick={() => setShowAddForm(true)}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            Add your first deadline
          </button>
        </div>
      )}

      {/* Add Deadline Form Modal */}
      {showAddForm && (
        <AddDeadlineForm
          triggerType={triggerType}
          onAdd={addDeadline}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {/* Summary Stats */}
      {deadlines.length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-gray-900">{deadlines.length}</p>
              <p className="text-sm text-gray-500">Total Deadlines</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">
                {deadlines.filter(d => d.priority === 'FATAL').length}
              </p>
              <p className="text-sm text-gray-500">Fatal</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-600">
                {deadlines.filter(d => d.priority === 'CRITICAL').length}
              </p>
              <p className="text-sm text-gray-500">Critical</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// TIMELINE DEADLINE ITEM
// ============================================

function TimelineDeadlineItem({
  deadline,
  position,
  onUpdate,
  onRemove,
  priorityColors
}: {
  deadline: Deadline;
  position: 'before' | 'after';
  onUpdate: (updates: Partial<Deadline>) => void;
  onRemove: () => void;
  priorityColors: any;
}) {
  const isLeft = position === 'before';

  return (
    <div className={`relative flex items-center mb-6 ${isLeft ? 'flex-row-reverse' : ''}`}>
      {/* Timeline Dot */}
      <div className="absolute left-1/2 -translate-x-1/2 z-10">
        <div className={`w-4 h-4 rounded-full border-4 border-white ${
          deadline.priority === 'FATAL' ? 'bg-red-600' :
          deadline.priority === 'CRITICAL' ? 'bg-orange-600' :
          deadline.priority === 'IMPORTANT' ? 'bg-yellow-600' :
          'bg-blue-600'
        }`} />
      </div>

      {/* Card */}
      <div className={`w-5/12 ${isLeft ? 'text-right' : ''}`}>
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className={`flex-1 ${isLeft ? 'text-right' : ''}`}>
              <h4 className="font-semibold text-gray-900">{deadline.title}</h4>
              <p className="text-xs text-gray-500 mt-1">
                {deadline.offset_days} days {position}
                {deadline.add_service_days && ' + service'}
              </p>
            </div>
            <button
              onClick={onRemove}
              className="text-red-600 hover:text-red-700"
            >
              <TrashIcon className="h-4 w-4" />
            </button>
          </div>

          <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${priorityColors[deadline.priority]}`}>
            {deadline.priority}
          </span>

          {deadline.applicable_rule && (
            <p className="text-xs text-gray-600 mt-2 italic">
              {deadline.applicable_rule}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================
// ADD DEADLINE FORM
// ============================================

function AddDeadlineForm({
  triggerType,
  onAdd,
  onCancel
}: {
  triggerType: string;
  onAdd: (deadline: Deadline) => void;
  onCancel: () => void;
}) {
  const [formData, setFormData] = useState({
    title: '',
    offset_days: 30,
    offset_direction: 'before' as 'before' | 'after',
    priority: 'IMPORTANT' as Deadline['priority'],
    description: '',
    applicable_rule: '',
    add_service_days: false
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({
      id: `deadline-${Date.now()}`,
      ...formData
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Add Deadline</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Deadline Title *
            </label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="Answer to Complaint"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Offset Days *
              </label>
              <input
                type="number"
                required
                min="0"
                value={formData.offset_days}
                onChange={(e) => setFormData({ ...formData, offset_days: parseInt(e.target.value) })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Direction *
              </label>
              <select
                value={formData.offset_direction}
                onChange={(e) => setFormData({ ...formData, offset_direction: e.target.value as 'before' | 'after' })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="before">Before Trigger</option>
                <option value="after">After Trigger</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Priority *
            </label>
            <select
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: e.target.value as Deadline['priority'] })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="FATAL">FATAL - Jurisdictional deadline</option>
              <option value="CRITICAL">CRITICAL - Court-ordered</option>
              <option value="IMPORTANT">IMPORTANT - Procedural</option>
              <option value="STANDARD">STANDARD - Best practice</option>
              <option value="INFORMATIONAL">INFORMATIONAL - Reminder</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rule Citation
            </label>
            <input
              type="text"
              value={formData.applicable_rule}
              onChange={(e) => setFormData({ ...formData, applicable_rule: e.target.value })}
              placeholder="Fla. R. Civ. P. 1.140(a)(1)"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              rows={2}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Optional notes about this deadline..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="add_service_days"
              checked={formData.add_service_days}
              onChange={(e) => setFormData({ ...formData, add_service_days: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="add_service_days" className="ml-2 text-sm text-gray-700">
              Add service days (extends by 5 days for mail service)
            </label>
          </div>

          <div className="flex gap-4 pt-4 border-t border-gray-200">
            <button
              type="submit"
              className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              Add Deadline
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
