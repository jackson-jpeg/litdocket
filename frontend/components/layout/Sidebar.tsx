'use client';

/**
 * Sidebar - File Explorer Style Navigation
 *
 * Inverted selection (navy background, white text when active)
 * Classic Windows Explorer aesthetic
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

const IconTools = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M1 0L0 1l2.2 3.081a1 1 0 00.815.419h.07a1 1 0 01.708.293l2.675 2.675-2.617 2.654A3.003 3.003 0 004 13a3 3 0 103.88-2.866l2.656-2.617 2.675 2.675a1 1 0 01.293.708v.07a1 1 0 00.419.815L15 16l1-1-2.775-3.565-5.447-5.447L12.344 1.422l-1.414-1.414L6.363 4.574 1.776.987 1 0zM4 15a2 2 0 110-4 2 2 0 010 4z"/>
  </svg>
);

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: <IconDashboard /> },
  { label: 'Cases', href: '/cases', icon: <IconFolder /> },
  { label: 'Calendar', href: '/calendar', icon: <IconCalendar /> },
  { label: 'Tools', href: '/tools', icon: <IconTools /> },
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
    <aside className="sidebar cockpit-sidebar flex flex-col custom-scrollbar">
      {/* System Title */}
      <div className="px-3 py-3 border-b border-grid-line">
        <div className="text-xxs uppercase tracking-widest text-ink-muted">
          Navigation
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 py-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-item ${isActive(item.href) ? 'active' : ''}`}
          >
            <span className="flex-shrink-0">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* System Info Footer */}
      <div className="px-3 py-2 border-t border-grid-line text-xxs text-ink-muted">
        <div>LitDocket v1.0</div>
        <div className="font-mono">SOVEREIGN</div>
      </div>
    </aside>
  );
}

export default Sidebar;
