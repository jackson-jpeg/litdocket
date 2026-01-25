import { useState, useCallback, useEffect } from 'react';
import apiClient from '@/lib/api-client';

interface RuleTemplate {
  id: string;
  rule_name: string;
  slug: string;
  jurisdiction: string;
  trigger_type: string;
  status: 'draft' | 'active' | 'deprecated' | 'archived';
  version_count: number;
  usage_count: number;
  is_public: boolean;
  is_official: boolean;
  created_at: string;
  description?: string;
  tags?: string[];
  version?: {
    id: string;
    version_number: number;
    version_name: string;
    rule_schema: any;
    status: string;
    created_at: string;
  };
}

interface RuleExecution {
  id: string;
  rule_template_id: string;
  case_id: string;
  trigger_data: any;
  deadlines_created: number;
  execution_time_ms: number;
  status: string;
  error_message?: string;
  executed_at: string;
}

interface CreateRuleRequest {
  rule_name: string;
  slug: string;
  jurisdiction: string;
  trigger_type: string;
  description?: string;
  tags?: string[];
  is_public?: boolean;
  rule_schema: any;
}

interface ExecuteRuleRequest {
  rule_template_id: string;
  case_id: string;
  trigger_data: any;
  dry_run?: boolean;
}

interface ExecuteRuleResponse {
  deadlines_created: number;
  execution_time_ms: number;
  rule_name: string;
  rule_version: number;
  errors: string[];
  deadlines: Array<{
    id: string;
    title: string;
    deadline_date: string | null;
    priority: string;
    rule_citation: string;
  }>;
}

interface UseRulesOptions {
  jurisdiction?: string;
  trigger_type?: string;
  status?: string;
  include_public?: boolean;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export function useRules({
  jurisdiction,
  trigger_type,
  status,
  include_public = true,
  onSuccess,
  onError
}: UseRulesOptions = {}) {
  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState<RuleTemplate[]>([]);
  const [selectedRule, setSelectedRule] = useState<RuleTemplate | null>(null);
  const [executions, setExecutions] = useState<RuleExecution[]>([]);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch list of available rule templates
   */
  const fetchRules = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get('/rules/templates', {
        params: {
          jurisdiction,
          trigger_type,
          status,
          include_public
        }
      });

      if (response.data.success) {
        setRules(response.data.data);
        return response.data.data;
      } else {
        throw new Error(response.data.message || 'Failed to fetch rules');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch rules';
      setError(errorMessage);
      onError?.(new Error(errorMessage));
      return [];
    } finally {
      setLoading(false);
    }
  }, [jurisdiction, trigger_type, status, include_public, onError]);

  /**
   * Fetch a specific rule template with its schema
   */
  const fetchRule = useCallback(async (ruleId: string, versionNumber?: number) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(`/rules/templates/${ruleId}`, {
        params: versionNumber ? { version_number: versionNumber } : {}
      });

      if (response.data.success) {
        const ruleData = response.data.data;
        setSelectedRule(ruleData);
        return ruleData;
      } else {
        throw new Error(response.data.message || 'Failed to fetch rule');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch rule';
      setError(errorMessage);
      onError?.(new Error(errorMessage));
      return null;
    } finally {
      setLoading(false);
    }
  }, [onError]);

  /**
   * Create a new rule template
   */
  const createRule = useCallback(async (request: CreateRuleRequest) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post('/rules/templates', request);

      if (response.data.success) {
        onSuccess?.();
        await fetchRules(); // Refresh list
        return response.data.data;
      } else {
        throw new Error(response.data.message || 'Failed to create rule');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create rule';
      setError(errorMessage);
      onError?.(new Error(errorMessage));
      return null;
    } finally {
      setLoading(false);
    }
  }, [fetchRules, onSuccess, onError]);

  /**
   * Execute a rule to generate deadlines
   */
  const executeRule = useCallback(async (
    request: ExecuteRuleRequest
  ): Promise<ExecuteRuleResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post('/rules/execute', request);

      if (response.data.success) {
        return response.data.data;
      } else {
        throw new Error(response.data.message || 'Failed to execute rule');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to execute rule';
      setError(errorMessage);
      onError?.(new Error(errorMessage));
      return null;
    } finally {
      setLoading(false);
    }
  }, [onError]);

  /**
   * Activate a draft rule (make it available for use)
   */
  const activateRule = useCallback(async (ruleId: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post(`/rules/templates/${ruleId}/activate`);

      if (response.data.success) {
        onSuccess?.();
        await fetchRules(); // Refresh list
        return true;
      } else {
        throw new Error(response.data.message || 'Failed to activate rule');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to activate rule';
      setError(errorMessage);
      onError?.(new Error(errorMessage));
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchRules, onSuccess, onError]);

  /**
   * Fetch execution history for a case or rule
   */
  const fetchExecutions = useCallback(async (caseId?: string, ruleTemplateId?: string) => {
    try {
      const response = await apiClient.get('/rules/executions', {
        params: {
          case_id: caseId,
          rule_template_id: ruleTemplateId
        }
      });

      if (response.data.success) {
        setExecutions(response.data.data);
        return response.data.data;
      }
      return [];
    } catch (err: any) {
      console.error('Failed to fetch executions:', err);
      return [];
    }
  }, []);

  /**
   * Browse public marketplace rules
   */
  const fetchMarketplaceRules = useCallback(async (
    marketplaceJurisdiction?: string,
    marketplaceTriggerType?: string
  ) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get('/rules/marketplace', {
        params: {
          jurisdiction: marketplaceJurisdiction,
          trigger_type: marketplaceTriggerType
        }
      });

      if (response.data.success) {
        return response.data.data;
      }
      return [];
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch marketplace rules';
      setError(errorMessage);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-fetch on mount and when filters change
  useEffect(() => {
    fetchRules();
  }, [jurisdiction, trigger_type, status, include_public]);

  return {
    // State
    loading,
    rules,
    selectedRule,
    executions,
    error,

    // Methods
    fetchRules,
    fetchRule,
    createRule,
    executeRule,
    activateRule,
    fetchExecutions,
    fetchMarketplaceRules,
    setSelectedRule
  };
}

/**
 * Example usage:
 *
 * const {
 *   rules,
 *   loading,
 *   createRule,
 *   executeRule
 * } = useRules({
 *   jurisdiction: 'florida_civil',
 *   trigger_type: 'TRIAL_DATE',
 *   onSuccess: () => toast.success('Rule created!')
 * });
 *
 * // Create a new rule
 * await createRule({
 *   rule_name: 'Florida Civil - Trial Date Chain',
 *   slug: 'florida-civil-trial-date',
 *   jurisdiction: 'florida_civil',
 *   trigger_type: 'TRIAL_DATE',
 *   rule_schema: { ... }
 * });
 *
 * // Execute a rule with dry-run preview
 * const result = await executeRule({
 *   rule_template_id: 'abc123',
 *   case_id: 'case456',
 *   trigger_data: { trial_date: '2026-06-01' },
 *   dry_run: true
 * });
 */
