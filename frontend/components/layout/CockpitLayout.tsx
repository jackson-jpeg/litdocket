'use client';

/**
 * Cockpit Layout - Main Application Shell
 *
 * Fixed Sidebar (280px) + Main Content Area with Breadcrumbs
 * No floating elements - clean integrated layout
 */

import React from 'react';
import { usePathname } from 'next/navigation';
import { EnhancedSidebar } from './EnhancedSidebar';
import { Breadcrumbs } from './Breadcrumbs';
import { AITerminal } from './AITerminal';

interface CockpitLayoutProps {
  children: React.ReactNode;
  /**
   * Optional dynamic labels for breadcrumbs (e.g., case ID to case number mapping)
   */
  breadcrumbLabels?: Record<string, string>;
}

export function CockpitLayout({ children, breadcrumbLabels }: CockpitLayoutProps) {
  const pathname = usePathname();

  // Don't show breadcrumb bar on dashboard/home
  const showBreadcrumbs = pathname !== '/dashboard' && pathname !== '/';

  return (
    <div className="h-screen w-screen overflow-hidden flex bg-paper">
      {/* Fixed Left Sidebar */}
      <EnhancedSidebar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Breadcrumb Bar - Only show when not on dashboard */}
        {showBreadcrumbs && (
          <div className="flex-shrink-0 px-8 py-3 bg-surface border-b border-ink min-h-[48px]">
            <Breadcrumbs dynamicLabels={breadcrumbLabels} />
          </div>
        )}

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
