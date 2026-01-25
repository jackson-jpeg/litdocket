'use client';

import React, { useState, useEffect } from 'react';
import { Sparkles, Brain, TrendingUp, FileSearch, Calendar, AlertTriangle, CheckCircle, Clock, Target } from 'lucide-react';
import SmartDocumentSearch from '@/components/SmartDocumentSearch';
import WorkloadHeatmap from '@/components/WorkloadHeatmap';
import { useWorkload } from '@/hooks/useWorkload';

type Tab = 'overview' | 'search' | 'workload';

export default function AIAssistantDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');

  // Get workload data for overview
  const { stats, burnoutAlerts, riskDays, aiSuggestions, loading: workloadLoading } = useWorkload({
    daysAhead: 30,
    autoRefresh: true,
    refreshInterval: 300000 // 5 minutes
  });

  const tabs = [
    { id: 'overview' as Tab, name: 'Overview', icon: Brain },
    { id: 'search' as Tab, name: 'Smart Search', icon: FileSearch },
    { id: 'workload' as Tab, name: 'Workload Intelligence', icon: TrendingUp }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/10 rounded-lg backdrop-blur-sm">
              <Sparkles className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">AI Assistant</h1>
              <p className="text-purple-100 mt-1">
                Your intelligent co-pilot for litigation management
              </p>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="mt-8 flex gap-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all
                    ${activeTab === tab.id
                      ? 'bg-white text-purple-600 shadow-lg'
                      : 'bg-white/10 text-white hover:bg-white/20'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  {tab.name}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Workload Stats */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Calendar className="w-6 h-6 text-blue-600" />
                  </div>
                  {stats && (
                    <span className="text-2xl font-bold text-gray-900">
                      {stats.total_deadlines}
                    </span>
                  )}
                </div>
                <h3 className="font-semibold text-gray-900">Total Deadlines</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Next 30 days
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-2 bg-yellow-100 rounded-lg">
                    <AlertTriangle className="w-6 h-6 text-yellow-600" />
                  </div>
                  {stats && (
                    <span className="text-2xl font-bold text-yellow-600">
                      {stats.saturated_days_count}
                    </span>
                  )}
                </div>
                <h3 className="font-semibold text-gray-900">High-Risk Days</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Workload saturation
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <Sparkles className="w-6 h-6 text-purple-600" />
                  </div>
                  <span className="text-2xl font-bold text-purple-600">
                    {aiSuggestions.length}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900">AI Suggestions</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Deadline optimizations
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Target className="w-6 h-6 text-green-600" />
                  </div>
                  {stats && stats.average_deadlines_per_day && (
                    <span className="text-2xl font-bold text-gray-900">
                      {stats.average_deadlines_per_day.toFixed(1)}
                    </span>
                  )}
                </div>
                <h3 className="font-semibold text-gray-900">Avg Per Day</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Workload distribution
                </p>
              </div>
            </div>

            {/* Burnout Alerts */}
            {burnoutAlerts.length > 0 && (
              <div className="bg-red-50 border-l-4 border-red-500 p-6 rounded-lg shadow">
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-red-100 rounded-lg flex-shrink-0">
                    <AlertTriangle className="w-6 h-6 text-red-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-red-900 text-lg mb-2">
                      ⚠️ Burnout Risk Detected
                    </h3>
                    <div className="space-y-2">
                      {burnoutAlerts.map((alert, i) => (
                        <div key={i} className="text-red-700">
                          <p className="font-medium">{alert.message}</p>
                          <p className="text-sm mt-1">
                            {new Date(alert.start_date).toLocaleDateString()} - {new Date(alert.end_date).toLocaleDateString()}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <button
                onClick={() => setActiveTab('search')}
                className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow text-left group"
              >
                <div className="p-3 bg-blue-100 rounded-lg inline-block mb-4 group-hover:bg-blue-200 transition-colors">
                  <FileSearch className="w-8 h-8 text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 text-lg mb-2">
                  Smart Document Search
                </h3>
                <p className="text-gray-600 text-sm">
                  Ask questions in natural language and get answers with exact citations from your case documents.
                </p>
              </button>

              <button
                onClick={() => setActiveTab('workload')}
                className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow text-left group"
              >
                <div className="p-3 bg-purple-100 rounded-lg inline-block mb-4 group-hover:bg-purple-200 transition-colors">
                  <TrendingUp className="w-8 h-8 text-purple-600" />
                </div>
                <h3 className="font-semibold text-gray-900 text-lg mb-2">
                  Workload Optimization
                </h3>
                <p className="text-gray-600 text-sm">
                  Visualize deadline clustering and get AI-powered suggestions to prevent burnout.
                </p>
              </button>

              <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg shadow p-6 border-2 border-purple-200">
                <div className="p-3 bg-white rounded-lg inline-block mb-4">
                  <Clock className="w-8 h-8 text-purple-600" />
                </div>
                <h3 className="font-semibold text-gray-900 text-lg mb-2">
                  Coming Soon: Real-Time Collaboration
                </h3>
                <p className="text-gray-600 text-sm">
                  Work on cases with your team in real-time with live presence and collaborative cursors.
                </p>
                <span className="inline-block mt-3 text-xs font-medium text-purple-600 bg-white px-3 py-1 rounded-full">
                  Q2 2026
                </span>
              </div>
            </div>

            {/* Recent AI Insights */}
            {aiSuggestions.length > 0 && (
              <div className="bg-white rounded-lg shadow">
                <div className="p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-purple-600" />
                    Recent AI Insights
                  </h3>
                </div>
                <div className="divide-y divide-gray-200">
                  {aiSuggestions.slice(0, 3).map((suggestion, i) => (
                    <div key={i} className="p-6 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="font-medium text-gray-900">
                              {new Date(suggestion.date).toLocaleDateString('en-US', {
                                weekday: 'long',
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric'
                              })}
                            </span>
                            <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                              Risk: {suggestion.risk_score.toFixed(1)}
                            </span>
                          </div>
                          <p className="text-gray-700">{suggestion.summary}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Feature Highlights */}
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow p-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                AI-Powered Features
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex gap-4">
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1">
                      Semantic Document Search
                    </h4>
                    <p className="text-sm text-gray-600">
                      Find information across all documents using natural language questions. Get AI-generated answers with source citations.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1">
                      Workload Intelligence
                    </h4>
                    <p className="text-sm text-gray-600">
                      Visual calendar heatmap shows deadline clustering. AI suggests optimal rescheduling to prevent burnout.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1">
                      Burnout Prevention
                    </h4>
                    <p className="text-sm text-gray-600">
                      Automatic alerts when consecutive high-workload days are detected. Proactive suggestions to redistribute work.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-1">
                      Auto-Embedding Generation
                    </h4>
                    <p className="text-sm text-gray-600">
                      Every uploaded document automatically generates embeddings for instant semantic search. No manual setup required.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'search' && (
          <div className="bg-white rounded-lg shadow p-8">
            <SmartDocumentSearch
              caseId={selectedCaseId}
              onOpenDocument={(docId) => {
                // Navigate to document
                window.location.href = `/documents/${docId}`;
              }}
            />
          </div>
        )}

        {activeTab === 'workload' && (
          <div className="space-y-8">
            <WorkloadHeatmap daysAhead={60} />
          </div>
        )}
      </div>
    </div>
  );
}
