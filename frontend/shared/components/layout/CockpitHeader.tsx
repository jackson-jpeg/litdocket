'use client';

/**
 * Cockpit Header - Top Navigation Bar
 *
 * Paper & Steel Design System
 * Slate background with clean typography
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
    <header className="h-12 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
      {/* Logo & Brand */}
      <div className="flex items-center gap-4">
        <div className="font-bold text-base tracking-tight text-blue-600">
          LITDOCKET
        </div>
        <div className="text-xs text-slate-500 font-mono">
          {new Date().toLocaleTimeString('en-US', { hour12: false })} EST
        </div>
      </div>

      {/* User Menu */}
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-xs text-slate-600 font-mono">
              {user.email}
            </span>
            <div className="w-px h-4 bg-slate-300" />
            <button
              onClick={handleLogout}
              className="text-xs text-slate-600 hover:text-slate-900 transition-colors px-2 py-1 rounded hover:bg-slate-100"
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
