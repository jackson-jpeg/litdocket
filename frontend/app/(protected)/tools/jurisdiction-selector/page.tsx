'use client';

/**
 * Jurisdiction Navigator - CompuLaw-Style Court Selector
 *
 * Sovereign Design System:
 * - Dark terminal aesthetic
 * - Dense hierarchical tree display
 * - Zero radius
 */

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { JurisdictionTreeSelector, JurisdictionSelection } from '@/components/jurisdiction';
import {
  GitBranch,
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  ChevronRight,
  Database,
  Scale,
} from 'lucide-react';

export default function JurisdictionSelectorPage() {
  const router = useRouter();
  const [selection, setSelection] = useState<JurisdictionSelection | null>(null);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => router.push('/tools')}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <GitBranch className="w-6 h-6 text-cyan-400" />
              <h1 className="text-2xl font-mono font-bold">JURISDICTION NAVIGATOR</h1>
              <span className="px-2 py-0.5 bg-emerald-900 text-emerald-400 text-xs font-mono">ACTIVE</span>
            </div>
          </div>
          <p className="text-slate-400 text-sm font-mono">
            CompuLaw-style hierarchical court selector with automatic concurrent rule detection
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Tree Selector */}
          <div className="space-y-4">
            <div className="bg-slate-900 border border-slate-700">
              <div className="bg-slate-800 border-b border-slate-700 px-4 py-3 flex items-center gap-2">
                <Database className="w-4 h-4 text-cyan-400" />
                <span className="font-mono text-sm text-slate-300">JURISDICTION TREE</span>
              </div>
              <div className="p-4">
                <JurisdictionTreeSelector
                  value={selection || undefined}
                  onChange={setSelection}
                  showDependencyBadges={true}
                  showRuleCounts={true}
                  expandedByDefault={false}
                  maxHeight="500px"
                  onValidationWarning={(warnings) => {
                    if (warnings.length > 0) {
                      console.log('Validation warnings:', warnings);
                    }
                  }}
                />
              </div>
            </div>

            {/* Instructions */}
            <div className="bg-slate-900 border border-slate-700 p-4">
              <h3 className="font-mono text-xs text-slate-500 uppercase mb-3">HOW TO USE</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-cyan-400 font-mono">1.</span>
                  <span className="text-slate-300">Navigate: Federal → Middle District → Bankruptcy</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-cyan-400 font-mono">2.</span>
                  <span className="text-slate-300">Select court location to auto-select concurrent rules</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-cyan-400 font-mono">3.</span>
                  <span className="text-slate-300">Dependencies (FRCP, FRBP) are locked automatically</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Selection Output */}
          <div className="space-y-4">
            {selection ? (
              <>
                {/* Status */}
                <div className={`p-4 border flex items-start gap-3 ${
                  selection.isValid
                    ? 'bg-emerald-900/30 border-emerald-800'
                    : 'bg-amber-900/30 border-amber-800'
                }`}>
                  {selection.isValid ? (
                    <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className={`font-mono text-sm ${
                      selection.isValid ? 'text-emerald-400' : 'text-amber-400'
                    }`}>
                      {selection.isValid ? 'SELECTION VALID' : 'WARNINGS DETECTED'}
                    </p>
                    <p className={`text-sm ${
                      selection.isValid ? 'text-emerald-300' : 'text-amber-300'
                    }`}>
                      {selection.activeRuleSetIds.length} rule sets active
                    </p>
                  </div>
                </div>

                {/* Active Rule Sets */}
                <div className="bg-slate-900 border border-slate-700">
                  <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 flex items-center justify-between">
                    <span className="font-mono text-sm text-slate-300">
                      ACTIVE RULE SETS ({selection.activeRuleSetIds.length})
                    </span>
                    <Scale className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="p-4">
                    {selection.activeRuleSetCodes.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {selection.activeRuleSetCodes.map((code) => (
                          <span
                            key={code}
                            className="px-2 py-1 bg-slate-800 text-cyan-400 font-mono text-xs border border-slate-700"
                          >
                            {code}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">No rule sets selected</p>
                    )}
                  </div>
                </div>

                {/* Selection Breakdown */}
                <div className="bg-slate-900 border border-slate-700">
                  <div className="bg-slate-800 border-b border-slate-700 px-4 py-2">
                    <span className="font-mono text-sm text-slate-300">SELECTION BREAKDOWN</span>
                  </div>
                  <div className="p-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-mono text-slate-500 uppercase mb-1">User Selected</p>
                        <p className="text-2xl font-mono font-bold text-white">
                          {selection.primaryRuleSetIds.length}
                        </p>
                        <p className="text-xs text-slate-400">rule sets</p>
                      </div>
                      <div>
                        <p className="text-xs font-mono text-slate-500 uppercase mb-1">Auto-Selected</p>
                        <p className="text-2xl font-mono font-bold text-cyan-400">
                          {selection.activeRuleSetIds.length - selection.primaryRuleSetIds.length}
                        </p>
                        <p className="text-xs text-slate-400">dependencies</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Warnings */}
                {selection.warnings.length > 0 && (
                  <div className="bg-slate-900 border border-slate-700">
                    <div className="bg-amber-900/50 border-b border-amber-800 px-4 py-2 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      <span className="font-mono text-sm text-amber-300">
                        WARNINGS ({selection.warnings.length})
                      </span>
                    </div>
                    <div className="p-4 space-y-3">
                      {selection.warnings.map((warning, i) => (
                        <div key={i} className="border-l-2 border-amber-600 pl-3 py-1">
                          <p className="text-sm text-amber-200">{warning.message}</p>
                          {warning.suggestedAction && (
                            <p className="text-xs text-slate-400 mt-1">
                              <ChevronRight className="w-3 h-3 inline" /> {warning.suggestedAction}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Raw JSON (collapsed) */}
                <details className="bg-slate-900 border border-slate-700">
                  <summary className="bg-slate-800 border-b border-slate-700 px-4 py-2 cursor-pointer">
                    <span className="font-mono text-sm text-slate-300">RAW DATA</span>
                  </summary>
                  <div className="p-4">
                    <pre className="bg-slate-800 p-3 text-xs font-mono text-slate-300 overflow-x-auto max-h-48">
                      {JSON.stringify(selection, null, 2)}
                    </pre>
                  </div>
                </details>
              </>
            ) : (
              /* Empty State */
              <div className="bg-slate-900 border border-slate-700 p-12 text-center">
                <GitBranch className="w-16 h-16 text-slate-700 mx-auto mb-4" />
                <p className="text-slate-500 font-mono text-sm">
                  Select jurisdictions from the tree
                </p>
                <p className="text-slate-600 font-mono text-xs mt-2">
                  Selection data will appear here
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Feature Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4">
            <GitBranch className="w-5 h-5 text-cyan-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Hierarchical Navigation</h3>
            <p className="text-xs text-slate-400">
              Navigate: Florida → Federal → Middle District → Bankruptcy Court
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4">
            <Database className="w-5 h-5 text-amber-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Concurrent Rules</h3>
            <p className="text-xs text-slate-400">
              Selecting FL:BRMD-7 auto-selects FRCP + FRBP dependencies
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4">
            <AlertTriangle className="w-5 h-5 text-rose-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Smart Warnings</h3>
            <p className="text-xs text-slate-400">
              Alerts when selecting local rules without required base rules
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
