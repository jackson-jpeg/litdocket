/**
 * Jurisdiction Tree Types
 *
 * TypeScript interfaces for the CompuLaw-style Jurisdiction Event Tree.
 * Supports hierarchical selection with concurrent rule loading.
 */

// Node in the jurisdiction tree (can be jurisdiction or rule set)
export interface JurisdictionTreeNode {
  id: string;
  code: string;
  name: string;
  type: 'jurisdiction' | 'rule_set';
  nodeType?: 'federal' | 'state' | 'local' | 'bankruptcy' | 'appellate' | 'rules';
  parentId: string | null;
  children: JurisdictionTreeNode[];
  // Rule set specific
  isLocal?: boolean;
  courtType?: string;
  // Selection state
  isSelected: boolean;
  isAutoSelected: boolean; // True if selected due to dependency
  isExpanded: boolean;
  // Dependencies (for rule sets)
  requiredRuleSets?: string[]; // IDs of rule sets that must be active
  dependencyType?: 'concurrent' | 'inherits' | 'supplements' | 'overrides';
}

// Flat rule set with dependency info (from Supabase)
export interface RuleSetWithDependencies {
  id: string;
  code: string;
  name: string;
  description: string | null;
  jurisdiction_id: string;
  court_type: string;
  is_local: boolean;
  is_active: boolean;
  dependencies: {
    required_rule_set_id: string;
    dependency_type: string;
    priority: number;
  }[];
}

// Selection result returned by the component
export interface JurisdictionSelection {
  // Primary selection (what user clicked)
  primaryJurisdictionId: string | null;
  primaryRuleSetIds: string[];
  // All active rule sets (including dependencies)
  activeRuleSetIds: string[];
  activeRuleSetCodes: string[];
  // Validation
  isValid: boolean;
  warnings: SelectionWarning[];
}

export interface SelectionWarning {
  type: 'missing_base_rules' | 'incomplete_hierarchy' | 'conflicting_rules';
  message: string;
  suggestedAction?: string;
  relatedRuleSetIds?: string[];
}

// Props for the JurisdictionTreeSelector component
export interface JurisdictionTreeSelectorProps {
  // Current selection (controlled component)
  value?: JurisdictionSelection;
  onChange?: (selection: JurisdictionSelection) => void;
  // Display options
  showRuleCounts?: boolean;
  showDependencyBadges?: boolean;
  expandedByDefault?: boolean;
  // Filtering
  filterByState?: string;
  filterByCourtType?: string;
  // Callbacks
  onNodeSelect?: (node: JurisdictionTreeNode) => void;
  onValidationWarning?: (warnings: SelectionWarning[]) => void;
  // Styling
  className?: string;
  maxHeight?: string;
}

// Tree state for the hook
export interface JurisdictionTreeState {
  nodes: JurisdictionTreeNode[];
  flatNodes: Map<string, JurisdictionTreeNode>;
  loading: boolean;
  error: string | null;
}
