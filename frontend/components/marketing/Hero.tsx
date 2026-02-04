import Link from 'next/link';
import { ArrowRight, Shield, Zap, Calendar, Scale } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-slate-50 to-white">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-blue-100 opacity-50 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-indigo-100 opacity-50 blur-3xl" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div className="text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-full text-blue-700 text-sm font-medium mb-8">
            <Shield className="w-4 h-4" />
            Built for litigation professionals
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-slate-900 mb-6 tracking-tight">
            Never Miss a <span className="text-blue-600">Fatal Deadline</span>
          </h1>

          {/* Subheadline */}
          <p className="text-xl text-slate-600 max-w-2xl mx-auto mb-10">
            Automatically calculate deadlines using FRCP, State Rules, and Judge&apos;s Standing Orders.
            Our AI reads your court documents and alerts you before time runs out.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/signup"
              className="flex items-center gap-2 px-8 py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-lg shadow-blue-600/25"
            >
              Start Free Trial
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              href="/pricing"
              className="px-8 py-4 text-slate-700 font-semibold hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
            >
              View Pricing
            </Link>
          </div>

          {/* Use cases */}
          <div className="mt-16 flex flex-col items-center">
            <p className="text-sm text-slate-500 mb-4">Used by attorneys handling</p>
            <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-slate-600">
              <span className="text-sm font-medium">Complex Commercial Litigation</span>
              <span className="text-slate-300">|</span>
              <span className="text-sm font-medium">Federal Court Cases</span>
              <span className="text-slate-300">|</span>
              <span className="text-sm font-medium">Multi-District Litigation</span>
              <span className="text-slate-300">|</span>
              <span className="text-sm font-medium">Class Actions</span>
            </div>
            <div className="flex items-center gap-8 text-slate-400 mt-6">
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5" />
                <span className="text-sm font-medium">14 Jurisdictions</span>
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                <span className="text-sm font-medium">50+ Rule Templates</span>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5" />
                <span className="text-sm font-medium">AI-Powered</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
