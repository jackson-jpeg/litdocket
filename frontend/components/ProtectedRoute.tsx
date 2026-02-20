/**
 * Protected Route Component
 *
 * Wraps routes that require authentication.
 * Redirects to login if user is not authenticated.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { Loader2 } from 'lucide-react';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      // Not authenticated - redirect to login
      router.push('/login');
    }
  }, [user, loading, router]);

  // Show loading spinner while checking auth
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50" aria-busy="true">
        <div className="text-center" role="status" aria-label="Authenticating">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-sm text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Not authenticated - show nothing (will redirect)
  if (!user) {
    return null;
  }

  // Authenticated - show the protected content
  return <>{children}</>;
}
