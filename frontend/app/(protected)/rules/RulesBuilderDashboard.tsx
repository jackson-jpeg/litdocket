'use client';

import { useState } from 'react';
import { useRules } from '@/hooks/useRules';
import {
  Cog6ToothIcon,
  SparklesIcon,
  ClockIcon,
  ShoppingBagIcon,
  PlusCircleIcon,
  CheckCircleIcon,
  PlayIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';

type TabType = 'my-rules' | 'marketplace' | 'create' | 'history';

export default function RulesBuilderDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('my-rules');
  const { rules, loading, error, fetchMarketplaceRules } = useRules({
    include_public: false
  });

  const tabs = [
    { id: 'my-rules' as TabType, name: 'My Rules', icon: Cog6ToothIcon, count: rules.length },
    { id: 'marketplace' as TabType, name: 'Marketplace', icon: ShoppingBagIcon },
    { id: 'create' as TabType, name: 'Create New', icon: PlusCircleIcon },
    { id: 'history' as TabType, name: 'Execution History', icon: ClockIcon }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
              <SparklesIcon className="h-8 w-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Rules Builder</h1>
              <p className="text-blue-100 mt-1">
                Create jurisdiction-specific deadline calculation rules
              </p>
            </div>
          </div>

          {/* Tabs */}
          <div className="mt-6 flex gap-2 border-b border-white/20">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 px-4 py-3 font-medium transition-all
                    ${isActive
                      ? 'text-white border-b-2 border-white'
                      : 'text-blue-200 hover:text-white hover:bg-white/10'
                    }
                  `}
                >
                  <Icon className="h-5 w-5" />
                  {tab.name}
                  {tab.count !== undefined && (
                    <span className={`
                      ml-2 px-2 py-0.5 text-xs rounded-full
                      ${isActive ? 'bg-white text-blue-600' : 'bg-blue-500 text-white'}
                    `}>
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {activeTab === 'my-rules' && <MyRulesTab rules={rules} loading={loading} />}
        {activeTab === 'marketplace' && <MarketplaceTab />}
        {activeTab === 'create' && <CreateRuleTab />}
        {activeTab === 'history' && <ExecutionHistoryTab />}
      </div>
    </div>
  );
}

// ============================================
// MY RULES TAB
// ============================================

function MyRulesTab({ rules, loading }: { rules: any[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (rules.length === 0) {
    return (
      <div className="text-center py-16">
        <Cog6ToothIcon className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No rules yet</h3>
        <p className="text-gray-500 mb-6">
          Create your first jurisdiction rule to automate deadline calculations
        </p>
        <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
          Create Your First Rule
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {rules.map((rule) => (
        <RuleCard key={rule.id} rule={rule} />
      ))}
    </div>
  );
}

function RuleCard({ rule }: { rule: any }) {
  const statusColors = {
    draft: 'bg-gray-100 text-gray-700',
    active: 'bg-green-100 text-green-700',
    deprecated: 'bg-yellow-100 text-yellow-700',
    archived: 'bg-red-100 text-red-700'
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">{rule.rule_name}</h3>
          <p className="text-sm text-gray-500">{rule.jurisdiction}</p>
        </div>
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[rule.status as keyof typeof statusColors]}`}>
          {rule.status}
        </span>
      </div>

      {/* Description */}
      {rule.description && (
        <p className="text-sm text-gray-600 mb-4 line-clamp-2">{rule.description}</p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-gray-100">
        <div>
          <p className="text-xs text-gray-500">Executions</p>
          <p className="text-lg font-semibold text-gray-900">{rule.usage_count}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Versions</p>
          <p className="text-lg font-semibold text-gray-900">{rule.version_count}</p>
        </div>
      </div>

      {/* Tags */}
      {rule.tags && rule.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {rule.tags.slice(0, 3).map((tag: string, idx: number) => (
            <span key={idx} className="px-2 py-1 bg-blue-50 text-blue-600 text-xs rounded">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
          Edit
        </button>
        <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium">
          <PlayIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================
// MARKETPLACE TAB
// ============================================

function MarketplaceTab() {
  return (
    <div className="text-center py-16">
      <ShoppingBagIcon className="h-16 w-16 text-gray-300 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">Rule Marketplace</h3>
      <p className="text-gray-500 mb-6">
        Browse and install jurisdiction rules shared by the LitDocket community
      </p>
      <p className="text-sm text-gray-400">Coming soon...</p>
    </div>
  );
}

// ============================================
// CREATE RULE TAB
// ============================================

function CreateRuleTab() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Create New Rule</h2>

        {/* Rule Basic Info */}
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rule Name
            </label>
            <input
              type="text"
              placeholder="Florida Civil - Trial Date Chain"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Jurisdiction
              </label>
              <input
                type="text"
                placeholder="florida_civil"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Trigger Type
              </label>
              <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option>TRIAL_DATE</option>
                <option>COMPLAINT_SERVED</option>
                <option>SUMMONS_ISSUED</option>
                <option>DISCOVERY_CUTOFF</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              rows={3}
              placeholder="Describe what this rule does and when it should be used..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Visual Builder Placeholder */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-8 border-2 border-dashed border-blue-300">
            <div className="text-center">
              <DocumentTextIcon className="h-12 w-12 text-blue-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Visual Rule Builder
              </h3>
              <p className="text-gray-600 mb-4">
                Drag-and-drop timeline interface for creating deadline chains
              </p>
              <p className="text-sm text-gray-500">
                Timeline visualization component coming in next update...
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-4 pt-6 border-t border-gray-200">
            <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
              Save as Draft
            </button>
            <button className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium">
              Preview Rule
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// EXECUTION HISTORY TAB
// ============================================

function ExecutionHistoryTab() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Execution History</h2>
        <p className="text-sm text-gray-500 mt-1">
          Complete audit trail of when rules were executed
        </p>
      </div>

      <div className="text-center py-16">
        <ClockIcon className="h-16 w-16 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">No executions yet</p>
        <p className="text-sm text-gray-400 mt-2">
          Execute a rule to see history here
        </p>
      </div>
    </div>
  );
}
