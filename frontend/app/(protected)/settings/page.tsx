'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useNotifications } from '@/hooks/useNotifications';
import { Download, User, Bell, Settings as SettingsIcon, Plug } from 'lucide-react';

type TabType = 'notifications' | 'preferences' | 'account' | 'integrations';

interface NotificationPreferences {
  in_app_enabled: boolean;
  in_app_deadline_reminders: boolean;
  in_app_document_updates: boolean;
  in_app_case_updates: boolean;
  in_app_ai_insights: boolean;
  email_enabled: boolean;
  email_fatal_deadlines: boolean;
  email_deadline_reminders: boolean;
  email_daily_digest: boolean;
  email_weekly_digest: boolean;
  remind_days_before_fatal: number[];
  remind_days_before_standard: number[];
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

const validTabs: TabType[] = ['notifications', 'preferences', 'account', 'integrations'];

export default function SettingsPage() {
  const { preferences, fetchPreferences, updatePreferences } = useNotifications();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [localPrefs, setLocalPrefs] = useState<NotificationPreferences | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Get active tab from URL hash or query param, default to 'notifications'
  const getActiveTab = (): TabType => {
    // Check hash first (e.g., /settings#notifications)
    if (typeof window !== 'undefined' && window.location.hash) {
      const hashTab = window.location.hash.slice(1) as TabType;
      if (validTabs.includes(hashTab)) {
        return hashTab;
      }
    }
    // Check query param (e.g., /settings?tab=notifications)
    const tabParam = searchParams.get('tab') as TabType;
    if (tabParam && validTabs.includes(tabParam)) {
      return tabParam;
    }
    return 'notifications';
  };

  const [activeTab, setActiveTab] = useState<TabType>(getActiveTab);

  // Update active tab when URL changes
  useEffect(() => {
    setActiveTab(getActiveTab());
  }, [searchParams]);

  // Listen for hash changes
  useEffect(() => {
    const handleHashChange = () => {
      setActiveTab(getActiveTab());
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Update URL when tab changes
  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    // Update URL hash without triggering navigation
    window.history.replaceState(null, '', `/settings#${tab}`);
  };

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  useEffect(() => {
    if (preferences) {
      setLocalPrefs(preferences);
    }
  }, [preferences]);

  const handleToggle = (key: keyof NotificationPreferences) => {
    if (!localPrefs) return;
    setLocalPrefs({ ...localPrefs, [key]: !localPrefs[key] });
  };

  const handleSave = async () => {
    if (!localPrefs) return;
    setSaving(true);
    setSaveMessage(null);
    try {
      await updatePreferences(localPrefs);
      setSaveMessage({ type: 'success', text: 'Settings saved successfully!' });
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err) {
      setSaveMessage({ type: 'error', text: 'Failed to save settings. Please try again.' });
    } finally {
      setSaving(false);
    }
  };

  const handleExportSettings = () => {
    if (!localPrefs) return;
    const settingsJson = JSON.stringify(localPrefs, null, 2);
    const blob = new Blob([settingsJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `litdocket-settings-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setSaveMessage({ type: 'success', text: 'Settings exported successfully!' });
    setTimeout(() => setSaveMessage(null), 3000);
  };

  if (!localPrefs) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-3xl mx-auto px-4">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
            <div className="bg-white rounded-lg shadow p-6 space-y-4">
              <div className="h-6 bg-gray-200 rounded w-1/3"></div>
              <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'notifications' as TabType, label: 'Notifications', icon: Bell },
    { id: 'preferences' as TabType, label: 'Preferences', icon: SettingsIcon },
    { id: 'account' as TabType, label: 'Account', icon: User },
    { id: 'integrations' as TabType, label: 'Integrations', icon: Plug },
  ];

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">Settings</h1>

        {/* Save Message */}
        {saveMessage && (
          <div className={`mb-6 p-4 rounded-lg ${
            saveMessage.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {saveMessage.text}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex gap-2 bg-slate-100 rounded-lg p-1 border border-slate-200 mb-6">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-md font-semibold text-sm transition-all duration-200 ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-slate-600 hover:bg-slate-200 hover:text-slate-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        {activeTab === 'notifications' && (
          <div className="space-y-6">
            {/* In-App Notifications */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-slate-200">
                <h2 className="text-lg font-semibold text-slate-900">In-App Notifications</h2>
                <p className="text-sm text-slate-500 mt-1">Control what notifications appear in your notification center</p>
              </div>
              <div className="px-6 py-4 space-y-4">
                <ToggleRow
                  label="Enable In-App Notifications"
                  description="Master switch for all in-app notifications"
                  checked={localPrefs.in_app_enabled}
                  onChange={() => handleToggle('in_app_enabled')}
                />
                <ToggleRow
                  label="Deadline Reminders"
                  description="Get notified about upcoming and overdue deadlines"
                  checked={localPrefs.in_app_deadline_reminders}
                  onChange={() => handleToggle('in_app_deadline_reminders')}
                  disabled={!localPrefs.in_app_enabled}
                />
                <ToggleRow
                  label="Document Updates"
                  description="Notifications when documents are uploaded or analyzed"
                  checked={localPrefs.in_app_document_updates}
                  onChange={() => handleToggle('in_app_document_updates')}
                  disabled={!localPrefs.in_app_enabled}
                />
                <ToggleRow
                  label="Case Updates"
                  description="Notifications for case status changes"
                  checked={localPrefs.in_app_case_updates}
                  onChange={() => handleToggle('in_app_case_updates')}
                  disabled={!localPrefs.in_app_enabled}
                />
                <ToggleRow
                  label="AI Insights"
                  description="Receive AI-generated insights and suggestions"
                  checked={localPrefs.in_app_ai_insights}
                  onChange={() => handleToggle('in_app_ai_insights')}
                  disabled={!localPrefs.in_app_enabled}
                />
              </div>
            </div>

            {/* Email Notifications */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-slate-200">
                <h2 className="text-lg font-semibold text-slate-900">Email Notifications</h2>
                <p className="text-sm text-slate-500 mt-1">Choose which notifications to receive via email</p>
              </div>
              <div className="px-6 py-4 space-y-4">
                <ToggleRow
                  label="Enable Email Notifications"
                  description="Master switch for all email notifications"
                  checked={localPrefs.email_enabled}
                  onChange={() => handleToggle('email_enabled')}
                />
                <ToggleRow
                  label="Fatal Deadline Alerts"
                  description="CRITICAL: Email alerts for fatal (malpractice-risk) deadlines"
                  checked={localPrefs.email_fatal_deadlines}
                  onChange={() => handleToggle('email_fatal_deadlines')}
                  disabled={!localPrefs.email_enabled}
                  highlight
                />
                <ToggleRow
                  label="Deadline Reminders"
                  description="Email reminders for upcoming deadlines"
                  checked={localPrefs.email_deadline_reminders}
                  onChange={() => handleToggle('email_deadline_reminders')}
                  disabled={!localPrefs.email_enabled}
                />
                <ToggleRow
                  label="Daily Digest"
                  description="Daily summary of upcoming deadlines and case activity"
                  checked={localPrefs.email_daily_digest}
                  onChange={() => handleToggle('email_daily_digest')}
                  disabled={!localPrefs.email_enabled}
                />
                <ToggleRow
                  label="Weekly Digest"
                  description="Weekly summary of your cases and deadlines"
                  checked={localPrefs.email_weekly_digest}
                  onChange={() => handleToggle('email_weekly_digest')}
                  disabled={!localPrefs.email_enabled}
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'preferences' && (
          <div className="space-y-6">
            {/* Quiet Hours */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-slate-200">
                <h2 className="text-lg font-semibold text-slate-900">Quiet Hours</h2>
                <p className="text-sm text-slate-500 mt-1">Pause non-critical notifications during specified hours</p>
              </div>
              <div className="px-6 py-4 space-y-4">
                <ToggleRow
                  label="Enable Quiet Hours"
                  description="Pause notifications during quiet hours (except fatal deadlines)"
                  checked={localPrefs.quiet_hours_enabled}
                  onChange={() => handleToggle('quiet_hours_enabled')}
                />
                {localPrefs.quiet_hours_enabled && (
                  <div className="flex gap-4 mt-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Start Time</label>
                      <input
                        type="time"
                        value={localPrefs.quiet_hours_start}
                        onChange={(e) => setLocalPrefs({ ...localPrefs, quiet_hours_start: e.target.value })}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-slate-700 mb-1">End Time</label>
                      <input
                        type="time"
                        value={localPrefs.quiet_hours_end}
                        onChange={(e) => setLocalPrefs({ ...localPrefs, quiet_hours_end: e.target.value })}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'account' && (
          <div className="space-y-6">
            {/* Export Settings */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-slate-200">
                <h2 className="text-lg font-semibold text-slate-900">Data Export</h2>
                <p className="text-sm text-slate-500 mt-1">Export your settings and preferences</p>
              </div>
              <div className="px-6 py-4">
                <button
                  onClick={handleExportSettings}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors font-medium"
                >
                  <Download className="w-4 h-4" />
                  <span>Export Settings (JSON)</span>
                </button>
                <p className="text-xs text-slate-500 mt-2">
                  Download your notification preferences and settings as a JSON file
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'integrations' && (
          <div className="space-y-6">
            {/* Coming Soon */}
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <Plug className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-800 mb-2">Integrations Coming Soon</h3>
              <p className="text-slate-600">
                Connect LitDocket with your favorite tools like Outlook, Slack, and more
              </p>
            </div>
          </div>
        )}

        {/* Save Button */}
        {(activeTab === 'notifications' || activeTab === 'preferences') && (
          <div className="flex justify-end mt-6">
            <button
              onClick={handleSave}
              disabled={saving}
              className={`px-6 py-3 rounded-lg font-medium text-white transition-colors ${
                saving
                  ? 'bg-slate-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg'
              }`}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Toggle Row Component
interface ToggleRowProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
  highlight?: boolean;
}

function ToggleRow({ label, description, checked, onChange, disabled = false, highlight = false }: ToggleRowProps) {
  return (
    <div className={`flex items-center justify-between py-3 ${disabled ? 'opacity-50' : ''}`}>
      <div className="flex-1 pr-4">
        <p className={`font-medium text-base ${highlight ? 'text-red-700' : 'text-slate-900'}`}>{label}</p>
        <p className="text-sm text-slate-500 mt-0.5">{description}</p>
      </div>
      <button
        type="button"
        onClick={onChange}
        disabled={disabled}
        className={`relative inline-flex h-8 w-14 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          disabled ? 'cursor-not-allowed' : ''
        } ${checked ? (highlight ? 'bg-red-600' : 'bg-blue-600') : 'bg-slate-200'}`}
        role="switch"
        aria-checked={checked}
      >
        <span
          className={`pointer-events-none inline-block h-7 w-7 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
            checked ? 'translate-x-6' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  );
}
