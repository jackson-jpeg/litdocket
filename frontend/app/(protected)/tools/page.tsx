'use client';

/**
 * Tools Hub - Command Center for Legal Power Tools
 *
 * Sovereign Design System:
 * - Dense grid layout
 * - Terminal aesthetic
 * - Zero radius
 */

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
  Sparkles,
} from 'lucide-react';

interface Tool {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  status: 'active' | 'beta' | 'coming_soon';
  category: 'calculation' | 'navigation' | 'analysis' | 'export';
}

const TOOLS: Tool[] = [
  {
    id: 'deadline-calculator',
    name: 'Deadline Calculator',
    description: 'Calculate deadlines with federal/state holiday awareness, service day extensions, and full audit trail.',
    icon: <Calculator className="w-5 h-5" />,
    href: '/tools/sovereign',
    status: 'active',
    category: 'calculation',
  },
  {
    id: 'jurisdiction-selector',
    name: 'Jurisdiction Navigator',
    description: 'CompuLaw-style hierarchical court selector with automatic concurrent rule detection.',
    icon: <GitBranch className="w-5 h-5" />,
    href: '/tools/jurisdiction-selector',
    status: 'active',
    category: 'navigation',
  },
  {
    id: 'rule-graph',
    name: 'Rule Dependency Graph',
    description: 'Visualize rule set dependencies and cascading requirements across jurisdictions.',
    icon: <Database className="w-5 h-5" />,
    href: '/tools/rule-graph',
    status: 'coming_soon',
    category: 'navigation',
  },
  {
    id: 'calendar-export',
    name: 'Calendar Export',
    description: 'Export deadlines to iCal, Google Calendar, Outlook with recurrence rules.',
    icon: <Calendar className="w-5 h-5" />,
    href: '/tools/calendar-export',
    status: 'coming_soon',
    category: 'export',
  },
  {
    id: 'document-analyzer',
    name: 'Document Analyzer',
    description: 'AI-powered analysis of legal documents with automatic deadline extraction.',
    icon: <FileSearch className="w-5 h-5" />,
    href: '/tools/document-analyzer',
    status: 'beta',
    category: 'analysis',
  },
  {
    id: 'statute-lookup',
    name: 'Statute Lookup',
    description: 'Quick reference for FRCP, FRAP, Florida Rules with deadline implications.',
    icon: <Scale className="w-5 h-5" />,
    href: '/tools/statute-lookup',
    status: 'coming_soon',
    category: 'analysis',
  },
  {
    id: 'time-calculator',
    name: 'Time Period Calculator',
    description: 'Calculate business days, court days, retrograde periods between any two dates.',
    icon: <Clock className="w-5 h-5" />,
    href: '/tools/time-calculator',
    status: 'coming_soon',
    category: 'calculation',
  },
  {
    id: 'batch-import',
    name: 'Batch Deadline Import',
    description: 'Import deadlines from CSV, Excel, or other docketing systems.',
    icon: <Zap className="w-5 h-5" />,
    href: '/tools/batch-import',
    status: 'coming_soon',
    category: 'export',
  },
];

const CATEGORY_LABELS: Record<string, string> = {
  calculation: 'CALCULATION',
  navigation: 'NAVIGATION',
  analysis: 'ANALYSIS',
  export: 'IMPORT/EXPORT',
};

export default function ToolsHubPage() {
  const router = useRouter();

  const getStatusBadge = (status: Tool['status']) => {
    switch (status) {
      case 'active':
        return <span className="px-2 py-0.5 bg-emerald-900 text-emerald-400 text-xs font-mono">ACTIVE</span>;
      case 'beta':
        return <span className="px-2 py-0.5 bg-amber-900 text-amber-400 text-xs font-mono">BETA</span>;
      case 'coming_soon':
        return <span className="px-2 py-0.5 bg-slate-700 text-slate-400 text-xs font-mono">SOON</span>;
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
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Sparkles className="w-6 h-6 text-cyan-400" />
                <h1 className="text-2xl font-mono font-bold text-white">TOOLS</h1>
              </div>
              <p className="text-slate-400 text-sm font-mono">
                Legal Power Tools for Professional Docketing
              </p>
            </div>
            <div className="text-right">
              <p className="text-slate-500 text-xs font-mono">
                {TOOLS.filter(t => t.status === 'active').length} ACTIVE
                {' / '}
                {TOOLS.filter(t => t.status === 'beta').length} BETA
                {' / '}
                {TOOLS.filter(t => t.status === 'coming_soon').length} COMING
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Quick Access - Active Tools */}
        <section className="mb-12">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-mono text-slate-400 uppercase tracking-wider">Quick Access</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {TOOLS.filter(t => t.status === 'active').map((tool) => (
              <button
                key={tool.id}
                onClick={() => handleToolClick(tool)}
                className="group bg-slate-900 border border-slate-700 hover:border-cyan-600 p-6 text-left transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 bg-slate-800 text-cyan-400 group-hover:bg-cyan-900 transition-colors">
                    {tool.icon}
                  </div>
                  {getStatusBadge(tool.status)}
                </div>
                <h3 className="text-lg font-mono font-semibold text-white mb-2 group-hover:text-cyan-400 transition-colors">
                  {tool.name}
                </h3>
                <p className="text-sm text-slate-400 mb-4">
                  {tool.description}
                </p>
                <div className="flex items-center gap-2 text-cyan-400 text-sm font-mono opacity-0 group-hover:opacity-100 transition-opacity">
                  <span>LAUNCH</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* All Tools by Category */}
        {Object.entries(toolsByCategory).map(([category, tools]) => (
          <section key={category} className="mb-8">
            <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
              <span className="w-8 h-px bg-slate-700" />
              {CATEGORY_LABELS[category]}
              <span className="flex-1 h-px bg-slate-700" />
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {tools.map((tool) => (
                <button
                  key={tool.id}
                  onClick={() => handleToolClick(tool)}
                  disabled={tool.status === 'coming_soon'}
                  className={`group p-4 text-left border transition-all ${
                    tool.status === 'coming_soon'
                      ? 'bg-slate-900/50 border-slate-800 cursor-not-allowed opacity-60'
                      : 'bg-slate-900 border-slate-700 hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className={`${tool.status === 'coming_soon' ? 'text-slate-600' : 'text-slate-400'}`}>
                      {tool.icon}
                    </div>
                    {tool.status === 'coming_soon' && (
                      <Lock className="w-3 h-3 text-slate-600" />
                    )}
                    {tool.status === 'beta' && (
                      <span className="text-xs font-mono text-amber-500">BETA</span>
                    )}
                  </div>
                  <h3 className={`text-sm font-mono font-medium mb-1 ${
                    tool.status === 'coming_soon' ? 'text-slate-500' : 'text-white'
                  }`}>
                    {tool.name}
                  </h3>
                  <p className="text-xs text-slate-500 line-clamp-2">
                    {tool.description}
                  </p>
                </button>
              ))}
            </div>
          </section>
        ))}

        {/* Footer Stats */}
        <footer className="mt-12 pt-8 border-t border-slate-800">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-3xl font-mono font-bold text-white">{TOOLS.length}</p>
              <p className="text-xs font-mono text-slate-500 uppercase">Total Tools</p>
            </div>
            <div>
              <p className="text-3xl font-mono font-bold text-emerald-400">
                {TOOLS.filter(t => t.status === 'active').length}
              </p>
              <p className="text-xs font-mono text-slate-500 uppercase">Active</p>
            </div>
            <div>
              <p className="text-3xl font-mono font-bold text-amber-400">
                {TOOLS.filter(t => t.status === 'beta').length}
              </p>
              <p className="text-xs font-mono text-slate-500 uppercase">In Beta</p>
            </div>
            <div>
              <p className="text-3xl font-mono font-bold text-slate-500">
                {TOOLS.filter(t => t.status === 'coming_soon').length}
              </p>
              <p className="text-xs font-mono text-slate-500 uppercase">Coming Soon</p>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
