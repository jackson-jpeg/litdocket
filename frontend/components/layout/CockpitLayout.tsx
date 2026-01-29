'use client';

/**
 * Cockpit Layout - Main Application Shell
 *
 * Fixed Sidebar (280px) + Main Content Area
 * No floating elements - clean integrated layout
 */

import React from 'react';
import { Sidebar } from './Sidebar';
import { AITerminal } from './AITerminal';

interface CockpitLayoutProps {
  children: React.ReactNode;
}

export function CockpitLayout({ children }: CockpitLayoutProps) {
  return (
    <div className="h-screen w-screen overflow-hidden flex bg-slate-100">
      {/* Fixed Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Scrollable Content */}
        <div className="flex-1 overflow-auto">
          <div className="p-8">
            {children}
          </div>
        </div>
      </main>

      {/* AI Command Bar */}
      <AITerminal />
    </div>
  );
}

export default CockpitLayout;
