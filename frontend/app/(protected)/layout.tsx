/**
 * Protected Layout
 *
 * All routes inside this layout require authentication.
 * Uses the Sovereign Cockpit viewport layout with keyboard shortcuts.
 * AI Terminal (Cmd+K) is included via CockpitLayout.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { CockpitLayout } from '@/components/layout';
import { KeyboardShortcutsProvider } from '@/providers/KeyboardShortcutsProvider';

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

  // Show loading state in Paper & Steel style
  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-paper">
        <div className="card p-8 text-center">
          <div className="text-sm font-mono text-ink-secondary mb-4">
            <span className="loading-terminal">AUTHENTICATING</span>
          </div>
          <div className="w-48 h-1 bg-surface border border-ink/20 overflow-hidden">
            <div className="h-full bg-steel animate-pulse" style={{ width: '60%' }} />
          </div>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!user) {
    return null;
  }

  // Authenticated - show the Cockpit with keyboard shortcuts
  // AI Terminal (Cmd+K) is included via CockpitLayout
  return (
    <KeyboardShortcutsProvider>
      <CockpitLayout>{children}</CockpitLayout>
    </KeyboardShortcutsProvider>
  );
}
