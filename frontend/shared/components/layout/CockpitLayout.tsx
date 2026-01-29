'use client';

/**
 * Cockpit Layout - Paper & Steel Application Shell
 *
 * Fixed Sidebar (dark slate) + Header + Centered Content Area (light)
 * Standard dashboard layout with max-w-7xl content container
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
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-app-bg">
      {/* Top Header Bar */}
      <CockpitHeader />

      {/* Main Body: Sidebar + Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Dark Slate */}
        <Sidebar />

        {/* Main Content Area - Light Background */}
        <main className="flex-1 flex flex-col overflow-hidden bg-app-bg">
          {/* Scrollable Content with max-width and centered */}
          <div className="flex-1 overflow-auto scrollbar-light">
            <div className="max-w-7xl mx-auto p-8">
              {children}
            </div>
          </div>
        </main>
      </div>

      {/* AI Command Bar - Floating overlay, independent of layout */}
      <AITerminal />
    </div>
  );
}

export default CockpitLayout;
