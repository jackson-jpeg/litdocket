'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Scale, Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function PublicNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close menu on ESC key
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && mobileMenuOpen) {
      setMobileMenuOpen(false);
    }
  }, [mobileMenuOpen]);

  // Lock body scroll when menu is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', handleKeyDown);
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [mobileMenuOpen, handleKeyDown]);

  const closeMenu = () => setMobileMenuOpen(false);

  return (
    <header className="bg-white border-b border-slate-200">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-9 h-9 bg-steel flex items-center justify-center">
                <Scale className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-ink">LitDocket</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <Link href="/pricing" className="text-ink-secondary hover:text-ink font-medium">
              Pricing
            </Link>
            <Link href="/terms" className="text-ink-secondary hover:text-ink font-medium">
              Terms
            </Link>
            <Link href="/privacy" className="text-ink-secondary hover:text-ink font-medium">
              Privacy
            </Link>
            <div className="flex items-center gap-3 ml-4">
              <Link
                href="/login"
                className="px-4 py-2 text-ink font-medium hover:text-ink-secondary"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="px-4 py-2 bg-steel text-white font-medium hover:bg-steel-light transition-colors"
              >
                Start Free Trial
              </Link>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-ink-secondary hover:bg-surface"
              aria-expanded={mobileMenuOpen}
              aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Navigation Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/50 z-40 md:hidden"
              onClick={closeMenu}
              aria-hidden="true"
            />

            {/* Drawer */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'tween', duration: 0.3 }}
              className="fixed top-0 right-0 bottom-0 w-80 max-w-[calc(100vw-3rem)] bg-white z-50 md:hidden shadow-modal"
            >
              {/* Drawer Header */}
              <div className="flex items-center justify-between h-16 px-4 border-b border-slate-200">
                <span className="text-lg font-bold text-ink">Menu</span>
                <button
                  onClick={closeMenu}
                  className="p-2 text-ink-secondary hover:bg-surface"
                  aria-label="Close menu"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Drawer Content */}
              <div className="flex flex-col p-4">
                <Link
                  href="/pricing"
                  className="text-ink hover:text-ink-secondary font-medium py-3 border-b border-slate-100"
                  onClick={closeMenu}
                >
                  Pricing
                </Link>
                <Link
                  href="/terms"
                  className="text-ink hover:text-ink-secondary font-medium py-3 border-b border-slate-100"
                  onClick={closeMenu}
                >
                  Terms
                </Link>
                <Link
                  href="/privacy"
                  className="text-ink hover:text-ink-secondary font-medium py-3 border-b border-slate-100"
                  onClick={closeMenu}
                >
                  Privacy
                </Link>

                {/* Auth buttons */}
                <div className="flex flex-col gap-3 pt-6 mt-4">
                  <Link
                    href="/login"
                    className="w-full px-4 py-3 text-center text-ink font-medium border border-ink-muted hover:bg-surface transition-colors"
                    onClick={closeMenu}
                  >
                    Log in
                  </Link>
                  <Link
                    href="/signup"
                    className="w-full px-4 py-3 text-center bg-steel text-white font-medium hover:bg-steel-light transition-colors"
                    onClick={closeMenu}
                  >
                    Start Free Trial
                  </Link>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </header>
  );
}
