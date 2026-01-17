'use client';

/**
 * Cockpit Layout - Fixed Viewport Container
 *
 * The Sovereign Design System's primary layout.
 * h-screen w-screen overflow-hidden - no page scrolling.
 */

import React from 'react';
import { CockpitHeader } from './CockpitHeader';
import { Sidebar } from './Sidebar';
import { AITerminal } from './AITerminal';

interface CockpitLayoutProps {
  children: React.ReactNode;
}

export function CockpitLayout({ children }: CockpitLayoutProps) {
  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-terminal-bg">
      {/* Top Header Bar */}
      <CockpitHeader />

      {/* Main Body: Sidebar + Content + Terminal */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Scrollable Content */}
          <div className="flex-1 overflow-auto p-6 scrollbar-dark">
            {children}
          </div>

          {/* AI Terminal (bottom) */}
          <AITerminal />
        </main>
      </div>
    </div>
  );
}

export default CockpitLayout;
