'use client';

/**
 * Jurisdiction Navigator - CompuLaw-Style Court Selector
 *
 * Gold Standard Design System (matching Dashboard):
 * - Light slate background
 * - White cards with shadows
 * - Rounded corners
 * - Uppercase tracking headers
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
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => router.push('/tools')}
              className="text-slate-400 hover:text-slate-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <GitBranch className="w-5 h-5 text-blue-600" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900">Jurisdiction Navigator</h1>
              <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-mono rounded-full border border-green-200">
                ACTIVE
              </span>
            </div>
          </div>
          <p className="text-slate-500 text-sm">
            CompuLaw-style hierarchical court selector with automatic concurrent rule detection
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Tree Selector */}
          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="bg-slate-100 border-b border-slate-200 px-4 py-3 flex items-center gap-2">
                <Database className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Jurisdiction Tree</span>
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
            <div className="bg-white border border-slate-200 p-4 rounded-lg">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">How to Use</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-blue-600 font-bold">1.</span>
                  <span className="text-slate-600">Navigate: Federal → Middle District → Bankruptcy</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-600 font-bold">2.</span>
                  <span className="text-slate-600">Select court location to auto-select concurrent rules</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-600 font-bold">3.</span>
                  <span className="text-slate-600">Dependencies (FRCP, FRBP) are locked automatically</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Selection Output */}
          <div className="space-y-4">
            {selection ? (
              <>
                {/* Status */}
                <div className={`p-4 border flex items-start gap-3 rounded-lg ${
                  selection.isValid
                    ? 'bg-green-50 border-green-200'
                    : 'bg-amber-50 border-amber-200'
                }`}>
                  {selection.isValid ? (
                    <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className={`font-medium text-sm ${
                      selection.isValid ? 'text-green-700' : 'text-amber-700'
                    }`}>
                      {selection.isValid ? 'Selection Valid' : 'Warnings Detected'}
                    </p>
                    <p className={`text-sm ${
                      selection.isValid ? 'text-green-600' : 'text-amber-600'
                    }`}>
                      {selection.activeRuleSetIds.length} rule sets active
                    </p>
                  </div>
                </div>

                {/* Active Rule Sets */}
                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="bg-slate-100 border-b border-slate-200 px-4 py-2 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                      Active Rule Sets ({selection.activeRuleSetIds.length})
                    </span>
                    <Scale className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="p-4">
                    {selection.activeRuleSetCodes.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {selection.activeRuleSetCodes.map((code) => (
                          <span
                            key={code}
                            className="px-2 py-1 bg-blue-50 text-blue-700 font-mono text-xs border border-blue-200 rounded"
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
                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="bg-slate-100 border-b border-slate-200 px-4 py-2">
                    <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Selection Breakdown</span>
                  </div>
                  <div className="p-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-50 rounded-lg p-3">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">User Selected</p>
                        <p className="text-2xl font-bold text-slate-900">
                          {selection.primaryRuleSetIds.length}
                        </p>
                        <p className="text-xs text-slate-500">rule sets</p>
                      </div>
                      <div className="bg-blue-50 rounded-lg p-3">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Auto-Selected</p>
                        <p className="text-2xl font-bold text-blue-600">
                          {selection.activeRuleSetIds.length - selection.primaryRuleSetIds.length}
                        </p>
                        <p className="text-xs text-slate-500">dependencies</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Warnings */}
                {selection.warnings.length > 0 && (
                  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <span className="text-xs font-bold text-amber-700 uppercase tracking-wider">
                        Warnings ({selection.warnings.length})
                      </span>
                    </div>
                    <div className="p-4 space-y-3">
                      {selection.warnings.map((warning, i) => (
                        <div key={i} className="border-l-2 border-amber-400 pl-3 py-1">
                          <p className="text-sm text-amber-700">{warning.message}</p>
                          {warning.suggestedAction && (
                            <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                              <ChevronRight className="w-3 h-3" /> {warning.suggestedAction}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Raw JSON (collapsed) */}
                <details className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <summary className="bg-slate-100 border-b border-slate-200 px-4 py-2 cursor-pointer">
                    <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Raw Data</span>
                  </summary>
                  <div className="p-4">
                    <pre className="bg-slate-50 p-3 text-xs font-mono text-slate-600 overflow-x-auto max-h-48 rounded">
                      {JSON.stringify(selection, null, 2)}
                    </pre>
                  </div>
                </details>
              </>
            ) : (
              /* Empty State */
              <div className="bg-white border border-slate-200 p-12 text-center rounded-xl">
                <div className="w-16 h-16 mx-auto bg-slate-100 rounded-full flex items-center justify-center mb-4">
                  <GitBranch className="w-8 h-8 text-slate-400" />
                </div>
                <p className="text-slate-600 font-medium">
                  Select jurisdictions from the tree
                </p>
                <p className="text-slate-400 text-sm mt-2">
                  Selection data will appear here
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Feature Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-3">
              <GitBranch className="w-5 h-5 text-blue-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Hierarchical Navigation</h3>
            <p className="text-xs text-slate-500">
              Navigate: Florida → Federal → Middle District → Bankruptcy Court
            </p>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center mb-3">
              <Database className="w-5 h-5 text-amber-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Concurrent Rules</h3>
            <p className="text-xs text-slate-500">
              Selecting FL:BRMD-7 auto-selects FRCP + FRBP dependencies
            </p>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center mb-3">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Smart Warnings</h3>
            <p className="text-xs text-slate-500">
              Alerts when selecting local rules without required base rules
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
