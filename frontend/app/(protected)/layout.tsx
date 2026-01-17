/**
 * Protected Layout
 *
 * All routes inside this layout require authentication.
 * Uses the Sovereign Cockpit viewport layout.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { CockpitLayout } from '@/components/layout';

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  // Show loading state in Bloomberg Terminal style
  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-terminal-bg">
        <div className="panel-glass p-8 text-center">
          <div className="font-mono text-sm text-text-secondary mb-4 uppercase tracking-wide">
            AUTHENTICATING
          </div>
          <div className="w-48 h-1 bg-terminal-elevated rounded-full overflow-hidden">
            <div className="h-full bg-accent-info animate-pulse" style={{ width: '60%' }} />
          </div>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!user) {
    return null;
  }

  // Authenticated - show the Cockpit
  return <CockpitLayout>{children}</CockpitLayout>;
}
