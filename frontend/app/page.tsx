'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { Loader2, Scale } from 'lucide-react';
import { PublicNav } from '@/components/marketing/PublicNav';
import { Footer } from '@/components/marketing/Footer';
import { Hero } from '@/components/marketing/Hero';
import { Features } from '@/components/marketing/Features';
import { Pricing } from '@/components/marketing/Pricing';

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      // Logged in - redirect to dashboard
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  // Show loading while checking auth
  if (loading) {
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

  // Show homepage for unauthenticated users
  if (!user) {
    return (
      <div className="min-h-screen flex flex-col bg-slate-50">
        <PublicNav />
        <main className="flex-1">
          <Hero />
          <Features />
          <Pricing />
        </main>
        <Footer />
      </div>
    );
  }

  // Redirecting to dashboard...
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50">
      <div className="text-center">
        <Scale className="w-16 h-16 text-blue-600 mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-slate-900 mb-2">LitDocket</h1>
        <div className="flex items-center justify-center gap-2 text-slate-600">
          <Loader2 className="w-5 h-5 animate-spin" />
          <p>Redirecting to dashboard...</p>
        </div>
      </div>
    </div>
  );
}
