'use client';

/**
 * DEADLINE HEAT MAP V2 - Tactical Grid
 * Paper & Steel Design System: Dense, authoritative, editorial
 *
 * Visual Language:
 * - gap-px dark container for hard grid lines
 * - Mono typography for counts (precision)
 * - Hard borders on hover (instant, no fade)
 * - High density layout (no wasted space)
 */

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

  // Paper & Steel Palette - Restrained, authoritative colors
  const fatalityLevels = [
    { key: 'fatal', label: 'FATAL', bgColor: 'bg-fatal', textColor: 'text-white', borderColor: 'border-fatal' },
    { key: 'critical', label: 'CRITICAL', bgColor: 'bg-critical', textColor: 'text-white', borderColor: 'border-critical' },
    { key: 'important', label: 'IMPORTANT', bgColor: 'bg-important', textColor: 'text-white', borderColor: 'border-important' },
    { key: 'standard', label: 'STANDARD', bgColor: 'bg-steel', textColor: 'text-white', borderColor: 'border-steel' },
    { key: 'informational', label: 'INFO', bgColor: 'bg-informational', textColor: 'text-white', borderColor: 'border-informational' }
  ];

  const urgencyBuckets = [
    { key: 'today', label: 'TODAY', subtext: '0d' },
    { key: '3_day', label: '3-DAY', subtext: '1-3d' },
    { key: '7_day', label: '7-DAY', subtext: '4-7d' },
    { key: '30_day', label: '30-DAY', subtext: '8-30d' }
  ];

  const getCellBgColor = (fatalityKey: string, count: number) => {
    if (count === 0) return 'bg-surface';

    const intensity = count > 5 ? 'high' : count > 2 ? 'mid' : 'low';

    const colorMap: Record<string, Record<string, string>> = {
      fatal: { low: 'bg-fatal/40', mid: 'bg-fatal/70', high: 'bg-fatal' },
      critical: { low: 'bg-critical/40', mid: 'bg-critical/70', high: 'bg-critical' },
      important: { low: 'bg-important/40', mid: 'bg-important/70', high: 'bg-important' },
      standard: { low: 'bg-steel/40', mid: 'bg-steel/70', high: 'bg-steel' },
      informational: { low: 'bg-informational/40', mid: 'bg-informational/70', high: 'bg-informational' }
    };

    return colorMap[fatalityKey]?.[intensity] || 'bg-surface';
  };

  return (
    <div className="bg-paper border border-ink">
      {/* Header - Editorial Authority */}
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
          </div>
          <div className="text-right font-mono text-xs text-ink-secondary uppercase tracking-wider">
            <p>Fatality × Urgency</p>
            <p className="mt-1">Darker = Higher Density</p>
          </div>
        </div>
      </div>

      {/* Tactical Grid - gap-px creates hard 1px grid lines */}
      <div className="p-6 overflow-x-auto">
        <div className="bg-ink p-px">
          <div className="grid grid-cols-5 gap-px bg-ink">
            {/* Header Row */}
            <div className="bg-surface p-4 font-mono text-xs font-bold text-ink-secondary uppercase">
              Fatality →<br />Urgency ↓
            </div>
            {urgencyBuckets.map((bucket) => (
              <div key={bucket.key} className="bg-surface p-4 text-center font-mono">
                <div className="text-xs font-bold text-ink uppercase tracking-wide">
                  {bucket.label}
                </div>
                <div className="text-[10px] text-ink-secondary mt-1 uppercase tracking-wider">
                  {bucket.subtext}
                </div>
              </div>
            ))}

            {/* Data Rows */}
            {fatalityLevels.map((level) => (
              <React.Fragment key={level.key}>
                {/* Row Label */}
                <div className={`${level.bgColor} ${level.textColor} p-4 flex items-center justify-center font-mono text-xs font-bold uppercase tracking-wider`}>
                  {level.label}
                </div>

                {/* Cells */}
                {urgencyBuckets.map((bucket) => {
                  const deadlines = matrix[level.key as keyof HeatMapMatrix][bucket.key as keyof typeof matrix.fatal];
                  const count = deadlines.length;
                  const cellBg = getCellBgColor(level.key, count);

                  return (
                    <div
                      key={bucket.key}
                      className={`${cellBg} p-4 cursor-pointer relative group
                        transition-transform hover:translate-x-1 hover:translate-y-1
                        ${count > 0 ? 'hover:border-2 hover:border-ink' : ''}`}
                      title={count > 0 ? `${count} deadline${count !== 1 ? 's' : ''}` : 'No deadlines'}
                    >
                      {/* Count - Large, bold, mono */}
                      <div className="text-center">
                        <div className={`font-mono text-4xl font-bold ${count === 0 ? 'text-ink-muted' : 'text-white'}`}>
                          {count}
                        </div>
                      </div>

                      {/* Tooltip on hover - appears with hard snap (no fade) */}
                      {count > 0 && (
                        <div className="absolute top-full left-0 mt-1 hidden group-hover:block z-10
                          bg-paper border-2 border-ink p-3 min-w-[280px] max-w-[320px]">
                          <div className="space-y-2 max-h-48 overflow-y-auto">
                            {deadlines.slice(0, 4).map((deadline) => (
                              <div
                                key={deadline.id}
                                className="text-xs border-b border-ink/20 pb-2 last:border-0
                                  cursor-pointer hover:translate-x-1 transition-transform"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onCaseClick?.(deadline.case_id);
                                }}
                              >
                                <p className="font-sans font-semibold text-ink truncate" title={deadline.title}>
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
                              <p className="font-mono text-xs text-ink font-bold text-center pt-1">
                                +{count - 4} MORE
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Summary Footer - Dense stat display */}
      <div className="p-6 border-t border-ink bg-surface">
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center border-l-4 border-fatal pl-3">
            <p className="font-mono text-3xl font-bold text-fatal">{summary.by_fatality.fatal}</p>
            <p className="font-mono text-xs text-ink-secondary mt-1 uppercase tracking-wide">Fatal</p>
          </div>
          <div className="text-center border-l-4 border-critical pl-3">
            <p className="font-mono text-3xl font-bold text-critical">{summary.by_fatality.critical}</p>
            <p className="font-mono text-xs text-ink-secondary mt-1 uppercase tracking-wide">Critical</p>
          </div>
          <div className="text-center border-l-4 border-important pl-3">
            <p className="font-mono text-3xl font-bold text-important">{summary.by_fatality.important}</p>
            <p className="font-mono text-xs text-ink-secondary mt-1 uppercase tracking-wide">Important</p>
          </div>
          <div className="text-center border-l-4 border-steel pl-3">
            <p className="font-mono text-3xl font-bold text-steel">{summary.by_fatality.standard}</p>
            <p className="font-mono text-xs text-ink-secondary mt-1 uppercase tracking-wide">Standard</p>
          </div>
        </div>
      </div>
    </div>
  );
}
