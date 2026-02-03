'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Clock,
  BookOpen,
  FileSearch,
  Target,
  Users,
  ChevronDown,
  Check,
  Sparkles,
} from 'lucide-react';

export interface Agent {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  primary_tools: string[];
  triggering_phrases: string[];
  is_active: boolean;
  display_order: number;
}

interface AgentSelectorProps {
  agents: Agent[];
  selectedAgent: Agent | null;
  onSelectAgent: (agent: Agent | null) => void;
  suggestedAgent?: Agent | null;
  compact?: boolean;
}

// Map icon names to Lucide components
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  clock: Clock,
  book: BookOpen,
  'file-search': FileSearch,
  target: Target,
  users: Users,
};

// Map color names to Tailwind classes
const colorMap: Record<string, { bg: string; text: string; border: string; ring: string }> = {
  red: {
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
    ring: 'ring-red-500',
  },
  blue: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
    ring: 'ring-blue-500',
  },
  purple: {
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
    ring: 'ring-purple-500',
  },
  green: {
    bg: 'bg-green-50',
    text: 'text-green-700',
    border: 'border-green-200',
    ring: 'ring-green-500',
  },
  orange: {
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    border: 'border-orange-200',
    ring: 'ring-orange-500',
  },
};

const defaultColor = {
  bg: 'bg-slate-50',
  text: 'text-slate-700',
  border: 'border-slate-200',
  ring: 'ring-slate-500',
};

export default function AgentSelector({
  agents,
  selectedAgent,
  onSelectAgent,
  suggestedAgent,
  compact = false,
}: AgentSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getIcon = (iconName: string | null) => {
    if (!iconName) return Sparkles;
    return iconMap[iconName] || Sparkles;
  };

  const getColorClasses = (colorName: string | null) => {
    if (!colorName) return defaultColor;
    return colorMap[colorName] || defaultColor;
  };

  const renderAgentPill = (agent: Agent | null, showDropdownIcon = false) => {
    if (!agent) {
      return (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 text-slate-600 text-sm">
          <Sparkles className="w-4 h-4" />
          <span className="font-medium">General Assistant</span>
          {showDropdownIcon && <ChevronDown className="w-3 h-3 ml-1" />}
        </div>
      );
    }

    const Icon = getIcon(agent.icon);
    const colors = getColorClasses(agent.color);

    return (
      <div
        className={`flex items-center gap-2 px-3 py-1.5 ${colors.bg} border ${colors.border} ${colors.text} text-sm`}
      >
        <Icon className="w-4 h-4" />
        <span className="font-medium">{agent.name}</span>
        {showDropdownIcon && <ChevronDown className="w-3 h-3 ml-1" />}
      </div>
    );
  };

  if (compact) {
    // Compact mode: Just pills for quick switching
    return (
      <div className="flex flex-wrap gap-1">
        {/* General Assistant option */}
        <button
          onClick={() => onSelectAgent(null)}
          className={`flex items-center gap-1.5 px-2 py-1 text-xs border transition-colors ${
            selectedAgent === null
              ? 'bg-slate-100 border-slate-300 text-slate-800'
              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <Sparkles className="w-3 h-3" />
          <span>General</span>
        </button>

        {agents.map((agent) => {
          const Icon = getIcon(agent.icon);
          const colors = getColorClasses(agent.color);
          const isSelected = selectedAgent?.slug === agent.slug;
          const isSuggested = suggestedAgent?.slug === agent.slug && !isSelected;

          return (
            <button
              key={agent.slug}
              onClick={() => onSelectAgent(agent)}
              className={`flex items-center gap-1.5 px-2 py-1 text-xs border transition-colors ${
                isSelected
                  ? `${colors.bg} ${colors.border} ${colors.text}`
                  : isSuggested
                  ? `bg-white ${colors.border} ${colors.text} ring-1 ${colors.ring}`
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
              title={agent.description || agent.name}
            >
              <Icon className="w-3 h-3" />
              <span>{agent.name.split(' ')[0]}</span>
              {isSuggested && (
                <span className="ml-0.5 text-[10px] font-bold uppercase">!</span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  // Full dropdown mode
  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="cursor-pointer hover:opacity-80 transition-opacity"
      >
        {renderAgentPill(selectedAgent, true)}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-slate-200 shadow-lg z-50">
          {/* General Assistant option */}
          <button
            onClick={() => {
              onSelectAgent(null);
              setIsOpen(false);
            }}
            className={`w-full flex items-start gap-3 p-3 text-left hover:bg-slate-50 transition-colors ${
              selectedAgent === null ? 'bg-slate-50' : ''
            }`}
          >
            <div className="w-8 h-8 bg-slate-100 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-slate-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm text-slate-900">General Assistant</span>
                {selectedAgent === null && (
                  <Check className="w-4 h-4 text-green-600" />
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Standard AI assistant for all tasks
              </p>
            </div>
          </button>

          <div className="border-t border-slate-100" />

          {/* Agent options */}
          {agents.map((agent) => {
            const Icon = getIcon(agent.icon);
            const colors = getColorClasses(agent.color);
            const isSelected = selectedAgent?.slug === agent.slug;
            const isSuggested = suggestedAgent?.slug === agent.slug && !isSelected;

            return (
              <button
                key={agent.slug}
                onClick={() => {
                  onSelectAgent(agent);
                  setIsOpen(false);
                }}
                className={`w-full flex items-start gap-3 p-3 text-left hover:bg-slate-50 transition-colors ${
                  isSelected ? 'bg-slate-50' : ''
                } ${isSuggested ? `ring-2 ${colors.ring} ring-inset` : ''}`}
              >
                <div
                  className={`w-8 h-8 ${colors.bg} flex items-center justify-center flex-shrink-0`}
                >
                  <Icon className={`w-4 h-4 ${colors.text}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-slate-900">{agent.name}</span>
                    {isSelected && <Check className="w-4 h-4 text-green-600" />}
                    {isSuggested && (
                      <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase bg-yellow-100 text-yellow-700">
                        Suggested
                      </span>
                    )}
                  </div>
                  {agent.description && (
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                      {agent.description}
                    </p>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
