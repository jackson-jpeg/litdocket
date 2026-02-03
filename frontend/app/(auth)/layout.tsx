/**
 * Auth Layout
 *
 * Shared layout for authentication pages (login, signup, etc.)
 */

import React from 'react';
import { Scale } from 'lucide-react';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-lg mb-4">
            <Scale className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">LitDocket</h1>
          <p className="text-slate-600">AI-Powered Legal Docketing</p>
        </div>

        {/* Auth form content */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {children}
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-slate-500 mt-6">
          © {new Date().getFullYear()} LitDocket. All rights reserved.
        </p>
      </div>
    </div>
  );
}
