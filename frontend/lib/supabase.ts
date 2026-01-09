/**
 * Supabase Client Configuration
 *
 * Supabase is the single source of truth for all data:
 * - Jurisdiction and Rule System (CompuLaw-style)
 * - Cases, Deadlines, Documents
 * - User preferences
 *
 * Firebase remains for authentication only.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Environment variables
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Validate configuration
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.warn(
    '[Supabase] Missing configuration. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY'
  );
}

// Create Supabase client
export const supabase: SupabaseClient = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
    },
    // Enable real-time subscriptions
    realtime: {
      params: {
        eventsPerSecond: 10,
      },
    },
  }
);

// ============================================
// Type Definitions
// ============================================

export interface Jurisdiction {
  id: string;
  code: string;
  name: string;
  description: string | null;
  jurisdiction_type: 'federal' | 'state' | 'local' | 'bankruptcy' | 'appellate';
  parent_jurisdiction_id: string | null;
  state: string | null;
  federal_circuit: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RuleSet {
  id: string;
  code: string;
  name: string;
  description: string | null;
  jurisdiction_id: string;
  court_type: string;
  version: string;
  effective_date: string | null;
  is_local: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RuleSetDependency {
  id: string;
  rule_set_id: string;
  required_rule_set_id: string;
  dependency_type: 'concurrent' | 'inherits' | 'supplements' | 'overrides';
  priority: number;
  notes: string | null;
  created_at: string;
  required_rule_set?: RuleSet;
}

export interface RuleTemplate {
  id: string;
  rule_set_id: string;
  rule_code: string;
  name: string;
  description: string | null;
  trigger_type: string;
  citation: string | null;
  court_type: string | null;
  case_types: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deadlines?: RuleTemplateDeadline[];
}

export interface RuleTemplateDeadline {
  id: string;
  rule_template_id: string;
  name: string;
  description: string | null;
  days_from_trigger: number;
  priority: 'informational' | 'standard' | 'important' | 'critical' | 'fatal';
  party_responsible: string | null;
  action_required: string | null;
  calculation_method: 'calendar_days' | 'court_days' | 'business_days';
  add_service_days: boolean;
  rule_citation: string | null;
  notes: string | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
}

export interface CourtLocation {
  id: string;
  jurisdiction_id: string;
  name: string;
  short_name: string | null;
  court_type: string;
  district: string | null;
  circuit: number | null;
  division: string | null;
  detection_patterns: string[];
  case_number_pattern: string | null;
  default_rule_set_id: string | null;
  local_rule_set_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ============================================
// Supabase Query Functions
// ============================================

/**
 * Get all active jurisdictions
 */
export async function getJurisdictions(): Promise<Jurisdiction[]> {
  const { data, error } = await supabase
    .from('jurisdictions')
    .select('*')
    .eq('is_active', true)
    .order('name');

  if (error) {
    console.error('Error fetching jurisdictions:', error);
    return [];
  }

  return data || [];
}

/**
 * Get jurisdiction by code
 */
export async function getJurisdictionByCode(code: string): Promise<Jurisdiction | null> {
  const { data, error } = await supabase
    .from('jurisdictions')
    .select('*')
    .eq('code', code)
    .single();

  if (error) {
    console.error('Error fetching jurisdiction:', error);
    return null;
  }

  return data;
}

/**
 * Get all rule sets, optionally filtered by jurisdiction
 */
export async function getRuleSets(jurisdictionId?: string): Promise<RuleSet[]> {
  let query = supabase
    .from('rule_sets')
    .select('*')
    .eq('is_active', true);

  if (jurisdictionId) {
    query = query.eq('jurisdiction_id', jurisdictionId);
  }

  const { data, error } = await query.order('code');

  if (error) {
    console.error('Error fetching rule sets:', error);
    return [];
  }

  return data || [];
}

/**
 * Get rule set with its dependencies
 */
export async function getRuleSetWithDependencies(ruleSetId: string): Promise<RuleSet & { dependencies: RuleSetDependency[] } | null> {
  const { data: ruleSet, error: rsError } = await supabase
    .from('rule_sets')
    .select('*')
    .eq('id', ruleSetId)
    .single();

  if (rsError || !ruleSet) {
    console.error('Error fetching rule set:', rsError);
    return null;
  }

  const { data: deps, error: depsError } = await supabase
    .from('rule_set_dependencies')
    .select(`
      *,
      required_rule_set:rule_sets!required_rule_set_id(*)
    `)
    .eq('rule_set_id', ruleSetId);

  if (depsError) {
    console.error('Error fetching dependencies:', depsError);
  }

  return {
    ...ruleSet,
    dependencies: deps || [],
  };
}

/**
 * Get rule templates for a rule set
 */
export async function getRuleTemplates(
  ruleSetId: string,
  triggerType?: string
): Promise<RuleTemplate[]> {
  let query = supabase
    .from('rule_templates')
    .select(`
      *,
      deadlines:rule_template_deadlines(*)
    `)
    .eq('rule_set_id', ruleSetId)
    .eq('is_active', true);

  if (triggerType) {
    query = query.eq('trigger_type', triggerType);
  }

  const { data, error } = await query.order('name');

  if (error) {
    console.error('Error fetching rule templates:', error);
    return [];
  }

  return data || [];
}

/**
 * Get court locations for a jurisdiction
 */
export async function getCourtLocations(jurisdictionId?: string): Promise<CourtLocation[]> {
  let query = supabase
    .from('court_locations')
    .select('*')
    .eq('is_active', true);

  if (jurisdictionId) {
    query = query.eq('jurisdiction_id', jurisdictionId);
  }

  const { data, error } = await query.order('name');

  if (error) {
    console.error('Error fetching court locations:', error);
    return [];
  }

  return data || [];
}

/**
 * Get rule sets assigned to a case
 */
export async function getCaseRuleSets(caseId: string): Promise<(RuleSet & { assignment_method: string })[]> {
  const { data, error } = await supabase
    .from('case_rule_sets')
    .select(`
      assignment_method,
      rule_set:rule_sets(*)
    `)
    .eq('case_id', caseId)
    .eq('is_active', true);

  if (error) {
    console.error('Error fetching case rule sets:', error);
    return [];
  }

  return (data || []).map(d => ({
    ...d.rule_set,
    assignment_method: d.assignment_method,
  }));
}

/**
 * Get deadlines for a trigger type from specified rule sets
 */
export async function getTriggerDeadlines(
  ruleSetIds: string[],
  triggerType: string
): Promise<RuleTemplateDeadline[]> {
  const { data, error } = await supabase
    .from('rule_templates')
    .select(`
      deadlines:rule_template_deadlines(*)
    `)
    .in('rule_set_id', ruleSetIds)
    .eq('trigger_type', triggerType)
    .eq('is_active', true);

  if (error) {
    console.error('Error fetching trigger deadlines:', error);
    return [];
  }

  // Flatten deadlines from all templates
  const deadlines: RuleTemplateDeadline[] = [];
  for (const template of data || []) {
    if (template.deadlines) {
      deadlines.push(...template.deadlines);
    }
  }

  // Sort by days_from_trigger
  return deadlines.sort((a, b) => a.days_from_trigger - b.days_from_trigger);
}

// ============================================
// Real-time Subscriptions
// ============================================

/**
 * Subscribe to rule set changes
 */
export function subscribeToRuleSets(
  callback: (payload: { eventType: string; new: RuleSet; old: RuleSet }) => void
) {
  return supabase
    .channel('rule_sets_changes')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'rule_sets' },
      (payload) => callback(payload as any)
    )
    .subscribe();
}

/**
 * Subscribe to jurisdiction changes
 */
export function subscribeToJurisdictions(
  callback: (payload: { eventType: string; new: Jurisdiction; old: Jurisdiction }) => void
) {
  return supabase
    .channel('jurisdictions_changes')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'jurisdictions' },
      (payload) => callback(payload as any)
    )
    .subscribe();
}

// Export default client
export default supabase;
