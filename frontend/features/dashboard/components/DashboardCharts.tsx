'use client';

import { BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface DashboardChartsProps {
  caseStats: {
    total_cases: number;
    by_jurisdiction: {
      state: number;
      federal: number;
      unknown: number;
    };
    by_case_type: {
      civil: number;
      criminal: number;
      appellate: number;
      other: number;
    };
  };
  deadlineStats: {
    overdue: number;
    urgent: number;
    upcoming_week: number;
    upcoming_month: number;
  };
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#6B7280'];

export default function DashboardCharts({ caseStats, deadlineStats }: DashboardChartsProps) {
  // Prepare jurisdiction data
  const jurisdictionData = [
    { name: 'State', value: caseStats.by_jurisdiction.state },
    { name: 'Federal', value: caseStats.by_jurisdiction.federal },
    { name: 'Unknown', value: caseStats.by_jurisdiction.unknown },
  ].filter(item => item.value > 0);

  // Prepare case type data
  const caseTypeData = [
    { name: 'Civil', value: caseStats.by_case_type.civil },
    { name: 'Criminal', value: caseStats.by_case_type.criminal },
    { name: 'Appellate', value: caseStats.by_case_type.appellate },
    { name: 'Other', value: caseStats.by_case_type.other },
  ].filter(item => item.value > 0);

  // Prepare deadline urgency data
  const deadlineUrgencyData = [
    { name: 'Overdue', count: deadlineStats.overdue, color: '#EF4444' },
    { name: 'Urgent (3 days)', count: deadlineStats.urgent, color: '#F59E0B' },
    { name: 'This Week', count: deadlineStats.upcoming_week, color: '#FCD34D' },
    { name: 'This Month', count: deadlineStats.upcoming_month, color: '#3B82F6' },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Deadline Urgency Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Deadline Urgency</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={deadlineUrgencyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#3B82F6">
              {deadlineUrgencyData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Cases by Jurisdiction */}
      {jurisdictionData.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Cases by Jurisdiction</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={jurisdictionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {jurisdictionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Cases by Type */}
      {caseTypeData.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Cases by Type</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={caseTypeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#8B5CF6" name="Number of Cases" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
