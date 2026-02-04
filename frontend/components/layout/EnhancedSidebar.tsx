'use client';

/**
 * EnhancedSidebar - Main Navigation with Tools and Recent Cases
 *
 * Three sections:
 * 1. Core navigation (Dashboard, Cases, Docket)
 * 2. Tools quick access (Calculator, Jurisdiction, Doc Analyzer, Authority)
 * 3. Recent cases (last 5 viewed)
 *
 * Includes keyboard shortcut hints and help button.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { useRecentCases } from '@/hooks/useRecentItems';
import { useKeyboardShortcuts } from '@/providers/KeyboardShortcutsProvider';
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

const IconCalculator = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M2 2a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V2zm2 .5v2a.5.5 0 00.5.5h7a.5.5 0 00.5-.5v-2a.5.5 0 00-.5-.5h-7a.5.5 0 00-.5.5zm0 4v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5zM4.5 9a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM4 12.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5zM7.5 6a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM7 9.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5zm.5 2.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM10 6.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5zm.5 2.5a.5.5 0 00-.5.5v4a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-4a.5.5 0 00-.5-.5h-1z"/>
  </svg>
);

const IconJurisdiction = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM2.04 4.326c.325 1.329 2.532 2.54 3.717 3.19.48.263.793.434.743.484-.08.08-.162.158-.242.234-.416.396-.787.749-.758 1.266.035.634.618.824 1.214 1.017.577.188 1.168.38 1.286.983.082.417-.075.988-.22 1.52-.215.782-.406 1.48.22 1.48 1.5-.5 3.798-3.186 4-5 .138-1.243-2-2-3.5-2.5-.478-.16-.755.081-.99.284-.172.15-.322.279-.51.216-.445-.148-2.5-2-1.5-2.5.78-.39.952-.171 1.227.182.078.099.163.208.273.318.609.304.662-.132.723-.633.039-.322.081-.671.277-.867.434-.434 1.265-.791 2.028-1.12.712-.306 1.365-.587 1.579-.88A7 7 0 102.04 4.327z"/>
  </svg>
);

const IconDocument = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M4 0a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V4.414a2 2 0 00-.586-1.414l-2.414-2.414A2 2 0 009.586 0H4zm5 1v3a1 1 0 001 1h3l-4-4z"/>
  </svg>
);

const IconAuthority = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8.186 1.113a.5.5 0 00-.372 0L1.846 3.5l2.404.961L10.404 2l-2.218-.887zm3.564 1.426L5.596 5 8 5.961 14.154 3.5l-2.404-.961zm3.25 1.7l-6.5 2.6v7.922l6.5-2.6V4.24zM7.5 14.762V6.838L1 4.239v7.923l6.5 2.6zM7.443.184a1.5 1.5 0 011.114 0l7.129 2.852A.5.5 0 0116 3.5v8.662a1 1 0 01-.629.928l-7.185 2.874a.5.5 0 01-.372 0L.63 13.09a1 1 0 01-.63-.928V3.5a.5.5 0 01.314-.464L7.443.184z"/>
  </svg>
);

const IconSettings = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 4.754a3.246 3.246 0 100 6.492 3.246 3.246 0 000-6.492zM5.754 8a2.246 2.246 0 114.492 0 2.246 2.246 0 01-4.492 0z"/>
    <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 01-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 01-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 01.52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 011.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 011.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 01.52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 01-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 01-1.255-.52l-.094-.319z"/>
  </svg>
);

const IconHelp = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 15A7 7 0 118 1a7 7 0 010 14zm0 1A8 8 0 108 0a8 8 0 000 16z"/>
    <path d="M5.255 5.786a.237.237 0 00.241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 00.25.246h.811a.25.25 0 00.25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
  </svg>
);

const IconChevron = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
    <path d="M4.646 1.646a.5.5 0 01.708 0l6 6a.5.5 0 010 .708l-6 6a.5.5 0 01-.708-.708L10.293 8 4.646 2.354a.5.5 0 010-.708z"/>
  </svg>
);

const IconTools = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M1 0L0 1l2.2 3.081a1 1 0 00.815.419h.07a1 1 0 01.708.293l2.675 2.675-2.617 2.654A3.003 3.003 0 000 13a3 3 0 105.878-.851l2.654-2.617.968.968-.305.914a1 1 0 00.242 1.023l3.356 3.356a1 1 0 001.414 0l1.586-1.586a1 1 0 000-1.414l-3.356-3.356a1 1 0 00-1.023-.242l-.914.305-.697-.697a1 1 0 00-.293-.708l-2.675-2.675a1 1 0 01-.293-.708v-.07a1 1 0 00-.419-.815L1 0zm9.646 10.646a.5.5 0 01.708 0l2.914 2.915a.5.5 0 01-.707.707l-2.915-2.914a.5.5 0 010-.708zM3 11l.471.242.529.026.287.445.445.287.026.529L5 13l-.242.471-.026.529-.445.287-.287.445-.529.026L3 15l-.471-.242L2 14.732l-.287-.445L1.268 14l-.026-.529L1 13l.242-.471.026-.529.445-.287.287-.445.529-.026L3 11z"/>
  </svg>
);

const IconBrain = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-4h2v2h-2v-2zm0-2h2c0-3.25 3-3 3-5 0-1.66-1.34-3-3-3S9 7.34 9 9h2c0-.55.45-1 1-1s1 .45 1 1c0 1.25-3 1.125-3 5z"/>
  </svg>
);

// Primary navigation - core daily workflow
const primaryNavItems = [
  { label: 'Dashboard', href: '/dashboard', icon: <IconDashboard />, shortcut: '⌘H' },
  { label: 'Cases', href: '/cases', icon: <IconCases />, shortcut: '⌘⇧C' },
  { label: 'Docket', href: '/calendar', icon: <IconDocket />, shortcut: '⌘D' },
];

// Utilities - tools and analyzers
const utilityItems = [
  { label: 'Calculator', href: '/tools/deadline-calculator', icon: <IconCalculator /> },
  { label: 'Analyzer', href: '/tools/document-analyzer', icon: <IconDocument /> },
  { label: 'Rules', href: '/tools/authority-core', icon: <IconAuthority /> },
  { label: 'Intelligence', href: '/intelligence', icon: <IconBrain /> },
];

export function EnhancedSidebar() {
  const pathname = usePathname();
  const { user, signOut } = useAuth();
  const { recentCases } = useRecentCases();
  const { setShowShortcutsModal } = useKeyboardShortcuts();
  const [showPendingPanel, setShowPendingPanel] = useState(false);

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard' || pathname === '/';
    }
    if (href === '/cases') {
      return pathname === '/cases' || pathname?.startsWith('/cases/');
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
      <nav className="flex-1 px-4 overflow-y-auto">
        {/* Primary Navigation */}
        <div className="mb-6">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 mb-2">
            Primary
          </div>
          <ul className="space-y-1">
            {primaryNavItems.map((item) => {
              const active = isActive(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`
                      flex items-center justify-between px-4 py-2.5 rounded-lg text-[14px] font-medium transition-all
                      ${active
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-400 hover:bg-white/10 hover:text-white'
                      }
                    `}
                    aria-current={active ? 'page' : undefined}
                  >
                    <span className="flex items-center gap-3">
                      <span className="flex-shrink-0">{item.icon}</span>
                      <span>{item.label}</span>
                    </span>
                    {item.shortcut && (
                      <kbd className="text-[10px] font-mono opacity-60">{item.shortcut}</kbd>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Utilities Section */}
        <div className="mb-6">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 mb-2">
            Utilities
          </div>
          <ul className="space-y-1">
            {utilityItems.map((item) => {
              const active = isActive(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`
                      flex items-center gap-3 px-4 py-2 rounded-lg text-[13px] font-medium transition-all
                      ${active
                        ? 'bg-blue-600/80 text-white'
                        : 'text-slate-400 hover:bg-white/10 hover:text-white'
                      }
                    `}
                    aria-current={active ? 'page' : undefined}
                  >
                    <span className="flex-shrink-0 opacity-80">{item.icon}</span>
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Recent Cases Section */}
        {recentCases.length > 0 && (
          <div className="mb-6">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 mb-2">
              Recent Cases
            </div>
            <ul className="space-y-1">
              {recentCases.slice(0, 5).map((caseItem) => (
                <li key={caseItem.id}>
                  <Link
                    href={`/cases/${caseItem.id}`}
                    className={`
                      flex items-center gap-3 px-4 py-2 rounded-lg text-[13px] transition-all group
                      ${pathname === `/cases/${caseItem.id}`
                        ? 'bg-blue-600/60 text-white'
                        : 'text-slate-400 hover:bg-white/10 hover:text-white'
                      }
                    `}
                    title={caseItem.title}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 flex-shrink-0" />
                    <span className="truncate flex-1">
                      {caseItem.case_number || caseItem.title}
                    </span>
                    <IconChevron />
                  </Link>
                </li>
              ))}
              <li>
                <Link
                  href="/cases"
                  className="flex items-center gap-3 px-4 py-2 rounded-lg text-[12px] text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all"
                >
                  <span className="w-1.5" />
                  <span>View all →</span>
                </Link>
              </li>
            </ul>
          </div>
        )}
      </nav>

      {/* Bottom Section */}
      <div className="px-4 py-3 space-y-2 border-t border-white/10">
        {/* AI Pending Approvals */}
        <PendingApprovalsIndicator
          onViewAll={() => setShowPendingPanel(true)}
          className="w-full justify-center"
        />

        {/* Keyboard Shortcuts Help */}
        <button
          onClick={() => setShowShortcutsModal(true)}
          className="w-full flex items-center justify-between px-4 py-2 rounded-lg text-[13px] text-slate-400 hover:bg-white/10 hover:text-white transition-all"
        >
          <span className="flex items-center gap-3">
            <IconHelp />
            <span>Shortcuts</span>
          </span>
          <kbd className="text-[10px] font-mono opacity-50">⌘/</kbd>
        </button>

        {/* Settings */}
        <Link
          href="/settings"
          className={`
            flex items-center gap-3 px-4 py-2 rounded-lg text-[13px] transition-all
            ${pathname?.startsWith('/settings')
              ? 'bg-blue-600/80 text-white'
              : 'text-slate-400 hover:bg-white/10 hover:text-white'
            }
          `}
        >
          <IconSettings />
          <span>Settings</span>
        </Link>
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

export default EnhancedSidebar;
