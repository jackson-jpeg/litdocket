'use client';

/**
 * Header Bar - Clean top bar
 *
 * Minimal header with time and user info.
 * Logo is in the sidebar, not duplicated here.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth/auth-context';
import { useRouter } from 'next/navigation';

export function CockpitHeader() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [time, setTime] = useState('');

  useEffect(() => {
    const updateTime = () => {
      setTime(new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = async () => {
    await signOut();
    router.push('/login');
  };

  return (
    <div className="h-12 px-6 flex items-center justify-between">
      {/* Left: Time */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-500 font-mono tabular-nums">
          {time}
        </span>
      </div>

      {/* Right: User */}
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-sm text-slate-600">
              {user.email}
            </span>
            <button
              onClick={handleLogout}
              className="text-sm text-slate-500 hover:text-slate-900 px-3 py-1 rounded-md hover:bg-slate-100 transition-colors"
            >
              Logout
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default CockpitHeader;
