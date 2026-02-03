import {
  FileText,
  GitBranch,
  Calendar,
  Globe,
  Shield,
  Zap,
  Bell,
  Users,
} from 'lucide-react';

const features = [
  {
    icon: FileText,
    title: 'AI Document Analysis',
    description:
      'Upload legal documents and let AI extract key dates, parties, and deadlines automatically. Review and approve suggestions before they hit your docket.',
  },
  {
    icon: GitBranch,
    title: 'Deadline Chains',
    description:
      'Enter a trigger event like trial date or complaint served, and automatically generate 50+ dependent deadlines. Changes cascade through the entire chain.',
  },
  {
    icon: Calendar,
    title: 'Smart Calendar',
    description:
      'Visualize your docket with priority-coded deadlines. Drag and drop to reschedule, and see workload distribution at a glance.',
  },
  {
    icon: Globe,
    title: 'Multi-Jurisdiction',
    description:
      'Supports Federal, State, and Local court rules across 14 jurisdictions. Each deadline includes rule citations and calculation methodology.',
  },
  {
    icon: Shield,
    title: 'Verification Gate',
    description:
      'Every AI-generated deadline requires attorney verification before activation. Complete audit trail for malpractice protection.',
  },
  {
    icon: Zap,
    title: 'Morning Report',
    description:
      'Start each day with a prioritized dashboard showing urgent deadlines, overdue items, and action recommendations.',
  },
  {
    icon: Bell,
    title: 'Smart Notifications',
    description:
      'Configurable alerts based on deadline priority and days remaining. Never be caught off guard by a fatal deadline.',
  },
  {
    icon: Users,
    title: 'Team Collaboration',
    description:
      'Share cases with team members using role-based access control. See who is viewing a case in real-time.',
  },
];

export function Features() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
            Everything you need to manage deadlines
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Built by attorneys who understand the stakes. LitDocket combines proven docketing
            methodologies with modern AI capabilities.
          </p>
        </div>

        {/* Features grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="p-6 rounded-xl border border-slate-200 hover:border-blue-200 hover:shadow-lg transition-all group"
            >
              <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center mb-4 group-hover:bg-blue-100 transition-colors">
                <feature.icon className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                {feature.title}
              </h3>
              <p className="text-slate-600 text-sm leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
