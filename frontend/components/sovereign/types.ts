/**
 * Sovereign Graph Engine - Type Definitions
 *
 * The "Clean Room" type system for jurisdictional rule management.
 * These types mirror the Supabase schema but add frontend-specific properties.
 */

// ============================================
// CORE ENTITY TYPES
// ============================================

export type JurisdictionType = 'federal' | 'state' | 'local' | 'bankruptcy' | 'appellate';

export type CourtType =
  | 'circuit'
  | 'county'
  | 'district'
  | 'bankruptcy'
  | 'appellate_state'
  | 'appellate_federal'
  | 'supreme_state'
  | 'supreme_federal';

export type DependencyType = 'concurrent' | 'inherits' | 'supplements' | 'overrides';

export type TriggerType =
  | 'case_filed'
  | 'service_completed'
  | 'complaint_served'
  | 'answer_due'
  | 'discovery_commenced'
  | 'discovery_deadline'
  | 'dispositive_motions_due'
  | 'pretrial_conference'
  | 'trial_date'
  | 'hearing_scheduled'
  | 'motion_filed'
  | 'order_entered'
  | 'appeal_filed'
  | 'mediation_scheduled'
  | 'custom_trigger';

export type DeadlinePriority = 'informational' | 'standard' | 'important' | 'critical' | 'fatal';

export type CalculationMethod = 'calendar_days' | 'court_days' | 'business_days';

export type ServiceMethod =
  | 'personal'
  | 'certified_mail'
  | 'first_class_mail'
  | 'electronic'
  | 'publication'
  | 'secretary_of_state'
  | 'posting';

// ============================================
// DATABASE ENTITIES
// ============================================

export interface Jurisdiction {
  id: string;
  code: string;
  name: string;
  description: string | null;
  canonical_slug: string | null;
  jurisdiction_type: JurisdictionType;
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
  canonical_slug: string | null;
  jurisdiction_id: string;
  court_type: CourtType;
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
  dependency_type: DependencyType;
  priority: number;
  notes: string | null;
  created_at: string;
}

export interface RuleTemplate {
  id: string;
  rule_set_id: string;
  rule_code: string;
  name: string;
  description: string | null;
  trigger_type: TriggerType;
  citation: string | null;
  court_type: CourtType | null;
  case_types: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RuleTemplateDeadline {
  id: string;
  rule_template_id: string;
  name: string;
  description: string | null;
  days_from_trigger: number;
  priority: DeadlinePriority;
  party_responsible: string | null;
  action_required: string | null;
  calculation_method: CalculationMethod;
  add_service_days: boolean;
  rule_citation: string | null;
  notes: string | null;
  conditions: Record<string, unknown>;
  display_order: number;
  is_active: boolean;
  created_at: string;
  source_text: string | null;
  source_url: string | null;
  ai_extracted: boolean;
  extraction_confidence: number | null;
  last_verified_at: string | null;
  verified_by: string | null;
}

export interface Holiday {
  id: string;
  name: string;
  holiday_date: string;
  holiday_type: 'federal' | 'state' | 'court' | 'judicial';
  jurisdiction_id: string | null;
  is_recurring: boolean;
  recurring_month: number | null;
  recurring_day: number | null;
  recurring_weekday: number | null;
  recurring_week: number | null;
  notes: string | null;
  created_at: string;
}

export interface ServiceMethodRule {
  id: string;
  jurisdiction_id: string;
  service_method: ServiceMethod;
  additional_days: number;
  rule_citation: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface RuleConflict {
  id: string;
  rule_set_a_id: string;
  rule_set_b_id: string;
  conflict_type: string;
  description: string;
  resolution_strategy: 'strictest' | 'local_prevails' | 'federal_prevails' | 'user_choice';
  resolution_notes: string | null;
  auto_resolve: boolean;
  created_at: string;
}

// ============================================
// UI STATE TYPES
// ============================================

/**
 * Tree node for the SovereignTreeGrid
 * Represents a jurisdiction in the hierarchy
 */
export interface JurisdictionNode extends Jurisdiction {
  children: JurisdictionNode[];
  ruleSets: RuleSet[];
  isExpanded: boolean;
  isSelected: boolean;
  isLocked: boolean; // Cannot be deselected (required by child)
  isLoading: boolean;
  depth: number;
  hasChildren: boolean;
  ruleSetCount: number;
}

/**
 * Rule set with resolved dependencies
 */
export interface ResolvedRuleSet extends RuleSet {
  dependencies: RuleSetWithDependency[];
  isSelected: boolean;
  isLocked: boolean; // Required by another selected rule set
  lockedBy: string[]; // IDs of rule sets that require this one
  conflictsWith: RuleConflictInfo[];
}

export interface RuleSetWithDependency extends RuleSet {
  dependency_type: DependencyType;
  priority: number;
  depth: number;
  is_root: boolean;
}

/**
 * Conflict information for display
 */
export interface RuleConflictInfo {
  conflictId: string;
  otherRuleSetId: string;
  otherRuleSetName: string;
  conflictType: string;
  description: string;
  resolution: string;
  autoResolved: boolean;
}

/**
 * Selection state for the tree grid
 */
export interface SelectionState {
  selectedJurisdictions: Set<string>;
  selectedRuleSets: Set<string>;
  lockedJurisdictions: Set<string>;
  lockedRuleSets: Set<string>;
  conflicts: RuleConflictInfo[];
}

/**
 * Calculated deadline result
 */
export interface CalculatedDeadline {
  templateId: string;
  deadlineId: string;
  name: string;
  description: string | null;
  triggerDate: Date;
  deadlineDate: Date;
  daysFromTrigger: number;
  priority: DeadlinePriority;
  partyResponsible: string | null;
  actionRequired: string | null;
  ruleCitation: string | null;
  calculationMethod: CalculationMethod;
  serviceMethod: ServiceMethod;
  serviceDaysAdded: number;
  holidaysSkipped: number;
  calculationNotes: string;
  ruleSetCode: string;
  ruleSetName: string;
}

/**
 * Date calculation request
 */
export interface DateCalculationRequest {
  triggerDate: Date;
  triggerType: TriggerType;
  ruleSetIds: string[];
  serviceMethod: ServiceMethod;
  jurisdictionId: string;
}

// ============================================
// TREE GRID PROPS
// ============================================

export interface SovereignTreeGridProps {
  /** Initially selected rule set IDs */
  initialSelection?: string[];
  /** Called when selection changes */
  onSelectionChange?: (selection: SelectionState) => void;
  /** Called when conflicts are detected */
  onConflictsDetected?: (conflicts: RuleConflictInfo[]) => void;
  /** Whether to show the rule details panel */
  showRuleDetails?: boolean;
  /** Whether selection is disabled (read-only mode) */
  disabled?: boolean;
  /** Optional class name */
  className?: string;
}

export interface ConflictResolverProps {
  conflicts: RuleConflictInfo[];
  onResolve: (conflictId: string, resolution: string) => void;
  onDismiss: () => void;
}

// ============================================
// API RESPONSE TYPES
// ============================================

export interface JurisdictionTreeResponse {
  id: string;
  code: string;
  name: string;
  canonical_slug: string | null;
  jurisdiction_type: JurisdictionType;
  parent_jurisdiction_id: string | null;
  state: string | null;
  is_active: boolean;
  rule_set_count: number;
  child_count: number;
}

export interface RuleSetOverviewResponse {
  id: string;
  code: string;
  name: string;
  canonical_slug: string | null;
  description: string | null;
  court_type: CourtType;
  is_local: boolean;
  jurisdiction_name: string;
  jurisdiction_slug: string | null;
  dependency_count: number;
  template_count: number;
  deadline_count: number;
}

export interface ResolvedDependencyResponse {
  rule_set_id: string;
  code: string;
  name: string;
  canonical_slug: string | null;
  dependency_type: DependencyType;
  priority: number;
  depth: number;
  is_root: boolean;
}

export interface DeadlineCalculationResponse {
  deadline_date: string;
  service_days_added: number;
  holidays_skipped: number;
  calculation_notes: string;
}
