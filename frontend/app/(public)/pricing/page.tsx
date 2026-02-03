import Link from 'next/link';
import { Check, ArrowRight, HelpCircle } from 'lucide-react';

export const metadata = {
  title: 'Pricing - LitDocket',
  description: 'Simple, transparent pricing for AI-powered legal docketing. Start with a 14-day free trial.',
};

const tiers = [
  {
    name: 'Solo',
    price: '$49',
    period: '/month',
    yearlyPrice: '$470',
    yearlySavings: 'Save $118/year',
    description: 'Perfect for solo practitioners managing their own caseload.',
    features: [
      { text: 'Up to 25 active cases', included: true },
      { text: 'AI document analysis', included: true },
      { text: 'Deadline chain generation', included: true },
      { text: 'Calendar view with drag & drop', included: true },
      { text: 'Email notifications', included: true },
      { text: '14 jurisdictions supported', included: true },
      { text: 'Morning report dashboard', included: true },
      { text: 'Basic analytics', included: true },
      { text: 'Team collaboration', included: false },
      { text: 'API access', included: false },
    ],
    cta: 'Start Free Trial',
    href: '/signup?plan=solo',
    featured: false,
  },
  {
    name: 'Team',
    price: '$149',
    period: '/month',
    yearlyPrice: '$1,430',
    yearlySavings: 'Save $358/year',
    description: 'For small firms needing collaboration and unlimited cases.',
    features: [
      { text: 'Unlimited active cases', included: true },
      { text: 'AI document analysis', included: true },
      { text: 'Deadline chain generation', included: true },
      { text: 'Calendar view with drag & drop', included: true },
      { text: 'Email & SMS notifications', included: true },
      { text: '14 jurisdictions supported', included: true },
      { text: 'Morning report dashboard', included: true },
      { text: 'Advanced analytics & workload', included: true },
      { text: 'Up to 5 team members', included: true },
      { text: 'Case sharing & collaboration', included: true },
      { text: 'Real-time presence', included: true },
      { text: 'Priority support', included: true },
    ],
    cta: 'Start Free Trial',
    href: '/signup?plan=team',
    featured: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    yearlyPrice: '',
    yearlySavings: '',
    description: 'For larger firms with custom requirements and compliance needs.',
    features: [
      { text: 'Everything in Team', included: true },
      { text: 'Unlimited team members', included: true },
      { text: 'SSO authentication (SAML/OIDC)', included: true },
      { text: 'API access', included: true },
      { text: 'Custom integrations', included: true },
      { text: 'Dedicated account manager', included: true },
      { text: 'Custom rule templates', included: true },
      { text: 'On-premise deployment option', included: true },
      { text: 'SLA guarantee', included: true },
      { text: 'Security audit reports', included: true },
    ],
    cta: 'Contact Sales',
    href: 'mailto:sales@litdocket.com',
    featured: false,
  },
];

const faqs = [
  {
    question: 'What happens after my free trial?',
    answer: 'After your 14-day free trial, you can choose to subscribe to continue using LitDocket. If you don\'t subscribe, your account will be converted to a limited free tier with read-only access to your data.',
  },
  {
    question: 'Can I switch plans later?',
    answer: 'Yes! You can upgrade or downgrade your plan at any time. When upgrading, you\'ll be charged the prorated difference. When downgrading, the new rate takes effect at your next billing cycle.',
  },
  {
    question: 'What jurisdictions are supported?',
    answer: 'We support Federal courts (FRCP, FRAP) and state courts in California, Florida, New York, Texas, Illinois, Georgia, Pennsylvania, Arizona, Colorado, Massachusetts, New Jersey, and Washington. More jurisdictions are added regularly.',
  },
  {
    question: 'Is my data secure?',
    answer: 'Yes. We use industry-standard encryption for data at rest and in transit. Your data is stored in SOC 2 compliant data centers, and we never share your data with third parties. Enterprise plans include additional security features.',
  },
  {
    question: 'Can I export my data?',
    answer: 'Yes. You can export your cases, deadlines, and documents at any time in standard formats (CSV, JSON, iCal). We believe your data belongs to you.',
  },
  {
    question: 'Do you offer discounts for nonprofits?',
    answer: 'Yes! We offer 50% off for legal aid organizations and nonprofits. Contact sales@litdocket.com with proof of nonprofit status.',
  },
];

export default function PricingPage() {
  return (
    <div className="bg-slate-50">
      {/* Header */}
      <section className="py-16 lg:py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-4">
            Simple, transparent pricing
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto">
            Start with a 14-day free trial. No credit card required. Cancel anytime.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16 -mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={`rounded-2xl p-8 ${
                  tier.featured
                    ? 'bg-blue-600 text-white ring-4 ring-blue-600 ring-offset-2 scale-105'
                    : 'bg-white border border-slate-200'
                }`}
              >
                {tier.featured && (
                  <div className="text-sm font-medium text-blue-200 mb-4">
                    Most Popular
                  </div>
                )}
                <h2
                  className={`text-2xl font-bold mb-2 ${
                    tier.featured ? 'text-white' : 'text-slate-900'
                  }`}
                >
                  {tier.name}
                </h2>
                <div className="flex items-baseline mb-2">
                  <span
                    className={`text-5xl font-bold ${
                      tier.featured ? 'text-white' : 'text-slate-900'
                    }`}
                  >
                    {tier.price}
                  </span>
                  <span
                    className={`ml-2 ${
                      tier.featured ? 'text-blue-100' : 'text-slate-500'
                    }`}
                  >
                    {tier.period}
                  </span>
                </div>
                {tier.yearlyPrice && (
                  <p
                    className={`text-sm mb-4 ${
                      tier.featured ? 'text-blue-200' : 'text-slate-500'
                    }`}
                  >
                    or {tier.yearlyPrice}/year ({tier.yearlySavings})
                  </p>
                )}
                <p
                  className={`text-sm mb-8 ${
                    tier.featured ? 'text-blue-100' : 'text-slate-600'
                  }`}
                >
                  {tier.description}
                </p>

                <Link
                  href={tier.href}
                  className={`flex items-center justify-center gap-2 w-full py-3 px-4 rounded-lg font-semibold transition-colors mb-8 ${
                    tier.featured
                      ? 'bg-white text-blue-600 hover:bg-blue-50'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {tier.cta}
                  <ArrowRight className="w-4 h-4" />
                </Link>

                <ul className="space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature.text} className="flex items-start gap-3">
                      <Check
                        className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                          feature.included
                            ? tier.featured
                              ? 'text-blue-200'
                              : 'text-blue-600'
                            : 'text-slate-300'
                        }`}
                      />
                      <span
                        className={`text-sm ${
                          feature.included
                            ? tier.featured
                              ? 'text-white'
                              : 'text-slate-700'
                            : tier.featured
                            ? 'text-blue-300 line-through'
                            : 'text-slate-400 line-through'
                        }`}
                      >
                        {feature.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16 lg:py-24 bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-slate-600">
              Have more questions?{' '}
              <a href="mailto:support@litdocket.com" className="text-blue-600 hover:underline">
                Contact our team
              </a>
            </p>
          </div>

          <div className="space-y-6">
            {faqs.map((faq) => (
              <div
                key={faq.question}
                className="bg-slate-50 rounded-xl p-6"
              >
                <div className="flex items-start gap-3">
                  <HelpCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-slate-900 mb-2">
                      {faq.question}
                    </h3>
                    <p className="text-slate-600 text-sm leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-blue-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to never miss a deadline?
          </h2>
          <p className="text-blue-100 text-lg mb-8">
            Start your 14-day free trial today. No credit card required.
          </p>
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 px-8 py-4 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition-colors"
          >
            Start Free Trial
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>
    </div>
  );
}
