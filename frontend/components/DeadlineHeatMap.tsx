'use client';

import { AlertTriangle, Clock, Calendar } from 'lucide-react';

interface HeatMapDeadline {
  id: string;
  case_id: string;
  title: string;
  deadline_date: string;
  days_until: number;
  action_required: string;
  case_title: string;
}

interface HeatMapMatrix {
  fatal: { today: HeatMapDeadline[]; '3_day': HeatMapDeadline[]; '7_day': HeatMapDeadline[]; '30_day': HeatMapDeadline[] };
  critical: { today: HeatMapDeadline[]; '3_day': HeatMapDeadline[]; '7_day': HeatMapDeadline[]; '30_day': HeatMapDeadline[] };
  important: { today: HeatMapDeadline[]; '3_day': HeatMapDeadline[]; '7_day': HeatMapDeadline[]; '30_day': HeatMapDeadline[] };
  standard: { today: HeatMapDeadline[]; '3_day': HeatMapDeadline[]; '7_day': HeatMapDeadline[]; '30_day': HeatMapDeadline[] };
  informational: { today: HeatMapDeadline[]; '3_day': HeatMapDeadline[]; '7_day': HeatMapDeadline[]; '30_day': HeatMapDeadline[] };
}

interface HeatMapData {
  matrix: HeatMapMatrix;
  summary: {
    total_deadlines: number;
    by_fatality: {
      fatal: number;
      critical: number;
      important: number;
      standard: number;
      informational: number;
    };
    by_urgency: {
      today: number;
      '3_day': number;
      '7_day': number;
      '30_day': number;
    };
  };
}

interface DeadlineHeatMapProps {
  heatMapData: HeatMapData;
  onCaseClick?: (caseId: string) => void;
}

export default function DeadlineHeatMap({ heatMapData, onCaseClick }: DeadlineHeatMapProps) {
  const { matrix, summary } = heatMapData;

  const fatalityLevels = [
    { key: 'fatal', label: 'Fatal', color: 'bg-red-600', textColor: 'text-white' },
    { key: 'critical', label: 'Critical', color: 'bg-orange-500', textColor: 'text-white' },
    { key: 'important', label: 'Important', color: 'bg-yellow-500', textColor: 'text-white' },
    { key: 'standard', label: 'Standard', color: 'bg-blue-500', textColor: 'text-white' },
    { key: 'informational', label: 'Info', color: 'bg-slate-400', textColor: 'text-white' }
  ];

  const urgencyBuckets = [
    { key: 'today', label: 'Today', icon: AlertTriangle, subtext: '0 days' },
    { key: '3_day', label: '3-Day', icon: Clock, subtext: '1-3 days' },
    { key: '7_day', label: '7-Day', icon: Calendar, subtext: '4-7 days' },
    { key: '30_day', label: '30-Day', icon: Calendar, subtext: '8-30 days' }
  ];

  const getCellColor = (fatalityKey: string, count: number) => {
    if (count === 0) return 'bg-slate-50 border-slate-200';

    switch (fatalityKey) {
      case 'fatal':
        return count > 5 ? 'bg-red-600 border-red-700' : count > 2 ? 'bg-red-500 border-red-600' : 'bg-red-400 border-red-500';
      case 'critical':
        return count > 5 ? 'bg-orange-600 border-orange-700' : count > 2 ? 'bg-orange-500 border-orange-600' : 'bg-orange-400 border-orange-500';
      case 'important':
        return count > 5 ? 'bg-yellow-600 border-yellow-700' : count > 2 ? 'bg-yellow-500 border-yellow-600' : 'bg-yellow-400 border-yellow-500';
      case 'standard':
        return count > 5 ? 'bg-blue-600 border-blue-700' : count > 2 ? 'bg-blue-500 border-blue-600' : 'bg-blue-400 border-blue-500';
      default:
        return count > 5 ? 'bg-slate-600 border-slate-700' : count > 2 ? 'bg-slate-500 border-slate-600' : 'bg-slate-400 border-slate-500';
    }
  };

  const getCellTextColor = (count: number) => {
    return count === 0 ? 'text-slate-400' : 'text-white';
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <div className="p-6 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Deadline Heat Map - Visual Triage
            </h3>
            <p className="text-sm text-slate-600 mt-1">
              {summary.total_deadlines} deadline{summary.total_deadlines !== 1 ? 's' : ''} in next 30 days
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-500">Fatality × Urgency Matrix</p>
            <p className="text-xs text-slate-500">Darker = More Deadlines</p>
          </div>
        </div>
      </div>

      <div className="p-6 overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-3 text-left text-xs font-semibold text-slate-600 bg-slate-50 border border-slate-200">
                Fatality →<br />Urgency ↓
              </th>
              {urgencyBuckets.map((bucket) => (
                <th key={bucket.key} className="p-3 text-center text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200 min-w-[140px]">
                  <div className="flex flex-col items-center gap-1">
                    <bucket.icon className="w-4 h-4" />
                    <span className="font-bold">{bucket.label}</span>
                    <span className="text-slate-500 font-normal">{bucket.subtext}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fatalityLevels.map((level) => (
              <tr key={level.key}>
                <td className={`p-3 text-center font-semibold text-xs ${level.color} ${level.textColor} border border-slate-300`}>
                  {level.label.toUpperCase()}
                </td>
                {urgencyBuckets.map((bucket) => {
                  const deadlines = matrix[level.key as keyof HeatMapMatrix][bucket.key as keyof typeof matrix.fatal];
                  const count = deadlines.length;
                  const cellColor = getCellColor(level.key, count);
                  const textColor = getCellTextColor(count);

                  return (
                    <td
                      key={bucket.key}
                      className={`p-3 text-center border border-slate-300 cursor-pointer hover:opacity-80 transition-opacity ${cellColor}`}
                      title={count > 0 ? `${count} deadline${count !== 1 ? 's' : ''}` : 'No deadlines'}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <span className={`text-2xl font-bold ${textColor}`}>
                          {count}
                        </span>
                        {count > 0 && (
                          <div className="w-full max-h-32 overflow-y-auto space-y-1">
                            {deadlines.slice(0, 3).map((deadline) => (
                              <div
                                key={deadline.id}
                                className="text-xs bg-white bg-opacity-90 p-2 rounded shadow-sm text-slate-800 text-left hover:bg-opacity-100 transition-all"
                                onClick={() => onCaseClick?.(deadline.case_id)}
                              >
                                <p className="font-semibold truncate" title={deadline.title}>
                                  {deadline.title}
                                </p>
                                <p className="text-slate-600 truncate" title={deadline.case_title}>
                                  {deadline.case_title}
                                </p>
                                <p className="text-slate-500 mt-1">
                                  {deadline.deadline_date} ({deadline.days_until}d)
                                </p>
                              </div>
                            ))}
                            {count > 3 && (
                              <p className="text-xs text-white font-semibold">
                                +{count - 3} more
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary Stats */}
      <div className="p-6 border-t border-slate-200 bg-slate-50">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-red-600">{summary.by_fatality.fatal}</p>
            <p className="text-xs text-slate-600 mt-1">Fatal</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-orange-600">{summary.by_fatality.critical}</p>
            <p className="text-xs text-slate-600 mt-1">Critical</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-yellow-600">{summary.by_fatality.important}</p>
            <p className="text-xs text-slate-600 mt-1">Important</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">{summary.by_fatality.standard}</p>
            <p className="text-xs text-slate-600 mt-1">Standard</p>
          </div>
        </div>
      </div>
    </div>
  );
}
