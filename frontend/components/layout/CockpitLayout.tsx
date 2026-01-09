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
    <div className="cockpit">
      {/* Top Header Bar */}
      <CockpitHeader />

      {/* Main Body: Sidebar + Content + Terminal */}
      <div className="cockpit-body">
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="cockpit-main">
          {/* Scrollable Content */}
          <div className="cockpit-content custom-scrollbar">
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
