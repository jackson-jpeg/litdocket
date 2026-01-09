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

  // Show loading state in Sovereign style
  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-canvas">
        <div className="panel panel-raised p-8 text-center">
          <div className="font-mono text-sm text-ink-secondary mb-2">
            AUTHENTICATING
          </div>
          <div className="w-48 h-1 bg-steel">
            <div className="h-full bg-navy animate-pulse" style={{ width: '60%' }} />
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
