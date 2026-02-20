'use client';

/**
 * DEADLINE HEAT MAP - Professional Grid
 * Paper & Steel Design System: Clean, spacious, readable
 *
 * Visual Language:
 * - White background with slate borders
 * - Clear typography with proper spacing
 * - Smooth hover states
 * - Balanced layout with breathing room
 */

import { AlertTriangle, Clock, Calendar } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

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
  const loadedAt = new Date(); // Track when component loaded

  // Paper & Steel Priority Palette
  const fatalityLevels = [
    { key: 'fatal', label: 'FATAL', bgColor: 'bg-red-600', textColor: 'text-white', borderColor: 'border-red-600' },
    { key: 'critical', label: 'CRITICAL', bgColor: 'bg-orange-600', textColor: 'text-white', borderColor: 'border-orange-600' },
    { key: 'important', label: 'IMPORTANT', bgColor: 'bg-amber-500', textColor: 'text-white', borderColor: 'border-amber-500' },
    { key: 'standard', label: 'STANDARD', bgColor: 'bg-blue-500', textColor: 'text-white', borderColor: 'border-blue-500' },
    { key: 'informational', label: 'INFO', bgColor: 'bg-slate-500', textColor: 'text-white', borderColor: 'border-slate-500' }
  ];

  const urgencyBuckets = [
    { key: 'today', label: 'TODAY', subtext: '0d' },
    { key: '3_day', label: '3-DAY', subtext: '1-3d' },
    { key: '7_day', label: '7-DAY', subtext: '4-7d' },
    { key: '30_day', label: '30-DAY', subtext: '8-30d' }
  ];

  const getCellBgColor = (fatalityKey: string, count: number) => {
    if (count === 0) return 'bg-slate-50';

    const intensity = count > 5 ? 'high' : count > 2 ? 'mid' : 'low';

    const colorMap: Record<string, Record<string, string>> = {
      fatal: { low: 'bg-red-100', mid: 'bg-red-300', high: 'bg-red-600' },
      critical: { low: 'bg-orange-100', mid: 'bg-orange-300', high: 'bg-orange-600' },
      important: { low: 'bg-amber-100', mid: 'bg-amber-300', high: 'bg-amber-500' },
      standard: { low: 'bg-blue-100', mid: 'bg-blue-300', high: 'bg-blue-500' },
      informational: { low: 'bg-slate-100', mid: 'bg-slate-300', high: 'bg-slate-500' }
    };

    return colorMap[fatalityKey]?.[intensity] || 'bg-slate-50';
  };

  return (
    <div className="card">
      {/* Header - Paper & Steel */}
      <div className="p-6 border-b border-ink bg-surface">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xl font-heading font-bold text-ink flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-fatal" />
              Deadline Heat Map
            </h3>
            <p className="text-sm font-mono text-ink-secondary mt-2">
              {summary.total_deadlines} deadlines × next 30 days
            </p>
            <div className="flex items-center gap-2 text-xs text-ink-muted font-mono mt-2">
              <Clock className="w-3 h-3" />
              Last updated: {formatDistanceToNow(loadedAt, { addSuffix: true })}
            </div>
          </div>
          <div className="text-right text-xs text-ink-secondary font-mono uppercase tracking-wider">
            <p>Priority × Urgency</p>
            <p className="mt-1">Darker = Higher Density</p>
          </div>
        </div>
      </div>

      {/* Heat Map Grid */}
      <div className="p-6 overflow-x-auto">
        <div className="border border-ink overflow-hidden">
          <div className="grid grid-cols-5 gap-0">
            {/* Header Row */}
            <div className="bg-surface p-4 border-r border-b border-ink text-xs font-mono font-semibold text-ink-secondary uppercase">
              Priority →<br />Urgency ↓
            </div>
            {urgencyBuckets.map((bucket, idx) => (
              <div key={bucket.key} className={`bg-surface p-4 text-center border-b border-ink ${idx < urgencyBuckets.length - 1 ? 'border-r border-ink' : ''}`}>
                <div className="text-xs font-mono font-bold text-ink uppercase tracking-wide">
                  {bucket.label}
                </div>
                <div className="text-[10px] font-mono text-ink-secondary mt-1 uppercase tracking-wider">
                  {bucket.subtext}
                </div>
              </div>
            ))}

            {/* Data Rows */}
            {fatalityLevels.map((level, levelIdx) => (
              <>
                {/* Row Label */}
                <div key={`label-${level.key}`} className={`${level.bgColor} ${level.textColor} p-4 flex items-center justify-center text-xs font-mono font-bold uppercase tracking-wider border-r border-ink ${levelIdx < fatalityLevels.length - 1 ? 'border-b border-ink' : ''}`}>
                  {level.label}
                </div>

                {/* Cells */}
                {urgencyBuckets.map((bucket, bucketIdx) => {
                  const deadlines = matrix[level.key as keyof HeatMapMatrix][bucket.key as keyof typeof matrix.fatal];
                  const count = deadlines.length;
                  const cellBg = getCellBgColor(level.key, count);
                  const isHighIntensity = count > 2;

                  return (
                    <div
                      key={`${level.key}-${bucket.key}`}
                      className={`${cellBg} p-6 cursor-pointer relative group transition-transform hover:translate-x-0.5 hover:translate-y-0.5 ${
                        bucketIdx < urgencyBuckets.length - 1 ? 'border-r border-ink/20' : ''
                      } ${levelIdx < fatalityLevels.length - 1 ? 'border-b border-ink/20' : ''}`}
                      title={count > 0 ? `${count} deadline${count !== 1 ? 's' : ''}` : 'No deadlines'}
                    >
                      {/* Count - Large, bold, mono */}
                      <div className="text-center">
                        <div className={`font-mono text-4xl font-bold ${count === 0 ? 'text-ink/20' : isHighIntensity ? 'text-white' : 'text-ink'}`}>
                          {count}
                        </div>
                      </div>

                      {/* Tooltip on hover */}
                      {count > 0 && (
                        <div className="absolute top-full left-0 mt-2 hidden group-hover:block z-10 bg-paper border-2 border-ink shadow-modal p-4 min-w-[300px] max-w-[320px]">
                          <div className="space-y-3 max-h-64 overflow-y-auto">
                            {deadlines.slice(0, 4).map((deadline) => (
                              <div
                                key={deadline.id}
                                role="button"
                                tabIndex={0}
                                className="text-xs border-b border-ink/20 pb-3 last:border-0 cursor-pointer hover:bg-surface -mx-2 px-2 py-2 transition-colors"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onCaseClick?.(deadline.case_id);
                                }}
                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onCaseClick?.(deadline.case_id); } }}
                              >
                                <p className="font-semibold text-ink truncate" title={deadline.title}>
                                  {deadline.title}
                                </p>
                                <p className="font-mono text-[10px] text-ink-secondary truncate mt-1" title={deadline.case_title}>
                                  {deadline.case_title}
                                </p>
                                <p className="font-mono text-[10px] text-ink-muted mt-1">
                                  {deadline.deadline_date} · {deadline.days_until}d
                                </p>
                              </div>
                            ))}
                            {count > 4 && (
                              <p className="font-mono text-xs text-steel font-bold text-center pt-2">
                                +{count - 4} more
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </>
            ))}
          </div>
        </div>
      </div>

      {/* Summary Footer - Clean stat display */}
      <div className="p-6 border-t border-ink bg-surface">
        <div className="grid grid-cols-4 gap-6">
          <div className="text-center">
            <p className="font-mono text-3xl font-bold text-fatal">{summary.by_fatality.fatal}</p>
            <p className="text-xs font-mono text-ink-secondary mt-2 uppercase tracking-wide font-semibold">Fatal</p>
          </div>
          <div className="text-center">
            <p className="font-mono text-3xl font-bold text-critical">{summary.by_fatality.critical}</p>
            <p className="text-xs font-mono text-ink-secondary mt-2 uppercase tracking-wide font-semibold">Critical</p>
          </div>
          <div className="text-center">
            <p className="font-mono text-3xl font-bold text-important">{summary.by_fatality.important}</p>
            <p className="text-xs font-mono text-ink-secondary mt-2 uppercase tracking-wide font-semibold">Important</p>
          </div>
          <div className="text-center">
            <p className="font-mono text-3xl font-bold text-steel">{summary.by_fatality.standard}</p>
            <p className="text-xs font-mono text-ink-secondary mt-2 uppercase tracking-wide font-semibold">Standard</p>
          </div>
        </div>
      </div>
    </div>
  );
}
