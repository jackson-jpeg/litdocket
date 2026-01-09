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
    <header className="cockpit-header">
      {/* Logo & Brand */}
      <div className="flex items-center gap-3">
        <div className="font-serif font-bold text-lg tracking-tight">
          LitDocket
        </div>
        <div className="text-xs text-white/60 font-mono">
          PRO
        </div>
      </div>

      {/* User Menu */}
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-sm text-white/80 font-mono">
              {user.email}
            </span>
            <div className="w-px h-4 bg-white/30" />
            <button
              onClick={handleLogout}
              className="text-sm text-white/80 hover:text-white"
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
