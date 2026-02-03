/**
 * Protected Layout
 *
 * All routes inside this layout require authentication.
 * Uses the Sovereign Cockpit viewport layout with keyboard shortcuts.
 * Includes global Case Assistant chat widget.
 */

'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { CockpitLayout } from '@/components/layout';
import { KeyboardShortcutsProvider } from '@/providers/KeyboardShortcutsProvider';
import CaseChatWidget from '@/components/chat/CaseChatWidget';

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams();

  // Extract caseId from URL params if on a case page
  const caseId = params?.caseId as string | undefined;

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  // Show loading state in Paper & Steel style
  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-app-bg">
        <div className="card p-8 text-center">
          <div className="text-sm text-text-secondary mb-4 font-medium">
            Authenticating...
          </div>
          <div className="w-48 h-1 bg-slate-200 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 animate-pulse" style={{ width: '60%' }} />
          </div>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!user) {
    return null;
  }

  // Authenticated - show the Cockpit with keyboard shortcuts and chat widget
  return (
    <KeyboardShortcutsProvider>
      <CockpitLayout>{children}</CockpitLayout>
      <CaseChatWidget caseId={caseId} />
    </KeyboardShortcutsProvider>
  );
}
