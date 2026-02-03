import Link from 'next/link';
import { Check, ArrowRight } from 'lucide-react';

const tiers = [
  {
    name: 'Solo',
    price: '$49',
    period: '/month',
    description: 'Perfect for solo practitioners managing their own caseload.',
    features: [
      'Up to 25 active cases',
      'AI document analysis',
      'Deadline chain generation',
      'Calendar view',
      'Email notifications',
      '14 jurisdictions supported',
    ],
    cta: 'Start Free Trial',
    href: '/signup?plan=solo',
    featured: false,
  },
  {
    name: 'Team',
    price: '$149',
    period: '/month',
    description: 'For small firms needing collaboration and unlimited cases.',
    features: [
      'Unlimited active cases',
      'Everything in Solo, plus:',
      'Up to 5 team members',
      'Case sharing & collaboration',
      'Real-time presence',
      'Priority support',
      'Advanced analytics',
    ],
    cta: 'Start Free Trial',
    href: '/signup?plan=team',
    featured: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For larger firms with custom requirements.',
    features: [
      'Everything in Team, plus:',
      'Unlimited team members',
      'SSO authentication',
      'API access',
      'Custom integrations',
      'Dedicated support',
      'On-premise deployment option',
    ],
    cta: 'Contact Sales',
    href: 'mailto:sales@litdocket.com',
    featured: false,
  },
];

export function Pricing() {
  return (
    <section className="py-24 bg-slate-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
            Simple, transparent pricing
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Start with a 14-day free trial. No credit card required. Cancel anytime.
          </p>
        </div>

        {/* Pricing cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`rounded-2xl p-8 ${
                tier.featured
                  ? 'bg-blue-600 text-white ring-4 ring-blue-600 ring-offset-2'
                  : 'bg-white border border-slate-200'
              }`}
            >
              <h3
                className={`text-lg font-semibold mb-2 ${
                  tier.featured ? 'text-white' : 'text-slate-900'
                }`}
              >
                {tier.name}
              </h3>
              <div className="flex items-baseline mb-4">
                <span
                  className={`text-4xl font-bold ${
                    tier.featured ? 'text-white' : 'text-slate-900'
                  }`}
                >
                  {tier.price}
                </span>
                <span
                  className={`ml-1 ${
                    tier.featured ? 'text-blue-100' : 'text-slate-500'
                  }`}
                >
                  {tier.period}
                </span>
              </div>
              <p
                className={`text-sm mb-6 ${
                  tier.featured ? 'text-blue-100' : 'text-slate-600'
                }`}
              >
                {tier.description}
              </p>

              <ul className="space-y-3 mb-8">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <Check
                      className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                        tier.featured ? 'text-blue-200' : 'text-blue-600'
                      }`}
                    />
                    <span
                      className={`text-sm ${
                        tier.featured ? 'text-white' : 'text-slate-700'
                      }`}
                    >
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              <Link
                href={tier.href}
                className={`flex items-center justify-center gap-2 w-full py-3 px-4 rounded-lg font-semibold transition-colors ${
                  tier.featured
                    ? 'bg-white text-blue-600 hover:bg-blue-50'
                    : 'bg-slate-900 text-white hover:bg-slate-800'
                }`}
              >
                {tier.cta}
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          ))}
        </div>

        {/* Additional info */}
        <p className="text-center text-sm text-slate-500 mt-12">
          All plans include a 14-day free trial. Need a custom solution?{' '}
          <a href="mailto:sales@litdocket.com" className="text-blue-600 hover:underline">
            Contact us
          </a>
        </p>
      </div>
    </section>
  );
}
