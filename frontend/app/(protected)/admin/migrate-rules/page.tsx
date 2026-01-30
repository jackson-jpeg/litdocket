'use client';

/**
 * Admin Migration Tool
 *
 * Provides interface to migrate hardcoded rules from rules_engine.py
 * to Authority Core database entries.
 *
 * Features:
 * - Preview all hardcoded rules to be migrated
 * - Filter by jurisdiction
 * - One-click migrate all or selective migration
 * - Progress and status tracking
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  RefreshCw,
  Database,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Play,
  ChevronDown,
  ChevronRight,
  Filter,
  Scale,
  Clock,
  FileText,
  ArrowRightCircle,
  Layers,
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface MigrationRule {
  rule_id: string;
  rule_name: string;
  jurisdiction: string;
  trigger_type: string;
  citation: string;
  deadlines_count: number;
  authority_tier: string;
  already_exists?: boolean;
  jurisdiction_id?: string;
}

interface MigrationPreview {
  total_rules: number;
  already_migrated: number;
  to_migrate: number;
  rules: MigrationRule[];
}

interface MigrationStatus {
  hardcoded_rules: {
    total: number;
    migrated: number;
    pending: number;
    by_jurisdiction: Record<string, { total: number; migrated: number; pending: number }>;
  };
  authority_core_rules: {
    total: number;
    from_migration: number;
    from_other_sources: number;
  };
  migration_complete: boolean;
}

interface MigrationResult {
  success: boolean;
  total_rules: number;
  migrated: number;
  skipped: number;
  errors: Array<{ rule_id: string; error: string }>;
  details: Array<{
    rule_id: string;
    status: string;
    authority_rule_id?: string;
    reason?: string;
  }>;
}

function StatusBadge({ status }: { status: 'migrated' | 'pending' | 'error' }) {
  const styles = {
    migrated: 'bg-green-100 text-green-700',
    pending: 'bg-amber-100 text-amber-700',
    error: 'bg-red-100 text-red-700',
  };

  const labels = {
    migrated: 'Already Migrated',
    pending: 'Pending',
    error: 'Error',
  };

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}

function TierBadge({ tier }: { tier: string }) {
  const styles: Record<string, string> = {
    federal: 'bg-blue-100 text-blue-700',
    state: 'bg-green-100 text-green-700',
    local: 'bg-amber-100 text-amber-700',
    standing_order: 'bg-purple-100 text-purple-700',
    firm: 'bg-slate-100 text-slate-700',
  };

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${styles[tier] || styles.state}`}>
      {tier}
    </span>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const percentage = max > 0 ? (value / max) * 100 : 0;

  return (
    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
      <div
        className={`h-full ${color} transition-all duration-500`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

export default function MigrateRulesPage() {
  const router = useRouter();

  const [status, setStatus] = useState<MigrationStatus | null>(null);
  const [preview, setPreview] = useState<MigrationPreview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMigrating, setIsMigrating] = useState(false);
  const [migrationResult, setMigrationResult] = useState<MigrationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jurisdictionFilter, setJurisdictionFilter] = useState<string>('');
  const [expandedRules, setExpandedRules] = useState<Set<string>>(new Set());

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [statusRes, previewRes] = await Promise.all([
        apiClient.get<MigrationStatus>('/authority-core/migration/status'),
        apiClient.get<MigrationPreview>('/authority-core/migration/preview'),
      ]);
      setStatus(statusRes.data);
      setPreview(previewRes.data);
    } catch (err) {
      console.error('Failed to fetch migration data:', err);
      setError('Failed to load migration data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleMigrate = async (jurisdiction?: string) => {
    setIsMigrating(true);
    setMigrationResult(null);
    setError(null);

    try {
      const params = jurisdiction ? `?jurisdiction=${jurisdiction}` : '';
      const response = await apiClient.post<MigrationResult>(
        `/authority-core/migration/execute${params}`
      );
      setMigrationResult(response.data);
      // Refresh data after migration
      await fetchData();
    } catch (err) {
      console.error('Migration failed:', err);
      setError('Migration failed. Check the console for details.');
    } finally {
      setIsMigrating(false);
    }
  };

  const toggleExpanded = (ruleId: string) => {
    setExpandedRules(prev => {
      const next = new Set(prev);
      if (next.has(ruleId)) {
        next.delete(ruleId);
      } else {
        next.add(ruleId);
      }
      return next;
    });
  };

  const filteredRules = preview?.rules.filter(
    rule => !jurisdictionFilter || rule.jurisdiction === jurisdictionFilter
  ) || [];

  const jurisdictions = preview
    ? Array.from(new Set(preview.rules.map(r => r.jurisdiction)))
    : [];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-12">
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/rules')}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Database className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-900">Rules Migration</h1>
                  <p className="text-slate-500">Migrate hardcoded rules to Authority Core</p>
                </div>
              </div>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-800">Error</p>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Status Overview */}
        {status && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Hardcoded Rules</h3>
                <FileText className="w-5 h-5 text-slate-400" />
              </div>
              <p className="text-3xl font-bold text-slate-900 mb-2">
                {status.hardcoded_rules.total}
              </p>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-green-600">
                  {status.hardcoded_rules.migrated} migrated
                </span>
                <span className="text-amber-600">
                  {status.hardcoded_rules.pending} pending
                </span>
              </div>
              <div className="mt-4">
                <ProgressBar
                  value={status.hardcoded_rules.migrated}
                  max={status.hardcoded_rules.total}
                  color="bg-green-500"
                />
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Authority Core</h3>
                <Database className="w-5 h-5 text-slate-400" />
              </div>
              <p className="text-3xl font-bold text-slate-900 mb-2">
                {status.authority_core_rules.total}
              </p>
              <div className="flex items-center gap-4 text-sm text-slate-600">
                <span>{status.authority_core_rules.from_migration} from migration</span>
                <span>{status.authority_core_rules.from_other_sources} other</span>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Status</h3>
                {status.migration_complete ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : (
                  <Clock className="w-5 h-5 text-amber-500" />
                )}
              </div>
              <p className={`text-xl font-bold ${status.migration_complete ? 'text-green-600' : 'text-amber-600'}`}>
                {status.migration_complete ? 'Complete' : 'In Progress'}
              </p>
              <p className="text-sm text-slate-600 mt-2">
                {status.migration_complete
                  ? 'All hardcoded rules have been migrated'
                  : `${status.hardcoded_rules.pending} rules still need migration`}
              </p>
              {!status.migration_complete && (
                <button
                  onClick={() => handleMigrate()}
                  disabled={isMigrating}
                  className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {isMigrating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Migrating...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Migrate All
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Migration Result */}
        {migrationResult && (
          <div className={`mb-8 p-6 rounded-xl border ${
            migrationResult.errors.length > 0
              ? 'bg-amber-50 border-amber-200'
              : 'bg-green-50 border-green-200'
          }`}>
            <div className="flex items-center gap-3 mb-4">
              {migrationResult.errors.length > 0 ? (
                <AlertTriangle className="w-6 h-6 text-amber-600" />
              ) : (
                <CheckCircle className="w-6 h-6 text-green-600" />
              )}
              <h3 className="text-lg font-semibold">
                Migration {migrationResult.errors.length > 0 ? 'Completed with Warnings' : 'Successful'}
              </h3>
            </div>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <p className="text-sm text-slate-600">Migrated</p>
                <p className="text-2xl font-bold text-green-600">{migrationResult.migrated}</p>
              </div>
              <div>
                <p className="text-sm text-slate-600">Skipped</p>
                <p className="text-2xl font-bold text-slate-600">{migrationResult.skipped}</p>
              </div>
              <div>
                <p className="text-sm text-slate-600">Errors</p>
                <p className="text-2xl font-bold text-red-600">{migrationResult.errors.length}</p>
              </div>
            </div>
            {migrationResult.errors.length > 0 && (
              <div className="mt-4 p-4 bg-white rounded-lg border border-amber-200">
                <p className="text-sm font-medium text-amber-800 mb-2">Errors:</p>
                <ul className="text-sm text-amber-700 space-y-1">
                  {migrationResult.errors.map((err, idx) => (
                    <li key={idx}>{err.rule_id}: {err.error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* By Jurisdiction */}
        {status && Object.keys(status.hardcoded_rules.by_jurisdiction).length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 mb-8">
            <h3 className="font-semibold text-slate-900 mb-4">By Jurisdiction</h3>
            <div className="space-y-4">
              {Object.entries(status.hardcoded_rules.by_jurisdiction).map(([jur, stats]) => (
                <div key={jur} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Scale className="w-4 h-4 text-slate-400" />
                    <span className="font-medium text-slate-900 capitalize">
                      {jur.replace('_', ' ')}
                    </span>
                    <span className="text-sm text-slate-500">
                      ({stats.total} rules)
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="w-32">
                      <ProgressBar
                        value={stats.migrated}
                        max={stats.total}
                        color="bg-green-500"
                      />
                    </div>
                    <span className="text-sm text-slate-600 w-20 text-right">
                      {stats.migrated}/{stats.total}
                    </span>
                    {stats.pending > 0 && (
                      <button
                        onClick={() => handleMigrate(jur)}
                        disabled={isMigrating}
                        className="flex items-center gap-1 px-3 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 disabled:opacity-50"
                      >
                        <ArrowRightCircle className="w-3 h-3" />
                        Migrate
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Rules Preview */}
        {preview && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900">Hardcoded Rules</h3>
                <p className="text-sm text-slate-500">
                  {filteredRules.length} rules
                  {jurisdictionFilter && ` in ${jurisdictionFilter.replace('_', ' ')}`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={jurisdictionFilter}
                  onChange={(e) => setJurisdictionFilter(e.target.value)}
                  className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm"
                >
                  <option value="">All Jurisdictions</option>
                  {jurisdictions.map((jur) => (
                    <option key={jur} value={jur}>
                      {jur.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
              {filteredRules.map((rule) => (
                <div key={rule.rule_id} className="px-6 py-4">
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => toggleExpanded(rule.rule_id)}
                  >
                    <div className="flex items-center gap-3">
                      {expandedRules.has(rule.rule_id) ? (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                      )}
                      <div>
                        <p className="font-medium text-slate-900">{rule.rule_name}</p>
                        <p className="text-sm text-slate-500">{rule.citation}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <TierBadge tier={rule.authority_tier} />
                      <span className="text-sm text-slate-500">
                        {rule.deadlines_count} deadlines
                      </span>
                      <StatusBadge status={rule.already_exists ? 'migrated' : 'pending'} />
                    </div>
                  </div>

                  {expandedRules.has(rule.rule_id) && (
                    <div className="mt-4 ml-7 p-4 bg-slate-50 rounded-lg">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-slate-500">Rule ID:</span>
                          <span className="ml-2 font-mono text-slate-700">{rule.rule_id}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Jurisdiction:</span>
                          <span className="ml-2 text-slate-700 capitalize">{rule.jurisdiction.replace('_', ' ')}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Trigger Type:</span>
                          <span className="ml-2 text-slate-700">{rule.trigger_type}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Deadlines:</span>
                          <span className="ml-2 text-slate-700">{rule.deadlines_count}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Info Panel */}
        <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-xl">
          <div className="flex items-start gap-4">
            <Layers className="w-6 h-6 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-blue-900 mb-2">About Rule Migration</h3>
              <ul className="space-y-2 text-sm text-blue-800">
                <li>
                  <strong>What gets migrated:</strong> All hardcoded rules from <code>rules_engine.py</code> are converted to Authority Core database entries.
                </li>
                <li>
                  <strong>Confidence score:</strong> Migrated rules get a confidence score of 1.0 (100%) since they are from the trusted hardcoded source.
                </li>
                <li>
                  <strong>Verification:</strong> All migrated rules are automatically marked as verified.
                </li>
                <li>
                  <strong>Safe to re-run:</strong> The migration skips rules that already exist, so you can safely run it multiple times.
                </li>
                <li>
                  <strong>After migration:</strong> Authority Core will use the database rules instead of hardcoded rules when both exist.
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
