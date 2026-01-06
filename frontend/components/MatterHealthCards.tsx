'use client';

import { AlertTriangle, Clock, CheckCircle, Activity, FileText, Gavel, ChevronRight } from 'lucide-react';

interface HealthCard {
  case_id: string;
  case_number: string;
  title: string;
  court: string;
  judge: string;
  jurisdiction: string;
  case_type: string;
  progress: {
    completed: number;
    pending: number;
    total: number;
    percentage: number;
  };
  next_deadline: {
    title: string;
    date: string;
    days_until: number;
    priority: string;
  } | null;
  next_deadline_urgency: string;
  health_status: string;
  document_count: number;
  filing_date: string | null;
}

interface MatterHealthCardsProps {
  healthCards: HealthCard[];
  onCaseClick?: (caseId: string) => void;
}

export default function MatterHealthCards({ healthCards, onCaseClick }: MatterHealthCardsProps) {
  const getHealthColor = (status: string) => {
    switch (status) {
      case 'critical': return 'border-red-500 bg-red-50';
      case 'needs_attention': return 'border-orange-500 bg-orange-50';
      case 'busy': return 'border-yellow-500 bg-yellow-50';
      case 'healthy': return 'border-green-500 bg-green-50';
      default: return 'border-slate-300 bg-white';
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'critical': return <AlertTriangle className="w-5 h-5 text-red-600" />;
      case 'needs_attention': return <Clock className="w-5 h-5 text-orange-600" />;
      case 'busy': return <Activity className="w-5 h-5 text-yellow-600" />;
      case 'healthy': return <CheckCircle className="w-5 h-5 text-green-600" />;
      default: return <Activity className="w-5 h-5 text-slate-400" />;
    }
  };

  const getHealthLabel = (status: string) => {
    switch (status) {
      case 'critical': return 'CRITICAL';
      case 'needs_attention': return 'Needs Attention';
      case 'busy': return 'Busy';
      case 'healthy': return 'Healthy';
      default: return 'Unknown';
    }
  };

  const getHealthBadgeColor = (status: string) => {
    switch (status) {
      case 'critical': return 'bg-red-600 text-white';
      case 'needs_attention': return 'bg-orange-600 text-white';
      case 'busy': return 'bg-yellow-600 text-white';
      case 'healthy': return 'bg-green-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical': return 'text-red-700 font-semibold';
      case 'urgent': return 'text-orange-700 font-semibold';
      case 'attention': return 'text-yellow-700';
      default: return 'text-slate-600';
    }
  };

  if (!healthCards || healthCards.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
        <div className="text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <p className="text-slate-600">No active cases requiring attention</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <div className="p-6 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-500" />
              Matter Health Cards
            </h3>
            <p className="text-sm text-slate-600 mt-1">
              {healthCards.length} active case{healthCards.length !== 1 ? 's' : ''} with pending deadlines
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-600 rounded"></div>
              <span>Critical</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-orange-600 rounded"></div>
              <span>Attention</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-600 rounded"></div>
              <span>Healthy</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-4 max-h-[800px] overflow-y-auto">
        {healthCards.map((card) => (
          <div
            key={card.case_id}
            className={`border-2 rounded-lg p-5 cursor-pointer hover:shadow-lg transition-all ${getHealthColor(card.health_status)}`}
            onClick={() => onCaseClick?.(card.case_id)}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  {getHealthIcon(card.health_status)}
                  <h4 className="font-bold text-slate-800 text-sm">{card.case_number}</h4>
                  <span className={`text-xs px-2 py-0.5 rounded font-semibold ${getHealthBadgeColor(card.health_status)}`}>
                    {getHealthLabel(card.health_status)}
                  </span>
                </div>
                <p className="text-slate-700 font-medium truncate">{card.title}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-slate-600">
                  <div className="flex items-center gap-1">
                    <Gavel className="w-3 h-3" />
                    <span>{card.judge}</span>
                  </div>
                  <span>•</span>
                  <span>{card.court}</span>
                  <span>•</span>
                  <div className="flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    <span>{card.document_count} docs</span>
                  </div>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0 ml-3" />
            </div>

            {/* Progress Bar */}
            <div className="mb-4">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="text-slate-600 font-medium">Deadline Progress</span>
                <span className="text-slate-700 font-semibold">
                  {card.progress.completed}/{card.progress.total} Complete ({card.progress.percentage}%)
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    card.progress.percentage === 100
                      ? 'bg-green-600'
                      : card.progress.percentage > 50
                      ? 'bg-blue-600'
                      : 'bg-orange-600'
                  }`}
                  style={{ width: `${card.progress.percentage}%` }}
                ></div>
              </div>
              <div className="flex items-center justify-between text-xs mt-1 text-slate-500">
                <span>{card.progress.completed} completed</span>
                <span>{card.progress.pending} pending</span>
              </div>
            </div>

            {/* Next Deadline */}
            {card.next_deadline ? (
              <div className="p-3 bg-white bg-opacity-70 border border-slate-300 rounded-lg">
                <p className="text-xs font-semibold text-slate-600 mb-1">Next Deadline:</p>
                <p className="font-semibold text-slate-800 text-sm">{card.next_deadline.title}</p>
                <div className="flex items-center justify-between mt-2">
                  <p className={`text-sm ${getUrgencyColor(card.next_deadline_urgency)}`}>
                    {card.next_deadline.date}
                  </p>
                  <span className={`text-xs px-2 py-1 rounded font-semibold ${
                    card.next_deadline.days_until <= 1
                      ? 'bg-red-100 text-red-800'
                      : card.next_deadline.days_until <= 3
                      ? 'bg-orange-100 text-orange-800'
                      : card.next_deadline.days_until <= 7
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {card.next_deadline.days_until === 0
                      ? 'TODAY'
                      : card.next_deadline.days_until === 1
                      ? 'TOMORROW'
                      : `${card.next_deadline.days_until} days`}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-center">
                <CheckCircle className="w-4 h-4 text-green-600 inline-block mr-2" />
                <span className="text-sm text-green-700 font-medium">No upcoming deadlines</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
