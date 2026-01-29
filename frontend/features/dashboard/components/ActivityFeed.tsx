'use client';

import { FileText, Calendar, Zap, CheckCircle, Upload, Clock } from 'lucide-react';

interface Activity {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  case_number?: string;
  case_id?: string;
}

interface ActivityFeedProps {
  activities: Activity[];
  onCaseClick?: (caseId: string) => void;
}

export default function ActivityFeed({ activities, onCaseClick }: ActivityFeedProps) {
  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'document_uploaded':
        return <Upload className="w-5 h-5 text-blue-600" />;
      case 'deadline_created':
        return <Calendar className="w-5 h-5 text-green-600" />;
      case 'trigger_created':
        return <Zap className="w-5 h-5 text-purple-600" />;
      case 'deadline_completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'case_created':
        return <FileText className="w-5 h-5 text-blue-600" />;
      default:
        return <Clock className="w-5 h-5 text-slate-600" />;
    }
  };

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'document_uploaded':
        return 'bg-blue-50 border-blue-200';
      case 'deadline_created':
        return 'bg-green-50 border-green-200';
      case 'trigger_created':
        return 'bg-purple-50 border-purple-200';
      case 'deadline_completed':
        return 'bg-green-50 border-green-200';
      case 'case_created':
        return 'bg-blue-50 border-blue-200';
      default:
        return 'bg-slate-50 border-slate-200';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <Clock className="w-5 h-5 text-blue-600" />
        Recent Activity
      </h3>

      {activities.length === 0 ? (
        <div className="text-center py-12">
          <Clock className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">No recent activity</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {activities.map((activity) => (
            <div
              key={activity.id}
              className={`border rounded-lg p-3 transition-all hover:shadow-md ${getActivityColor(activity.type)}`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {getActivityIcon(activity.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-900">{activity.description}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-500">{formatTimestamp(activity.timestamp)}</span>
                    {activity.case_number && (
                      <>
                        <span className="text-xs text-slate-400">•</span>
                        <button
                          onClick={() => activity.case_id && onCaseClick?.(activity.case_id)}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          {activity.case_number}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
