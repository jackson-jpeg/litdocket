'use client';

/**
 * Jurisdiction Selector Demo Page
 *
 * Test page for the JurisdictionTreeSelector component.
 */

import React, { useState } from 'react';
import { JurisdictionTreeSelector, JurisdictionSelection } from '@/components/jurisdiction';

export default function JurisdictionSelectorPage() {
  const [selection, setSelection] = useState<JurisdictionSelection | null>(null);

  return (
    <div className="min-h-screen bg-surface p-4">
      {/* Page header */}
      <div className="window-frame mb-4">
        <div className="window-titlebar">
          <span className="window-titlebar-text">Jurisdiction Event Tree</span>
        </div>
        <div className="window-content">
          <p className="text-sm text-grey-600">
            CompuLaw-style hierarchical jurisdiction and rule set selector.
            Select a court location to see concurrent rules auto-select.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Selector */}
        <div>
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

        {/* Selection output */}
        <div className="window-frame">
          <div className="window-titlebar">
            <span className="window-titlebar-text">Selection Output</span>
          </div>
          <div className="window-content">
            {selection ? (
              <div className="space-y-4">
                {/* Status */}
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">Status:</span>
                  {selection.isValid ? (
                    <span className="badge-success">Valid</span>
                  ) : (
                    <span className="badge-warning">Has Warnings</span>
                  )}
                </div>

                {/* Active Rule Sets */}
                <div>
                  <h3 className="font-serif font-bold text-sm mb-2">
                    Active Rule Sets ({selection.activeRuleSetIds.length})
                  </h3>
                  {selection.activeRuleSetCodes.length > 0 ? (
                    <div className="panel-inset p-2">
                      <div className="flex flex-wrap gap-1">
                        {selection.activeRuleSetCodes.map((code) => (
                          <span key={code} className="badge-info font-mono">
                            {code}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-grey-500 italic">
                      No rule sets selected
                    </p>
                  )}
                </div>

                {/* User Selected vs Auto-Selected */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-xs font-semibold text-grey-600 uppercase mb-1">
                      User Selected
                    </h4>
                    <p className="font-mono text-sm">
                      {selection.primaryRuleSetIds.length} rule set(s)
                    </p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-grey-600 uppercase mb-1">
                      Auto-Selected (Dependencies)
                    </h4>
                    <p className="font-mono text-sm">
                      {selection.activeRuleSetIds.length - selection.primaryRuleSetIds.length} rule set(s)
                    </p>
                  </div>
                </div>

                {/* Warnings */}
                {selection.warnings.length > 0 && (
                  <div>
                    <h3 className="font-serif font-bold text-sm mb-2">
                      Warnings ({selection.warnings.length})
                    </h3>
                    <div className="space-y-2">
                      {selection.warnings.map((warning, i) => (
                        <div key={i} className="alert-warning">
                          <p className="text-sm font-medium">{warning.message}</p>
                          {warning.suggestedAction && (
                            <p className="text-xs text-grey-600 mt-1">
                              {warning.suggestedAction}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Raw JSON */}
                <div>
                  <h3 className="font-serif font-bold text-sm mb-2">Raw Data</h3>
                  <pre className="panel-inset p-2 text-xs font-mono overflow-x-auto max-h-48">
                    {JSON.stringify(selection, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <p className="text-sm text-grey-500 italic">
                Select jurisdictions or rule sets from the tree to see output here.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="enterprise-card mt-4">
        <div className="enterprise-card-header">
          How It Works
        </div>
        <div className="enterprise-card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <h4 className="font-semibold text-navy mb-1">1. Hierarchical Selection</h4>
              <p className="text-grey-600">
                Navigate: Florida → Federal → Middle District → Bankruptcy
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-navy mb-1">2. Concurrent Rules</h4>
              <p className="text-grey-600">
                Selecting FL:BRMD-7 auto-selects FRCP + FRBP dependencies
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-navy mb-1">3. Smart Warnings</h4>
              <p className="text-grey-600">
                Alerts when selecting local rules without base rules
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
