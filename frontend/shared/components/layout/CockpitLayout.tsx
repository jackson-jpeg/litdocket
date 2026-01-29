'use client';

/**
 * Cockpit Layout - Clean Application Shell
 *
 * BULLETPROOF layout using fixed positioning for sidebar:
 * - Fixed sidebar (256px) on left
 * - Main content offset with margin-left
 * - No complex nested flex containers
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
    <div className="min-h-screen bg-slate-100">
      {/* Fixed Sidebar - Always visible on left */}
      <div className="fixed inset-y-0 left-0 w-64 z-40">
        <Sidebar />
      </div>

      {/* Main Area - Offset by sidebar width */}
      <div className="pl-64">
        {/* Top Header */}
        <header className="sticky top-0 z-30 bg-white border-b border-slate-200">
          <CockpitHeader />
        </header>

        {/* Page Content */}
        <main className="min-h-[calc(100vh-48px)]">
          <div className="max-w-7xl mx-auto px-8 py-6">
            {children}
          </div>
        </main>
      </div>

      {/* AI Command Bar - Floating overlay */}
      <AITerminal />
    </div>
  );
}

export default CockpitLayout;
