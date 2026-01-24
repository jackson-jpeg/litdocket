import { Metadata } from 'next';
import AIAssistantDashboard from './AIAssistantDashboard';

export const metadata: Metadata = {
  title: 'AI Assistant | LitDocket',
  description: 'AI-powered document search and workload optimization'
};

export default function AIAssistantPage() {
  return <AIAssistantDashboard />;
}
