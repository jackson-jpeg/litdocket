'use client';

/**
 * Calendar Page - DEPRECATED
 *
 * This page has been replaced by the Docket page (/docket).
 * This redirect maintains backward compatibility for bookmarks.
 *
 * @deprecated Use /docket instead
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function CalendarRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/docket');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <p className="text-slate-600 font-mono text-sm">Redirecting to Docket...</p>
    </div>
  );
}
