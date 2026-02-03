'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Scale, Menu, X } from 'lucide-react';

export function PublicNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="bg-white border-b border-slate-200">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center">
                <Scale className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-slate-900">LitDocket</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <Link href="/pricing" className="text-slate-600 hover:text-slate-900 font-medium">
              Pricing
            </Link>
            <Link href="/terms" className="text-slate-600 hover:text-slate-900 font-medium">
              Terms
            </Link>
            <Link href="/privacy" className="text-slate-600 hover:text-slate-900 font-medium">
              Privacy
            </Link>
            <div className="flex items-center gap-3 ml-4">
              <Link
                href="/login"
                className="px-4 py-2 text-slate-700 font-medium hover:text-slate-900"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Start Free Trial
              </Link>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:bg-slate-100"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-slate-200">
            <div className="flex flex-col gap-4">
              <Link
                href="/pricing"
                className="text-slate-600 hover:text-slate-900 font-medium py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Pricing
              </Link>
              <Link
                href="/terms"
                className="text-slate-600 hover:text-slate-900 font-medium py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Terms
              </Link>
              <Link
                href="/privacy"
                className="text-slate-600 hover:text-slate-900 font-medium py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Privacy
              </Link>
              <div className="flex flex-col gap-3 pt-4 border-t border-slate-200">
                <Link
                  href="/login"
                  className="w-full px-4 py-2 text-center text-slate-700 font-medium border border-slate-300 rounded-lg hover:bg-slate-50"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Log in
                </Link>
                <Link
                  href="/signup"
                  className="w-full px-4 py-2 text-center bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Start Free Trial
                </Link>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
