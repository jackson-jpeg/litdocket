'use client';

import { useState } from 'react';
import * as React from 'react';
import { useRules } from '@/hooks/useRules';
import TimelineRuleBuilder from '@/components/rules/TimelineRuleBuilder';
import RuleExecutionPreview from '@/components/rules/RuleExecutionPreview';
import {
  Settings,
  Sparkles,
  Clock,
  ShoppingBag,
  PlusCircle,
  CheckCircle,
  Play,
  FileText,
  Save,
  Eye,
  X
} from 'lucide-react';

type TabType = 'my-rules' | 'marketplace' | 'create' | 'history';

export default function RulesBuilderDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('my-rules');
  const [testingRule, setTestingRule] = useState<any | null>(null);

  // Lift the hook to parent so all tabs share the same state
  const {
    rules,
    loading,
    error,
    createRule,
    fetchRules,
    fetchMarketplaceRules
  } = useRules({
    include_public: false
  });

  // Callback for when a rule is created successfully
  const handleRuleCreated = async () => {
    await fetchRules(); // Refresh the rules list
    setActiveTab('my-rules'); // Navigate to My Rules tab
  };

  const tabs = [
    { id: 'my-rules' as TabType, name: 'My Rules', icon: Settings, count: rules.length },
    { id: 'marketplace' as TabType, name: 'Marketplace', icon: ShoppingBag },
    { id: 'create' as TabType, name: 'Create New', icon: PlusCircle },
    { id: 'history' as TabType, name: 'Execution History', icon: Clock }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
              <Sparkles className="h-8 w-8" />
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

        {activeTab === 'my-rules' && <MyRulesTab rules={rules} loading={loading} onTestRule={setTestingRule} />}
        {activeTab === 'marketplace' && <MarketplaceTab />}
        {activeTab === 'create' && (
          <CreateRuleTab
            createRule={createRule}
            loading={loading}
            onRuleCreated={handleRuleCreated}
          />
        )}
        {activeTab === 'history' && <ExecutionHistoryTab />}
      </div>

      {/* Test Rule Modal */}
      {testingRule && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-auto m-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                Test Rule: {testingRule.rule_name}
              </h2>
              <button
                onClick={() => setTestingRule(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>
            <div className="p-4">
              <RuleExecutionPreview
                ruleTemplateId={testingRule.id}
                caseId=""
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// MY RULES TAB
// ============================================

function MyRulesTab({ rules, loading, onTestRule }: { rules: any[]; loading: boolean; onTestRule: (rule: any) => void }) {
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
        <Settings className="h-16 w-16 text-gray-300 mx-auto mb-4" />
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
        <RuleCard key={rule.id} rule={rule} onTest={() => onTestRule(rule)} />
      ))}
    </div>
  );
}

function RuleCard({ rule, onTest }: { rule: any; onTest: () => void }) {
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
        <button
          onClick={onTest}
          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium"
          title="Test Rule"
        >
          <Play className="h-4 w-4" />
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
      <ShoppingBag className="h-16 w-16 text-gray-300 mx-auto mb-4" />
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

interface CreateRuleTabProps {
  createRule: (request: any) => Promise<any>;
  loading: boolean;
  onRuleCreated: () => Promise<void>;
}

function CreateRuleTab({ createRule, loading, onRuleCreated }: CreateRuleTabProps) {
  const [formData, setFormData] = useState({
    rule_name: '',
    slug: '',
    jurisdiction: '',
    trigger_type: 'TRIAL_DATE',
    description: '',
    tags: [] as string[],
    is_public: false
  });
  const [deadlines, setDeadlines] = useState<any[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Auto-generate slug from rule name
  const handleRuleNameChange = (name: string) => {
    setFormData({
      ...formData,
      rule_name: name,
      slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
    });
  };

  const handleAddTag = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      if (!formData.tags.includes(tagInput.trim())) {
        setFormData({
          ...formData,
          tags: [...formData.tags, tagInput.trim()]
        });
      }
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter(tag => tag !== tagToRemove)
    });
  };

  const handleSave = async (isDraft: boolean = true) => {
    // Build rule schema from deadlines
    const ruleSchema = {
      metadata: {
        name: formData.rule_name,
        description: formData.description,
        effective_date: new Date().toISOString().split('T')[0]
      },
      trigger: {
        type: formData.trigger_type,
        required_fields: [
          {
            name: formData.trigger_type.toLowerCase() + '_date',
            type: 'date',
            label: formData.trigger_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
            required: true
          }
        ]
      },
      deadlines: deadlines.map(d => ({
        id: d.id,
        title: d.title,
        offset_days: d.offset_direction === 'before' ? -Math.abs(d.offset_days) : Math.abs(d.offset_days),
        offset_direction: d.offset_direction,
        priority: d.priority,
        description: d.description,
        applicable_rule: d.applicable_rule,
        add_service_days: d.add_service_days || false
      })),
      dependencies: [],
      validation: {
        min_deadlines: 1,
        max_deadlines: 100,
        require_citations: false
      },
      settings: {
        auto_cascade_updates: true,
        allow_manual_override: true,
        notification_lead_days: [1, 3, 7, 14]
      }
    };

    const result = await createRule({
      rule_name: formData.rule_name,
      slug: formData.slug,
      jurisdiction: formData.jurisdiction,
      trigger_type: formData.trigger_type,
      description: formData.description,
      tags: formData.tags,
      is_public: formData.is_public,
      rule_schema: ruleSchema
    });

    if (result) {
      setSaveStatus('success');
      // Notify parent to refresh rules and switch to My Rules tab
      await onRuleCreated();
    } else {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  const isFormValid = formData.rule_name && formData.jurisdiction && formData.trigger_type && deadlines.length > 0;

  return (
    <div className="space-y-6">
      {/* Header with Save Status */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Create New Rule</h2>
            <p className="text-sm text-gray-500 mt-1">
              Build a custom jurisdiction rule with visual timeline
            </p>
          </div>

          {saveStatus === 'success' && (
            <div className="flex items-center gap-2 text-green-600 bg-green-50 px-4 py-2 rounded-lg">
              <CheckCircle className="h-5 w-5" />
              <span className="font-medium">Rule saved!</span>
            </div>
          )}

          {saveStatus === 'error' && (
            <div className="flex items-center gap-2 text-red-600 bg-red-50 px-4 py-2 rounded-lg">
              <span className="font-medium">Failed to save rule</span>
            </div>
          )}
        </div>

        {/* Basic Info */}
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rule Name *
            </label>
            <input
              type="text"
              required
              value={formData.rule_name}
              onChange={(e) => handleRuleNameChange(e.target.value)}
              placeholder="Florida Civil - Trial Date Chain"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {formData.slug && (
              <p className="text-xs text-gray-500 mt-1">Slug: {formData.slug}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Jurisdiction *
              </label>
              <input
                type="text"
                required
                value={formData.jurisdiction}
                onChange={(e) => setFormData({ ...formData, jurisdiction: e.target.value })}
                placeholder="florida_civil"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">e.g., florida_civil, federal_civil, texas_criminal</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Trigger Type *
              </label>
              <select
                value={formData.trigger_type}
                onChange={(e) => setFormData({ ...formData, trigger_type: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="TRIAL_DATE">Trial Date</option>
                <option value="COMPLAINT_SERVED">Complaint Served</option>
                <option value="SUMMONS_ISSUED">Summons Issued</option>
                <option value="DISCOVERY_CUTOFF">Discovery Cutoff</option>
                <option value="MOTION_HEARING">Motion Hearing</option>
                <option value="DEPOSITION_SCHEDULED">Deposition Scheduled</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe what this rule does and when it should be used..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tags
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {formData.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                >
                  {tag}
                  <button
                    onClick={() => handleRemoveTag(tag)}
                    className="hover:text-blue-900"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleAddTag}
              placeholder="Type tag and press Enter"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_public"
              checked={formData.is_public}
              onChange={(e) => setFormData({ ...formData, is_public: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="is_public" className="ml-2 text-sm text-gray-700">
              Make this rule public (share in marketplace)
            </label>
          </div>
        </div>
      </div>

      {/* Timeline Builder */}
      <TimelineRuleBuilder
        triggerType={formData.trigger_type}
        deadlines={deadlines}
        onChange={setDeadlines}
      />

      {/* Actions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex gap-4">
          <button
            onClick={() => handleSave(true)}
            disabled={!isFormValid || loading}
            className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-5 w-5" />
                Save as Draft
              </>
            )}
          </button>
          <button
            disabled={!isFormValid}
            className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Eye className="h-5 w-5" />
            Preview Rule
          </button>
        </div>

        {!isFormValid && (
          <p className="text-sm text-gray-500 mt-3 text-center">
            Complete all required fields (*) and add at least one deadline to save
          </p>
        )}
      </div>
    </div>
  );
}

// ============================================
// EXECUTION HISTORY TAB
// ============================================

function ExecutionHistoryTab() {
  const { executions, fetchExecutions, loading } = useRules();
  const [selectedRuleFilter, setSelectedRuleFilter] = useState<string>('all');

  // Load executions on mount
  React.useEffect(() => {
    fetchExecutions();
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  const filteredExecutions = selectedRuleFilter === 'all'
    ? executions
    : executions.filter((e: any) => e.rule_template_id === selectedRuleFilter);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Execution History</h2>
            <p className="text-sm text-gray-500 mt-1">
              Complete audit trail of when rules were executed
            </p>
          </div>

          {executions.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Filter:</span>
              <select
                value={selectedRuleFilter}
                onChange={(e) => setSelectedRuleFilter(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Rules</option>
                {/* Add unique rules as options */}
              </select>
            </div>
          )}
        </div>
      </div>

      {executions.length === 0 ? (
        <div className="text-center py-16">
          <Clock className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No executions yet</p>
          <p className="text-sm text-gray-400 mt-2">
            Execute a rule to see history here
          </p>
        </div>
      ) : (
        <div className="divide-y divide-gray-200">
          {filteredExecutions.map((execution: any) => (
            <ExecutionHistoryItem key={execution.id} execution={execution} />
          ))}
        </div>
      )}
    </div>
  );
}

function ExecutionHistoryItem({ execution }: { execution: any }) {
  const [expanded, setExpanded] = React.useState(false);

  const statusColors = {
    success: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    partial: 'bg-yellow-100 text-yellow-800'
  };

  const statusColor = execution.status === 'success'
    ? statusColors.success
    : execution.error_message
    ? statusColors.error
    : statusColors.partial;

  return (
    <div className="p-6 hover:bg-gray-50 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-semibold text-gray-900">
              {execution.rule_template_id}
            </h3>
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColor}`}>
              {execution.status || 'success'}
            </span>
          </div>

          <div className="grid grid-cols-4 gap-4 text-sm text-gray-600 mb-2">
            <div>
              <span className="text-gray-500">Deadlines Created:</span>{' '}
              <span className="font-medium text-gray-900">{execution.deadlines_created}</span>
            </div>
            <div>
              <span className="text-gray-500">Execution Time:</span>{' '}
              <span className="font-medium text-gray-900">{execution.execution_time_ms}ms</span>
            </div>
            <div>
              <span className="text-gray-500">Case:</span>{' '}
              <span className="font-medium text-gray-900">{execution.case_id}</span>
            </div>
            <div>
              <span className="text-gray-500">Date:</span>{' '}
              <span className="font-medium text-gray-900">
                {new Date(execution.executed_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          {execution.error_message && (
            <div className="mt-2 text-sm text-red-600 bg-red-50 rounded px-3 py-2">
              <strong>Error:</strong> {execution.error_message}
            </div>
          )}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="ml-4 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg font-medium"
        >
          {expanded ? 'Hide Details' : 'Show Details'}
        </button>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Trigger Data</h4>
              <pre className="bg-gray-50 rounded p-3 text-xs overflow-x-auto">
                {JSON.stringify(execution.trigger_data, null, 2)}
              </pre>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">
                Generated Deadlines ({execution.deadline_ids?.length || 0})
              </h4>
              <div className="bg-gray-50 rounded p-3 max-h-40 overflow-y-auto">
                {execution.deadline_ids && execution.deadline_ids.length > 0 ? (
                  <ul className="text-xs space-y-1">
                    {execution.deadline_ids.map((id: string, idx: number) => (
                      <li key={idx} className="text-gray-600">
                        • {id}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-gray-500">No deadlines recorded</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
