'use client';

/**
 * Sidebar - Paper & Steel Navigation
 *
 * Dark slate background (slate-900) with professional navigation
 * Active state: slate-800 + blue left border + white text
 * Inactive state: slate-400 text with hover to slate-200
 */

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  children?: NavItem[];
}

// Simple icon components
const IconFolder = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M1 3.5A1.5 1.5 0 012.5 2h3.379a1 1 0 01.707.293L7.707 3.5H13.5A1.5 1.5 0 0115 5v7.5a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12.5v-9z"/>
  </svg>
);

const IconCalendar = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M4 0a1 1 0 00-1 1v1H2a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V4a2 2 0 00-2-2h-1V1a1 1 0 00-2 0v1H5V1a1 1 0 00-1-1zM2 6h12v8H2V6z"/>
  </svg>
);

const IconDashboard = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M0 2a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2H2a2 2 0 01-2-2V2zm4 0v6h8V2H4zm8 8H4v4h8v-4zM2 2v2h2V2H2zm0 4v2h2V6H2zm0 4v4h2v-4H2z"/>
  </svg>
);

const IconSettings = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 4.754a3.246 3.246 0 100 6.492 3.246 3.246 0 000-6.492zM5.754 8a2.246 2.246 0 114.492 0 2.246 2.246 0 01-4.492 0z"/>
    <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 01-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 01-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 01.52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 011.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 011.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 01.52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 01-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 01-1.255-.52l-.094-.319z"/>
  </svg>
);

// Docket icon (clipboard with list)
const IconDocket = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M4 1.5H3a2 2 0 00-2 2V14a2 2 0 002 2h10a2 2 0 002-2V3.5a2 2 0 00-2-2h-1v1h1a1 1 0 011 1V14a1 1 0 01-1 1H3a1 1 0 01-1-1V3.5a1 1 0 011-1h1v-1z"/>
    <path d="M9.5 1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-3a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h3zm-3-1A1.5 1.5 0 005 1.5v1A1.5 1.5 0 006.5 4h3A1.5 1.5 0 0011 2.5v-1A1.5 1.5 0 009.5 0h-3z"/>
    <path d="M4.5 6a.5.5 0 000 1h7a.5.5 0 000-1h-7zm0 3a.5.5 0 000 1h7a.5.5 0 000-1h-7zm0 3a.5.5 0 000 1h4a.5.5 0 000-1h-4z"/>
  </svg>
);

/**
 * Navigation Items
 *
 * Streamlined from 6 to 4 items:
 * - Dashboard: Morning report
 * - Cases: Case management + triggers
 * - Docket: Cross-case deadline management (replaces Calendar)
 * - Settings: User preferences + Rules management
 *
 * Tools and Rules Builder are now accessible through:
 * - Tools -> Case Detail / Trigger Entry
 * - Rules -> Settings/Rules tab
 */
const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: <IconDashboard /> },
  { label: 'Cases', href: '/cases', icon: <IconFolder /> },
  { label: 'Docket', href: '/docket', icon: <IconDocket /> },
  { label: 'Settings', href: '/settings', icon: <IconSettings /> },
];

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard' || pathname === '/';
    }
    return pathname.startsWith(href);
  };

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex-shrink-0 flex flex-col overflow-y-auto scrollbar-light">
      {/* Logo/Branding */}
      <div className="px-4 py-6 border-b border-slate-800">
        <h1 className="text-xl font-bold text-white">LitDocket</h1>
        <p className="text-xs text-slate-400 mt-1">Legal Docketing</p>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                ${active
                  ? 'bg-slate-800 text-white border-l-4 border-blue-500 pl-2.5'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }
              `}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* System Info Footer */}
      <div className="p-4 border-t border-slate-800">
        <div className="text-xs text-slate-500 font-mono">v4.0.0</div>
      </div>
    </aside>
  );
}

export default Sidebar;
