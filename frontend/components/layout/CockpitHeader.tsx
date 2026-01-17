'use client';

/**
 * Cockpit Header - Top Navigation Bar
 *
 * Navy background, white text
 * Logo + user menu
 */

import React from 'react';
import { useAuth } from '@/lib/auth/auth-context';
import { useRouter } from 'next/navigation';

export function CockpitHeader() {
  const { user, signOut } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await signOut();
    router.push('/login');
  };

  return (
    <header className="h-12 bg-terminal-surface border-b border-border-subtle flex items-center justify-between px-4 flex-shrink-0">
      {/* Logo & Brand */}
      <div className="flex items-center gap-4">
        <div className="font-tight font-bold text-base tracking-tight text-accent-info">
          LITDOCKET
        </div>
        <div className="text-xs text-text-muted font-mono">
          {new Date().toLocaleTimeString('en-US', { hour12: false })} EST
        </div>
      </div>

      {/* User Menu */}
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-xs text-text-secondary font-mono">
              {user.email}
            </span>
            <div className="w-px h-4 bg-border-subtle" />
            <button
              onClick={handleLogout}
              className="text-xs text-text-secondary hover:text-text-primary transition-colors px-2 py-1 rounded hover:bg-terminal-elevated"
            >
              Logout
            </button>
          </>
        )}
      </div>
    </header>
  );
}

export default CockpitHeader;
