import Link from 'next/link';
import { ArrowRight, Shield, Zap, Calendar, Scale } from 'lucide-react';

const useCases = ['Complex Commercial Litigation', 'Federal Court Cases', 'Multi-District Litigation', 'Class Actions'];

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-paper">
      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: 'linear-gradient(#1A1A1A 1px, transparent 1px), linear-gradient(90deg, #1A1A1A 1px, transparent 1px)',
          backgroundSize: '48px 48px'
        }}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div className="text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-surface border-l-4 border-wax text-ink text-xs font-semibold uppercase tracking-wider mb-8">
            <Shield className="w-4 h-4" />
            Built for litigation professionals
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-ink mb-6 tracking-tight">
            Never Miss a <span className="text-wax">Fatal Deadline</span>
          </h1>

          {/* Subheadline - Honest AI messaging */}
          <p className="text-xl text-ink-secondary max-w-2xl mx-auto mb-10">
            Upload documents and AI extracts key dates for your review.
            Our rules engine calculates precise deadline chains from FRCP, State Rules, and Standing Orders.
            Every deadline requires attorney verification.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <div className="flex flex-col items-center gap-2">
              <Link
                href="/signup"
                className="flex items-center gap-2 px-8 py-4 bg-steel text-white font-semibold hover:bg-steel-light transition-colors"
              >
                Start 14-Day Free Trial
                <ArrowRight className="w-5 h-5" />
              </Link>
              <span className="text-xs text-ink-muted">No credit card required</span>
            </div>
            <Link
              href="/pricing"
              className="px-8 py-4 text-ink font-semibold border border-ink-muted hover:border-ink transition-colors"
            >
              Compare Plans
            </Link>
          </div>

          {/* Use cases */}
          <div className="mt-16 flex flex-col items-center">
            <p className="text-sm text-ink-muted mb-4">Used by attorneys handling</p>
            <div className="flex flex-wrap items-center justify-center gap-y-2">
              {useCases.map((item, i) => (
                <span
                  key={item}
                  className={`text-sm font-medium text-ink-secondary px-3 ${
                    i < useCases.length - 1 ? 'sm:border-r sm:border-ink-muted' : ''
                  }`}
                >
                  {item}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-8 text-ink-muted mt-6">
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
