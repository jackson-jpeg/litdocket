'use client';

/**
 * Tools Hub - Command Center for Legal Power Tools
 *
 * Gold Standard Design System (matching Dashboard):
 * - Light slate background
 * - White cards with shadows
 * - Rounded corners
 * - Uppercase tracking headers
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Calculator,
  GitBranch,
  Calendar,
  FileSearch,
  Scale,
  Clock,
  Database,
  Zap,
  ArrowRight,
  Lock,
  Wrench,
  Info,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

interface Tool {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  status: 'active' | 'beta' | 'coming_soon';
  category: 'calculation' | 'navigation' | 'analysis' | 'export';
  shortcut?: string;
  docsLink?: string;
}

const TOOLS: Tool[] = [
  {
    id: 'authority-core',
    name: 'Authority Core',
    description: 'AI-powered rules database. Extract, verify, and manage court rules from any jurisdiction.',
    icon: <Database className="w-5 h-5" />,
    href: '/tools/authority-core',
    status: 'active',
    category: 'navigation',
    shortcut: 'Alt+A',
    docsLink: '/docs/tools/authority-core',
  },
  {
    id: 'deadline-calculator',
    name: 'Deadline Calculator',
    description: 'Calculate deadlines with federal/state holiday awareness, service day extensions, and full audit trail.',
    icon: <Calculator className="w-5 h-5" />,
    href: '/tools/deadline-calculator',
    status: 'active',
    category: 'calculation',
    shortcut: 'Alt+C',
    docsLink: '/docs/tools/deadline-calculator',
  },
  {
    id: 'jurisdiction-selector',
    name: 'Jurisdiction Navigator',
    description: 'CompuLaw-style hierarchical court selector with automatic concurrent rule detection.',
    icon: <GitBranch className="w-5 h-5" />,
    href: '/tools/jurisdiction-selector',
    status: 'active',
    category: 'navigation',
    shortcut: 'Alt+J',
    docsLink: '/docs/tools/jurisdiction-selector',
  },
  {
    id: 'rule-graph',
    name: 'Rule Dependency Graph',
    description: 'Visualize rule set dependencies and cascading requirements across jurisdictions.',
    icon: <Database className="w-5 h-5" />,
    href: '/tools/rule-graph',
    status: 'coming_soon',
    category: 'navigation',
    docsLink: '/docs/tools/rule-graph',
  },
  {
    id: 'calendar-export',
    name: 'Calendar Export',
    description: 'Export deadlines to iCal, Google Calendar, Outlook with recurrence rules.',
    icon: <Calendar className="w-5 h-5" />,
    href: '/tools/calendar-export',
    status: 'coming_soon',
    category: 'export',
    docsLink: '/docs/tools/calendar-export',
  },
  {
    id: 'document-analyzer',
    name: 'Document Analyzer',
    description: 'AI-powered analysis of legal documents with automatic deadline extraction.',
    icon: <FileSearch className="w-5 h-5" />,
    href: '/tools/document-analyzer',
    status: 'beta',
    category: 'analysis',
    shortcut: 'Alt+D',
    docsLink: '/docs/tools/document-analyzer',
  },
  {
    id: 'statute-lookup',
    name: 'Statute Lookup',
    description: 'Quick reference for FRCP, FRAP, Florida Rules with deadline implications.',
    icon: <Scale className="w-5 h-5" />,
    href: '/tools/statute-lookup',
    status: 'coming_soon',
    category: 'analysis',
    docsLink: '/docs/tools/statute-lookup',
  },
  {
    id: 'time-calculator',
    name: 'Time Period Calculator',
    description: 'Calculate business days, court days, retrograde periods between any two dates.',
    icon: <Clock className="w-5 h-5" />,
    href: '/tools/time-calculator',
    status: 'coming_soon',
    category: 'calculation',
    docsLink: '/docs/tools/time-calculator',
  },
  {
    id: 'batch-import',
    name: 'Batch Deadline Import',
    description: 'Import deadlines from CSV, Excel, or other docketing systems.',
    icon: <Zap className="w-5 h-5" />,
    href: '/tools/batch-import',
    status: 'coming_soon',
    category: 'export',
    docsLink: '/docs/tools/batch-import',
  },
];

const CATEGORY_LABELS: Record<string, string> = {
  calculation: 'CALCULATION',
  navigation: 'NAVIGATION',
  analysis: 'ANALYSIS',
  export: 'IMPORT/EXPORT',
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  calculation: <Calculator className="w-4 h-4" />,
  navigation: <GitBranch className="w-4 h-4" />,
  analysis: <FileSearch className="w-4 h-4" />,
  export: <Calendar className="w-4 h-4" />,
};

export default function ToolsHubPage() {
  const router = useRouter();
  const [comingSoonExpanded, setComingSoonExpanded] = useState(false);

  const getStatusBadge = (status: Tool['status']) => {
    switch (status) {
      case 'active':
        return (
          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-mono rounded-full border border-green-200">
            ACTIVE
          </span>
        );
      case 'beta':
        return (
          <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-mono rounded-full border border-amber-200">
            BETA
          </span>
        );
      case 'coming_soon':
        return (
          <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-xs font-mono rounded-full border border-slate-200">
            SOON
          </span>
        );
    }
  };

  const handleToolClick = (tool: Tool) => {
    if (tool.status === 'coming_soon') return;
    router.push(tool.href);
  };

  // Group tools by category
  const toolsByCategory = TOOLS.reduce((acc, tool) => {
    if (!acc[tool.category]) acc[tool.category] = [];
    acc[tool.category].push(tool);
    return acc;
  }, {} as Record<string, Tool[]>);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-slate-100 rounded-lg">
                  <Wrench className="w-5 h-5 text-slate-700" />
                </div>
                <h1 className="text-2xl font-bold text-slate-900">Tools</h1>
              </div>
              <p className="text-slate-500 text-sm">
                Legal Power Tools for Professional Docketing
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right text-sm">
                <div className="flex items-center gap-4">
                  <span className="text-green-600 font-medium">
                    {TOOLS.filter(t => t.status === 'active').length} Active
                  </span>
                  <span className="text-amber-600 font-medium">
                    {TOOLS.filter(t => t.status === 'beta').length} Beta
                  </span>
                  <span className="text-slate-400">
                    {TOOLS.filter(t => t.status === 'coming_soon').length} Coming
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Quick Access - Active/Beta Tools */}
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-green-600" />
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Quick Access</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {TOOLS.filter(t => t.status !== 'coming_soon').map((tool) => (
              <button
                key={tool.id}
                onClick={() => handleToolClick(tool)}
                className="group bg-white border border-slate-200 hover:border-slate-400 hover:shadow-lg p-6 text-left transition-all duration-200 rounded-xl hover:-translate-y-1 hover:scale-[1.02] focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 bg-blue-50 text-blue-600 rounded-lg group-hover:bg-blue-100 transition-colors">
                    {tool.icon}
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(tool.status)}
                    {tool.shortcut && (
                      <kbd className="px-2 py-1 bg-slate-200 text-slate-700 text-xs font-mono rounded border border-slate-300">
                        {tool.shortcut}
                      </kbd>
                    )}
                  </div>
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2 group-hover:text-blue-700 transition-colors">
                  {tool.name}
                </h3>
                <p className="text-sm text-slate-500 mb-4">
                  {tool.description}
                </p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-blue-600 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                    <span>Launch Tool</span>
                    <ArrowRight className="w-4 h-4" />
                  </div>
                  {tool.docsLink && (
                    <a
                      href={tool.docsLink}
                      onClick={(e) => {
                        e.stopPropagation();
                        alert(`Documentation: ${tool.name}\n\nDocs will be available soon at: ${tool.docsLink}`);
                      }}
                      className="flex items-center gap-1 text-xs text-slate-400 hover:text-blue-600 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Info className="w-3 h-3" />
                      <span>Learn more</span>
                    </a>
                  )}
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* All Tools by Category (excluding coming soon) */}
        {Object.entries(toolsByCategory).map(([category, tools]) => {
          const activeTools = tools.filter(t => t.status !== 'coming_soon');
          if (activeTools.length === 0) return null;

          return (
            <section key={category} className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-slate-400">{CATEGORY_ICONS[category]}</span>
                <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  {CATEGORY_LABELS[category]}
                </h2>
                <div className="flex-1 h-px bg-slate-200" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {activeTools.map((tool) => (
                  <button
                    key={tool.id}
                    onClick={() => handleToolClick(tool)}
                    className="group p-4 text-left border bg-white border-slate-200 rounded-lg transition-all duration-200 hover:border-slate-400 hover:shadow-md hover:-translate-y-0.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-slate-600">
                        {tool.icon}
                      </div>
                      <div className="flex items-center gap-1">
                        {tool.status === 'beta' && (
                          <span className="text-xs font-mono text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">BETA</span>
                        )}
                        {tool.shortcut && (
                          <kbd className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs font-mono rounded border border-slate-200">
                            {tool.shortcut}
                          </kbd>
                        )}
                      </div>
                    </div>
                    <h3 className="text-sm font-medium mb-1 text-slate-900 group-hover:text-blue-700 transition-colors">
                      {tool.name}
                    </h3>
                    <p className="text-xs text-slate-500 line-clamp-2 mb-2">
                      {tool.description}
                    </p>
                    {tool.docsLink && (
                      <a
                        href={tool.docsLink}
                        onClick={(e) => {
                          e.stopPropagation();
                          alert(`Documentation: ${tool.name}\n\nDocs will be available soon at: ${tool.docsLink}`);
                        }}
                        className="flex items-center gap-1 text-xs text-slate-400 hover:text-blue-600 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <Info className="w-3 h-3" />
                        <span>Learn more</span>
                      </a>
                    )}
                  </button>
                ))}
              </div>
            </section>
          );
        })}

        {/* Coming Soon Section - Collapsed by default */}
        <section className="mb-8">
          <button
            onClick={() => setComingSoonExpanded(!comingSoonExpanded)}
            className="w-full flex items-center gap-2 mb-4 hover:bg-slate-50 px-3 py-2 rounded-lg transition-colors"
          >
            {comingSoonExpanded ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Coming Soon ({TOOLS.filter(t => t.status === 'coming_soon').length} tools)
            </h2>
            <div className="flex-1 h-px bg-slate-200" />
          </button>
          {comingSoonExpanded && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 opacity-60">
              {TOOLS.filter(t => t.status === 'coming_soon').map((tool) => (
                <div
                  key={tool.id}
                  className="group p-4 text-left border bg-slate-50 border-slate-200 rounded-lg cursor-not-allowed"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-slate-400">
                      {tool.icon}
                    </div>
                    <Lock className="w-3 h-3 text-slate-400" />
                  </div>
                  <h3 className="text-sm font-medium mb-1 text-slate-500">
                    {tool.name}
                  </h3>
                  <p className="text-xs text-slate-500 line-clamp-2 mb-2">
                    {tool.description}
                  </p>
                  {tool.docsLink && (
                    <div className="flex items-center gap-1 text-xs text-slate-400">
                      <Info className="w-3 h-3" />
                      <span>Docs coming soon</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Footer Stats */}
        <footer className="mt-12 pt-8 border-t border-slate-200">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <p className="text-3xl font-bold text-slate-900">{TOOLS.length}</p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Total Tools</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <p className="text-3xl font-bold text-green-600">
                {TOOLS.filter(t => t.status === 'active').length}
              </p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Active</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <p className="text-3xl font-bold text-amber-600">
                {TOOLS.filter(t => t.status === 'beta').length}
              </p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">In Beta</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <p className="text-3xl font-bold text-slate-400">
                {TOOLS.filter(t => t.status === 'coming_soon').length}
              </p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Coming Soon</p>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
