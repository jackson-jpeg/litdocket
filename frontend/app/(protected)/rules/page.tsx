import { Metadata } from 'next';
import RulesBuilderDashboard from './RulesBuilderDashboard';

export const metadata: Metadata = {
  title: 'Rules Builder | LitDocket',
  description: 'Create and manage jurisdiction-specific deadline calculation rules'
};

export default function RulesBuilderPage() {
  return <RulesBuilderDashboard />;
}
