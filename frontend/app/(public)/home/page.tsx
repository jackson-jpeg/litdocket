import { Hero } from '@/components/marketing/Hero';
import { Features } from '@/components/marketing/Features';
import { Pricing } from '@/components/marketing/Pricing';

export const metadata = {
  title: 'LitDocket - AI-Powered Legal Docketing',
  description: 'Never miss a fatal deadline. AI-powered legal docketing that combines CompuLaw-style rules-based calculation with intelligent document analysis.',
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <Features />
      <Pricing />
    </>
  );
}
