'use client';

/**
 * ContextualToolCard - Tool suggestion card for contextual discovery
 *
 * Displays relevant tool suggestions based on the current page context.
 * Used on Dashboard, Case Detail, and Calendar pages.
 */

import React from 'react';
import Link from 'next/link';
import { Calculator, Globe, FileSearch, BookOpen, ChevronRight, Sparkles, Zap } from 'lucide-react';

type ToolType = 'calculator' | 'jurisdiction' | 'analyzer' | 'authority';

interface ToolConfig {
  id: ToolType;
  name: string;
  description: string;
  href: string;
  icon: React.ReactNode;
  shortcut: string;
  color: string;
  bgColor: string;
}

const tools: Record<ToolType, ToolConfig> = {
  calculator: {
    id: 'calculator',
    name: 'Deadline Calculator',
    description: 'Calculate deadlines from any event',
    href: '/tools/deadline-calculator',
    icon: <Calculator className="w-5 h-5" />,
    shortcut: 'Alt+C',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50 border-blue-200 hover:bg-blue-100',
  },
  jurisdiction: {
    id: 'jurisdiction',
    name: 'Jurisdiction Navigator',
    description: 'Explore rules by court and jurisdiction',
    href: '/tools/jurisdiction-selector',
    icon: <Globe className="w-5 h-5" />,
    shortcut: 'Alt+J',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50 border-emerald-200 hover:bg-emerald-100',
  },
  analyzer: {
    id: 'analyzer',
    name: 'Document Analyzer',
    description: 'Upload and analyze court documents',
    href: '/tools/document-analyzer',
    icon: <FileSearch className="w-5 h-5" />,
    shortcut: 'Alt+D',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50 border-purple-200 hover:bg-purple-100',
  },
  authority: {
    id: 'authority',
    name: 'Authority Core',
    description: 'Search legal rules and regulations',
    href: '/tools/authority-core',
    icon: <BookOpen className="w-5 h-5" />,
    shortcut: 'Alt+A',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50 border-amber-200 hover:bg-amber-100',
  },
};

interface ContextualToolCardProps {
  /**
   * Which tool to suggest
   */
  toolId: ToolType;

  /**
   * Optional custom title
   */
  title?: string;

  /**
   * Optional custom description
   */
  description?: string;

  /**
   * Size variant
   */
  size?: 'compact' | 'default' | 'large';

  /**
   * Optional query parameters to pass to the tool
   */
  queryParams?: Record<string, string>;

  /**
   * Optional class name
   */
  className?: string;
}

export function ContextualToolCard({
  toolId,
  title,
  description,
  size = 'default',
  queryParams,
  className = '',
}: ContextualToolCardProps) {
  const tool = tools[toolId];
  if (!tool) return null;

  const href = queryParams
    ? `${tool.href}?${new URLSearchParams(queryParams).toString()}`
    : tool.href;

  if (size === 'compact') {
    return (
      <Link
        href={href}
        className={`
          flex items-center gap-3 px-4 py-3 rounded-lg border transition-all
          ${tool.bgColor}
          ${className}
        `}
      >
        <span className={tool.color}>{tool.icon}</span>
        <span className="flex-1 text-sm font-medium text-slate-800">
          {title || tool.name}
        </span>
        <kbd className="text-[10px] font-mono text-slate-500 bg-white/50 px-1.5 py-0.5 rounded">
          {tool.shortcut}
        </kbd>
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </Link>
    );
  }

  if (size === 'large') {
    return (
      <Link
        href={href}
        className={`
          block p-6 rounded-xl border transition-all group
          ${tool.bgColor}
          ${className}
        `}
      >
        <div className="flex items-start gap-4">
          <div className={`p-3 rounded-lg bg-white ${tool.color}`}>
            {tool.icon}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-semibold text-slate-900">
                {title || tool.name}
              </h3>
              <kbd className="text-[10px] font-mono text-slate-500 bg-white/70 px-1.5 py-0.5 rounded">
                {tool.shortcut}
              </kbd>
            </div>
            <p className="text-sm text-slate-600">
              {description || tool.description}
            </p>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-400 group-hover:translate-x-1 transition-transform" />
        </div>
      </Link>
    );
  }

  // Default size
  return (
    <Link
      href={href}
      className={`
        flex items-center gap-4 px-4 py-4 rounded-lg border transition-all group
        ${tool.bgColor}
        ${className}
      `}
    >
      <div className={`p-2 rounded-lg bg-white ${tool.color}`}>
        {tool.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <h4 className="text-sm font-semibold text-slate-900 truncate">
            {title || tool.name}
          </h4>
          <kbd className="text-[10px] font-mono text-slate-500 bg-white/70 px-1.5 py-0.5 rounded flex-shrink-0">
            {tool.shortcut}
          </kbd>
        </div>
        <p className="text-xs text-slate-600 truncate">
          {description || tool.description}
        </p>
      </div>
      <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0 group-hover:translate-x-1 transition-transform" />
    </Link>
  );
}

/**
 * ToolSuggestionBanner - A horizontal banner suggesting a tool
 */
interface ToolSuggestionBannerProps {
  toolId: ToolType;
  message: string;
  className?: string;
}

export function ToolSuggestionBanner({
  toolId,
  message,
  className = '',
}: ToolSuggestionBannerProps) {
  const tool = tools[toolId];
  if (!tool) return null;

  return (
    <Link
      href={tool.href}
      className={`
        flex items-center justify-between px-5 py-3 rounded-lg border transition-all
        bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200 hover:border-blue-300 hover:shadow-md
        ${className}
      `}
    >
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-slate-800">{message}</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`font-medium text-sm ${tool.color}`}>{tool.name}</span>
        <kbd className="text-[10px] font-mono text-slate-500 bg-white px-1.5 py-0.5 rounded">
          {tool.shortcut}
        </kbd>
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </div>
    </Link>
  );
}

/**
 * QuickToolsGrid - A grid of tool cards for empty states
 */
interface QuickToolsGridProps {
  tools?: ToolType[];
  title?: string;
  className?: string;
}

export function QuickToolsGrid({
  tools: toolIds = ['calculator', 'jurisdiction', 'analyzer', 'authority'],
  title = 'Quick Tools',
  className = '',
}: QuickToolsGridProps) {
  return (
    <div className={className}>
      <div className="flex items-center gap-2 mb-4">
        <Zap className="w-4 h-4 text-amber-500" />
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {toolIds.map(toolId => (
          <ContextualToolCard key={toolId} toolId={toolId} size="compact" />
        ))}
      </div>
    </div>
  );
}

export default ContextualToolCard;
