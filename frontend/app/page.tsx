'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { Loader2, Scale } from 'lucide-react';

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (user) {
        // Logged in - go to dashboard
        router.push('/dashboard');
      } else {
        // Not logged in - go to login
        router.push('/login');
      }
    }
  }, [user, loading, router]);

  // Show loading while checking auth
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50">
      <div className="text-center">
        <Scale className="w-16 h-16 text-blue-600 mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-slate-900 mb-2">LitDocket</h1>
        <div className="flex items-center justify-center gap-2 text-slate-600">
          <Loader2 className="w-5 h-5 animate-spin" />
          <p>Loading...</p>
        </div>
      </div>
    </div>
  );
}
