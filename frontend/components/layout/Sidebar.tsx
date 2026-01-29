'use client';

/**
 * Sidebar - Main Navigation
 *
 * Fixed left sidebar with 4 main nav items.
 * Settings subsections appear only on /settings route.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { PendingApprovalsIndicator, PendingApprovalsPanel } from '@/components/audit/PendingApprovalsIndicator';

// Icons
const IconDashboard = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8.354 1.146a.5.5 0 00-.708 0l-6 6A.5.5 0 001.5 7.5v7a.5.5 0 00.5.5h4a.5.5 0 00.5-.5v-4h3v4a.5.5 0 00.5.5h4a.5.5 0 00.5-.5v-7a.5.5 0 00-.146-.354L13 5.793V2.5a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5v1.293L8.354 1.146z"/>
  </svg>
);

const IconCases = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
    <path d="M1 3.5A1.5 1.5 0 012.5 2h3.379a1 1 0 01.707.293L7.707 3.5H13.5A1.5 1.5 0 0115 5v7.5a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12.5v-9z"/>
  </svg>
);

const IconDocket = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
    <path d="M4 0a1 1 0 00-1 1v1H2a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V4a2 2 0 00-2-2h-1V1a1 1 0 00-2 0v1H5V1a1 1 0 00-1-1zM2 6h12v8H2V6z"/>
  </svg>
);

const IconSettings = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 4.754a3.246 3.246 0 100 6.492 3.246 3.246 0 000-6.492zM5.754 8a2.246 2.246 0 114.492 0 2.246 2.246 0 01-4.492 0z"/>
    <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 01-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 01-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 01.52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 011.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 011.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 01.52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 01-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 01-1.255-.52l-.094-.319z"/>
  </svg>
);

const IconTools = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
    <path d="M1 0L0 1l2.2 3.081a1 1 0 00.815.419h.07a1 1 0 01.708.293l2.675 2.675-2.617 2.654A3.003 3.003 0 000 13a3 3 0 105.878-.851l2.654-2.617.968.968-.305.914a1 1 0 00.242 1.023l3.356 3.356a1 1 0 001.414 0l1.586-1.586a1 1 0 000-1.414l-3.356-3.356a1 1 0 00-1.023-.242l-.914.305-.697-.697a1 1 0 00-.293-.708l-2.675-2.675a1 1 0 01-.293-.708v-.07a1 1 0 00-.419-.815L1 0zm9.646 10.646a.5.5 0 01.708 0l2.914 2.915a.5.5 0 01-.707.707l-2.915-2.914a.5.5 0 010-.708zM3 11l.471.242.529.026.287.445.445.287.026.529L5 13l-.242.471-.026.529-.445.287-.287.445-.529.026L3 15l-.471-.242L2 14.732l-.287-.445L1.268 14l-.026-.529L1 13l.242-.471.026-.529.445-.287.287-.445.529-.026L3 11z"/>
  </svg>
);

const mainNavItems = [
  { label: 'Dashboard', href: '/dashboard', icon: <IconDashboard /> },
  { label: 'Cases', href: '/cases', icon: <IconCases /> },
  { label: 'Docket', href: '/calendar', icon: <IconDocket /> },
  { label: 'Tools', href: '/tools', icon: <IconTools /> },
  { label: 'Settings', href: '/settings', icon: <IconSettings /> },
];

const settingsSubsections = [
  { label: 'Notifications', section: 'notifications' },
  { label: 'Preferences', section: 'preferences' },
  { label: 'Rules', section: 'rules' },
  { label: 'Account', section: 'account' },
  { label: 'Integrations', section: 'integrations' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, signOut } = useAuth();
  const isSettingsPage = pathname?.startsWith('/settings');
  const [showPendingPanel, setShowPendingPanel] = useState(false);

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard' || pathname === '/';
    }
    return pathname?.startsWith(href);
  };

  return (
    <aside className="w-[280px] bg-[#001f3f] flex-shrink-0 flex flex-col h-screen">
      {/* Logo */}
      <div className="px-5 py-6">
        <h1 className="text-xl font-bold text-white">LitDocket</h1>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-4">
        <ul className="space-y-1">
          {mainNavItems.map((item) => {
            const active = isActive(item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg text-[15px] font-medium transition-all
                    ${active
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-400 hover:bg-white/10 hover:text-white'
                    }
                  `}
                  aria-current={active ? 'page' : undefined}
                >
                  <span className="flex-shrink-0">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Settings Subsections - only show on /settings */}
        {isSettingsPage && (
          <ul className="mt-4 pt-4 border-t border-white/10 space-y-1">
            {settingsSubsections.map((item) => (
              <li key={item.section}>
                <button
                  className="w-full text-left px-4 py-2.5 text-sm text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-all"
                >
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </nav>

      {/* AI Pending Approvals */}
      <div className="px-4 py-3">
        <PendingApprovalsIndicator
          onViewAll={() => setShowPendingPanel(true)}
          className="w-full justify-center"
        />
      </div>

      {/* User Info */}
      <div className="px-4 py-4 border-t border-white/10">
        <div className="text-sm text-slate-400 truncate mb-2">
          {user?.email || 'Not signed in'}
        </div>
        <button
          onClick={() => signOut()}
          className="text-sm text-slate-500 hover:text-white transition-colors"
        >
          Logout
        </button>
      </div>

      {/* Pending Approvals Panel (Modal) */}
      {showPendingPanel && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <PendingApprovalsPanel
            onClose={() => setShowPendingPanel(false)}
            className="w-full max-w-lg"
          />
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
