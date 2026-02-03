'use client';

/**
 * SovereignTreeGrid - The Jurisdictional Knowledge Graph Selector
 *
 * "Graph Theory, Not Code Lists"
 *
 * A Windows 95 / Enterprise-style split-pane tree grid for selecting
 * jurisdictions and rule sets. Implements cascading selection where
 * selecting a child automatically locks required parent dependencies.
 *
 * Features:
 * - Hierarchical jurisdiction tree with lazy loading
 * - Automatic dependency resolution (DAG traversal)
 * - Locked selections for required dependencies
 * - Conflict detection and resolution
 * - Brutalist/Enterprise aesthetic
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { supabase, isSupabaseAvailable } from '@/lib/supabase';
import apiClient from '@/lib/api-client';
import {
  Jurisdiction,
  RuleSet,
  JurisdictionNode,
  ResolvedRuleSet,
  SelectionState,
  RuleConflictInfo,
  RuleSetWithDependency,
  SovereignTreeGridProps,
  DependencyType,
} from './types';

// ============================================
// ICONS (Inline SVGs for zero dependencies)
// ============================================

const IconChevronRight = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <path d="M4 2L8 6L4 10V2Z" />
  </svg>
);

const IconChevronDown = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <path d="M2 4L6 8L10 4H2Z" />
  </svg>
);

const IconFolder = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
    <path d="M1 2.5A1.5 1.5 0 012.5 1h2.879a1 1 0 01.707.293L7 2.207h4.5A1.5 1.5 0 0113 3.707V11.5a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 011 11.5v-9z" />
  </svg>
);

const IconFolderOpen = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
    <path d="M1 2.5A1.5 1.5 0 012.5 1h2.879a1 1 0 01.707.293L7 2.207h4.5A1.5 1.5 0 0113 3.707V4H2.5A1.5 1.5 0 001 5.5v-3z" />
    <path d="M1.5 5h11.382a1 1 0 01.894 1.447l-1.764 3.528A2 2 0 0110.236 11H2.5A1.5 1.5 0 011 9.5V5.5a.5.5 0 01.5-.5z" />
  </svg>
);

const IconDocument = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
    <path d="M2 1.5A1.5 1.5 0 013.5 0h5.379a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 01.439 1.061V12.5a1.5 1.5 0 01-1.5 1.5h-8A1.5 1.5 0 012 12.5v-11zM3.5 1a.5.5 0 00-.5.5v11a.5.5 0 00.5.5h8a.5.5 0 00.5-.5V4H9.5A1.5 1.5 0 018 2.5V1H3.5z" />
  </svg>
);

const IconLock = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <path d="M4 4V3a2 2 0 114 0v1h1a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1V5a1 1 0 011-1h1zm1-1a1 1 0 112 0v1H5V3z" />
  </svg>
);

const IconWarning = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
    <path d="M7 0L0 12h14L7 0zm0 4l4.5 7h-9L7 4zm-.5 2v3h1V6h-1zm0 4v1h1v-1h-1z" />
  </svg>
);

const IconCheck = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" />
  </svg>
);

const IconLink = ({ className = '' }: { className?: string }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <path d="M6.5 1.5a2.5 2.5 0 013.536 3.536l-2 2a2.5 2.5 0 01-3.536 0 .5.5 0 01.708-.708 1.5 1.5 0 002.12 0l2-2a1.5 1.5 0 00-2.12-2.12l-.5.5a.5.5 0 01-.708-.708l.5-.5z" />
    <path d="M5.5 10.5a2.5 2.5 0 01-3.536-3.536l2-2a2.5 2.5 0 013.536 0 .5.5 0 01-.708.708 1.5 1.5 0 00-2.12 0l-2 2a1.5 1.5 0 002.12 2.12l.5-.5a.5.5 0 01.708.708l-.5.5z" />
  </svg>
);

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Build the jurisdiction tree from flat array
 */
function buildJurisdictionTree(
  jurisdictions: Jurisdiction[],
  ruleSets: RuleSet[]
): JurisdictionNode[] {
  // Create a map for quick lookup
  const nodeMap = new Map<string, JurisdictionNode>();
  const ruleSetMap = new Map<string, RuleSet[]>();

  // Group rule sets by jurisdiction
  ruleSets.forEach((rs) => {
    const existing = ruleSetMap.get(rs.jurisdiction_id) || [];
    existing.push(rs);
    ruleSetMap.set(rs.jurisdiction_id, existing);
  });

  // Create nodes
  jurisdictions.forEach((j) => {
    const jurisdictionRuleSets = ruleSetMap.get(j.id) || [];
    nodeMap.set(j.id, {
      ...j,
      children: [],
      ruleSets: jurisdictionRuleSets,
      isExpanded: false,
      isSelected: false,
      isLocked: false,
      isLoading: false,
      depth: 0,
      hasChildren: false,
      ruleSetCount: jurisdictionRuleSets.length,
    });
  });

  // Build tree structure
  const roots: JurisdictionNode[] = [];

  nodeMap.forEach((node) => {
    if (node.parent_jurisdiction_id) {
      const parent = nodeMap.get(node.parent_jurisdiction_id);
      if (parent) {
        parent.children.push(node);
        parent.hasChildren = true;
        node.depth = parent.depth + 1;
      } else {
        roots.push(node);
      }
    } else {
      roots.push(node);
    }
  });

  // Calculate depths recursively
  function setDepths(nodes: JurisdictionNode[], depth: number) {
    nodes.forEach((node) => {
      node.depth = depth;
      if (node.children.length > 0) {
        setDepths(node.children, depth + 1);
      }
    });
  }

  setDepths(roots, 0);

  // Sort children alphabetically
  function sortChildren(nodes: JurisdictionNode[]) {
    nodes.sort((a, b) => a.name.localeCompare(b.name));
    nodes.forEach((node) => {
      if (node.children.length > 0) {
        sortChildren(node.children);
      }
    });
  }

  sortChildren(roots);

  return roots;
}

/**
 * Flatten tree for rendering
 */
function flattenTree(
  nodes: JurisdictionNode[],
  result: JurisdictionNode[] = []
): JurisdictionNode[] {
  nodes.forEach((node) => {
    result.push(node);
    if (node.isExpanded && node.children.length > 0) {
      flattenTree(node.children, result);
    }
  });
  return result;
}

// ============================================
// SUBCOMPONENTS
// ============================================

interface TreeNodeRowProps {
  node: JurisdictionNode;
  onToggleExpand: (id: string) => void;
  onToggleSelect: (id: string) => void;
  onSelectRuleSet: (ruleSetId: string, jurisdictionId: string) => void;
  selectedRuleSets: Set<string>;
  lockedRuleSets: Set<string>;
}

const TreeNodeRow: React.FC<TreeNodeRowProps> = ({
  node,
  onToggleExpand,
  onToggleSelect,
  onSelectRuleSet,
  selectedRuleSets,
  lockedRuleSets,
}) => {
  const indent = node.depth * 20;
  const hasRuleSets = node.ruleSets.length > 0;

  return (
    <div className="tree-node-group">
      {/* Jurisdiction Row */}
      <div
        className={`tree-node ${node.isSelected ? 'selected' : ''} ${node.isLocked ? 'locked' : ''}`}
        style={{ paddingLeft: `${indent + 4}px` }}
      >
        {/* Expand/Collapse Toggle */}
        <button
          className="tree-toggle"
          onClick={() => onToggleExpand(node.id)}
          disabled={!node.hasChildren && !hasRuleSets}
        >
          {(node.hasChildren || hasRuleSets) ? (
            node.isExpanded ? (
              <IconChevronDown className="text-ink-secondary" />
            ) : (
              <IconChevronRight className="text-ink-secondary" />
            )
          ) : (
            <span className="w-3" />
          )}
        </button>

        {/* Folder Icon */}
        <span className="tree-icon">
          {node.isExpanded ? (
            <IconFolderOpen className="text-amber" />
          ) : (
            <IconFolder className="text-amber" />
          )}
        </span>

        {/* Node Name */}
        <span className="tree-label flex-1 truncate" title={node.name}>
          {node.name}
        </span>

        {/* Rule Set Count Badge */}
        {node.ruleSetCount > 0 && (
          <span className="tree-badge">{node.ruleSetCount}</span>
        )}

        {/* Lock Icon */}
        {node.isLocked && (
          <span className="tree-lock" title="Required by selected rule set">
            <IconLock className="text-ink-muted" />
          </span>
        )}

        {/* Type Badge */}
        <span className={`tree-type-badge type-${node.jurisdiction_type}`}>
          {node.jurisdiction_type.toUpperCase().slice(0, 3)}
        </span>
      </div>

      {/* Rule Sets (shown when expanded) */}
      {node.isExpanded && node.ruleSets.length > 0 && (
        <div className="rule-set-list" style={{ marginLeft: `${indent + 24}px` }}>
          {node.ruleSets.map((ruleSet) => {
            const isSelected = selectedRuleSets.has(ruleSet.id);
            const isLocked = lockedRuleSets.has(ruleSet.id);

            return (
              <div
                key={ruleSet.id}
                className={`rule-set-item ${isSelected ? 'selected' : ''} ${isLocked ? 'locked' : ''}`}
                onClick={() => !isLocked && onSelectRuleSet(ruleSet.id, node.id)}
              >
                {/* Checkbox */}
                <span className={`rule-checkbox ${isSelected ? 'checked' : ''} ${isLocked ? 'locked' : ''}`}>
                  {isSelected && <IconCheck />}
                  {isLocked && !isSelected && <IconLock className="w-2 h-2" />}
                </span>

                {/* Document Icon */}
                <IconDocument className="text-navy" />

                {/* Rule Set Name */}
                <span className="rule-set-name flex-1 truncate" title={ruleSet.name}>
                  {ruleSet.name}
                </span>

                {/* Code Badge */}
                <span className="rule-set-code font-mono">{ruleSet.code}</span>

                {/* Local Badge */}
                {ruleSet.is_local && <span className="rule-local-badge">LOCAL</span>}

                {/* Lock Icon */}
                {isLocked && (
                  <span className="rule-lock" title="Required by another selected rule">
                    <IconLock className="text-ink-muted" />
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

interface SelectedRulesPanelProps {
  selectedRuleSets: ResolvedRuleSet[];
  onRemoveRuleSet: (id: string) => void;
  conflicts: RuleConflictInfo[];
}

const SelectedRulesPanel: React.FC<SelectedRulesPanelProps> = ({
  selectedRuleSets,
  onRemoveRuleSet,
  conflicts,
}) => {
  const rootSets = selectedRuleSets.filter((rs) => !rs.isLocked);
  const dependencySets = selectedRuleSets.filter((rs) => rs.isLocked);

  return (
    <div className="selected-rules-panel">
      <div className="panel-header">
        <span className="font-serif">Active Rules</span>
        <span className="text-ink-muted text-xs ml-2">({selectedRuleSets.length})</span>
      </div>

      <div className="panel-body">
        {/* Conflicts Warning */}
        {conflicts.length > 0 && (
          <div className="conflict-warning">
            <div className="conflict-header">
              <IconWarning className="text-amber" />
              <span className="font-semibold">RULE CONFLICT DETECTED</span>
            </div>
            {conflicts.map((conflict) => (
              <div key={conflict.conflictId} className="conflict-item">
                <p className="text-xs">{conflict.description}</p>
                <p className="text-xxs text-ink-muted mt-1">
                  Resolution: {conflict.resolution}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Selected Rule Sets */}
        {rootSets.length > 0 && (
          <div className="rule-section">
            <div className="section-header">Selected</div>
            {rootSets.map((rs) => (
              <div key={rs.id} className="active-rule-item">
                <div className="rule-info">
                  <span className="rule-name">{rs.name}</span>
                  <span className="rule-code font-mono">{rs.code}</span>
                </div>
                <button
                  className="rule-remove"
                  onClick={() => onRemoveRuleSet(rs.id)}
                  title="Remove"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Dependencies (Locked) */}
        {dependencySets.length > 0 && (
          <div className="rule-section">
            <div className="section-header">
              <IconLink className="mr-1" />
              Dependencies (Auto-loaded)
            </div>
            {dependencySets.map((rs) => (
              <div key={rs.id} className="active-rule-item locked">
                <div className="rule-info">
                  <span className="rule-name">{rs.name}</span>
                  <span className="rule-code font-mono">{rs.code}</span>
                </div>
                <IconLock className="text-ink-muted" />
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {selectedRuleSets.length === 0 && (
          <div className="empty-state">
            <IconDocument className="text-ink-muted w-8 h-8 mb-2" />
            <p className="text-ink-muted text-sm">No rules selected</p>
            <p className="text-ink-muted text-xs mt-1">
              Select a rule set from the tree to begin
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================

export function SovereignTreeGrid({
  initialSelection = [],
  onSelectionChange,
  onConflictsDetected,
  showRuleDetails = true,
  disabled = false,
  className = '',
}: SovereignTreeGridProps) {
  // State
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [ruleSets, setRuleSets] = useState<RuleSet[]>([]);
  const [dependencies, setDependencies] = useState<Map<string, RuleSetWithDependency[]>>(new Map());
  const [tree, setTree] = useState<JurisdictionNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selection state
  const [selectedRuleSets, setSelectedRuleSets] = useState<Set<string>>(new Set(initialSelection));
  const [lockedRuleSets, setLockedRuleSets] = useState<Set<string>>(new Set());
  const [conflicts, setConflicts] = useState<RuleConflictInfo[]>([]);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');

  // ============================================
  // DATA FETCHING
  // ============================================

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        let jurisdictionsData: Jurisdiction[] = [];
        let ruleSetsData: RuleSet[] = [];
        let depsData: Array<{ rule_set_id: string; required_rule_set_id: string; dependency_type: string; priority: number }> = [];

        // Try Supabase first if available, otherwise fall back to API
        if (isSupabaseAvailable) {
          // Fetch from Supabase directly
          const [jResult, rsResult, depResult] = await Promise.all([
            supabase.from('jurisdictions').select('*').eq('is_active', true).order('name'),
            supabase.from('rule_sets').select('*').eq('is_active', true).order('name'),
            supabase.from('rule_set_dependencies').select('*'),
          ]);

          if (jResult.error) throw jResult.error;
          if (rsResult.error) throw rsResult.error;
          if (depResult.error) throw depResult.error;

          jurisdictionsData = jResult.data || [];
          ruleSetsData = rsResult.data || [];
          depsData = depResult.data || [];
        } else {
          // Fall back to API endpoint
          const response = await apiClient.get('/api/v1/jurisdictions/tree');
          const treeData = response.data;

          // Transform API response to match Supabase format
          jurisdictionsData = (treeData.jurisdictions || []).map((j: {
            id: string;
            code: string;
            name: string;
            jurisdiction_type: string;
            parent_jurisdiction_id?: string;
          }) => ({
            id: j.id,
            code: j.code,
            name: j.name,
            jurisdiction_type: j.jurisdiction_type,
            parent_jurisdiction_id: j.parent_jurisdiction_id || null,
            is_active: true,
          }));

          ruleSetsData = (treeData.rule_sets || []).map((rs: {
            id: string;
            code: string;
            name: string;
            jurisdiction_id: string;
            court_type?: string;
            is_local: boolean;
            dependencies: Array<{ required_rule_set_id: string; dependency_type: string; priority: number }>;
          }) => ({
            id: rs.id,
            code: rs.code,
            name: rs.name,
            jurisdiction_id: rs.jurisdiction_id,
            court_type: rs.court_type,
            is_local: rs.is_local,
            is_active: true,
          }));

          // Extract dependencies from rule sets
          (treeData.rule_sets || []).forEach((rs: {
            id: string;
            dependencies: Array<{ required_rule_set_id: string; dependency_type: string; priority: number }>;
          }) => {
            if (rs.dependencies && rs.dependencies.length > 0) {
              rs.dependencies.forEach((dep) => {
                depsData.push({
                  rule_set_id: rs.id,
                  required_rule_set_id: dep.required_rule_set_id,
                  dependency_type: dep.dependency_type,
                  priority: dep.priority,
                });
              });
            }
          });
        }

        setJurisdictions(jurisdictionsData);
        setRuleSets(ruleSetsData);

        // Build dependency map
        const depMap = new Map<string, RuleSetWithDependency[]>();
        depsData.forEach((dep) => {
          const ruleSet = ruleSetsData.find((rs) => rs.id === dep.required_rule_set_id);
          if (ruleSet) {
            const existing = depMap.get(dep.rule_set_id) || [];
            existing.push({
              ...ruleSet,
              dependency_type: dep.dependency_type as DependencyType,
              priority: dep.priority,
              depth: 1,
              is_root: false,
            });
            depMap.set(dep.rule_set_id, existing);
          }
        });
        setDependencies(depMap);

        // Build tree
        const treeResult = buildJurisdictionTree(jurisdictionsData, ruleSetsData);
        setTree(treeResult);

        setLoading(false);
      } catch (err) {
        console.error('Failed to load jurisdiction data:', err);
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        const message = axiosErr?.response?.data?.detail || 'Unable to load jurisdiction data. Please refresh the page.';
        setError(message);
        setLoading(false);
      }
    }

    loadData();
  }, []);

  // ============================================
  // SELECTION LOGIC
  // ============================================

  /**
   * Resolve all dependencies for selected rule sets
   */
  const resolveDependencies = useCallback(
    (selected: Set<string>): Set<string> => {
      const allRequired = new Set<string>();

      function addDependencies(ruleSetId: string) {
        const deps = dependencies.get(ruleSetId) || [];
        deps.forEach((dep) => {
          if (!allRequired.has(dep.id)) {
            allRequired.add(dep.id);
            // Recursively add dependencies of dependencies
            addDependencies(dep.id);
          }
        });
      }

      selected.forEach((id) => {
        addDependencies(id);
      });

      return allRequired;
    },
    [dependencies]
  );

  /**
   * Handle rule set selection/deselection
   */
  const handleSelectRuleSet = useCallback(
    (ruleSetId: string, _jurisdictionId: string) => {
      if (disabled) return;

      setSelectedRuleSets((prev) => {
        const newSelection = new Set(prev);

        if (newSelection.has(ruleSetId)) {
          // Deselect - only if not locked
          if (!lockedRuleSets.has(ruleSetId)) {
            newSelection.delete(ruleSetId);
          }
        } else {
          // Select
          newSelection.add(ruleSetId);
        }

        return newSelection;
      });
    },
    [disabled, lockedRuleSets]
  );

  /**
   * Remove a rule set from selection
   */
  const handleRemoveRuleSet = useCallback(
    (ruleSetId: string) => {
      if (disabled || lockedRuleSets.has(ruleSetId)) return;

      setSelectedRuleSets((prev) => {
        const newSelection = new Set(prev);
        newSelection.delete(ruleSetId);
        return newSelection;
      });
    },
    [disabled, lockedRuleSets]
  );

  // Update locked rule sets when selection changes
  useEffect(() => {
    const newLocked = resolveDependencies(selectedRuleSets);
    setLockedRuleSets(newLocked);

    // Notify parent of selection change
    if (onSelectionChange) {
      onSelectionChange({
        selectedJurisdictions: new Set(),
        selectedRuleSets: new Set([...selectedRuleSets, ...newLocked]),
        lockedJurisdictions: new Set(),
        lockedRuleSets: newLocked,
        conflicts,
      });
    }
  }, [selectedRuleSets, resolveDependencies, onSelectionChange, conflicts]);

  // ============================================
  // TREE INTERACTION
  // ============================================

  const handleToggleExpand = useCallback((id: string) => {
    setTree((prevTree) => {
      const updateNode = (nodes: JurisdictionNode[]): JurisdictionNode[] => {
        return nodes.map((node) => {
          if (node.id === id) {
            return { ...node, isExpanded: !node.isExpanded };
          }
          if (node.children.length > 0) {
            return { ...node, children: updateNode(node.children) };
          }
          return node;
        });
      };
      return updateNode(prevTree);
    });
  }, []);

  const handleToggleSelect = useCallback((_id: string) => {
    // Jurisdiction selection - could be used for filtering
  }, []);

  // ============================================
  // DERIVED DATA
  // ============================================

  // Flatten tree for rendering
  const flattenedNodes = useMemo(() => {
    let nodes = flattenTree(tree);

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      nodes = nodes.filter(
        (node) =>
          node.name.toLowerCase().includes(query) ||
          node.code.toLowerCase().includes(query) ||
          node.ruleSets.some(
            (rs) =>
              rs.name.toLowerCase().includes(query) ||
              rs.code.toLowerCase().includes(query)
          )
      );
    }

    return nodes;
  }, [tree, searchQuery]);

  // Build resolved rule set list for the panel
  const resolvedRuleSets = useMemo((): ResolvedRuleSet[] => {
    const allSelected = new Set([...selectedRuleSets, ...lockedRuleSets]);
    const result: ResolvedRuleSet[] = [];

    allSelected.forEach((id) => {
      const ruleSet = ruleSets.find((rs) => rs.id === id);
      if (ruleSet) {
        result.push({
          ...ruleSet,
          dependencies: dependencies.get(id) || [],
          isSelected: selectedRuleSets.has(id),
          isLocked: lockedRuleSets.has(id) && !selectedRuleSets.has(id),
          lockedBy: [],
          conflictsWith: [],
        });
      }
    });

    // Sort: selected first, then dependencies
    result.sort((a, b) => {
      if (a.isLocked !== b.isLocked) return a.isLocked ? 1 : -1;
      return a.name.localeCompare(b.name);
    });

    return result;
  }, [selectedRuleSets, lockedRuleSets, ruleSets, dependencies]);

  // ============================================
  // RENDER
  // ============================================

  if (loading) {
    return (
      <div className={`sovereign-tree-grid loading ${className}`}>
        <div className="loading-state">
          <div className="loading-spinner" />
          <span className="text-ink-muted">Loading jurisdiction data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`sovereign-tree-grid error ${className}`}>
        <div className="error-state">
          <IconWarning className="text-alert w-6 h-6 mb-2" />
          <span className="text-alert">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`sovereign-tree-grid ${className}`}>
      {/* Left Panel: Jurisdiction Tree */}
      <div className="tree-panel">
        <div className="panel-header">
          <span className="font-serif">Jurisdiction Navigator</span>
        </div>

        {/* Search */}
        <div className="tree-search">
          <input
            type="text"
            placeholder="Search jurisdictions or rules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input text-sm"
          />
        </div>

        {/* Tree */}
        <div className="tree-body custom-scrollbar">
          {flattenedNodes.length === 0 ? (
            <div className="empty-state py-8">
              <p className="text-ink-muted text-sm">No jurisdictions found</p>
            </div>
          ) : (
            flattenedNodes.map((node) => (
              <TreeNodeRow
                key={node.id}
                node={node}
                onToggleExpand={handleToggleExpand}
                onToggleSelect={handleToggleSelect}
                onSelectRuleSet={handleSelectRuleSet}
                selectedRuleSets={new Set([...selectedRuleSets, ...lockedRuleSets])}
                lockedRuleSets={lockedRuleSets}
              />
            ))
          )}
        </div>
      </div>

      {/* Right Panel: Selected Rules */}
      {showRuleDetails && (
        <SelectedRulesPanel
          selectedRuleSets={resolvedRuleSets}
          onRemoveRuleSet={handleRemoveRuleSet}
          conflicts={conflicts}
        />
      )}

      {/* Inline Styles */}
      <style jsx>{`
        .sovereign-tree-grid {
          display: flex;
          height: 100%;
          min-height: 400px;
          background-color: var(--canvas);
          border: 1px solid var(--grid-line);
        }

        .tree-panel {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-width: 300px;
          border-right: 1px solid var(--grid-line);
        }

        .selected-rules-panel {
          width: 320px;
          display: flex;
          flex-direction: column;
          background-color: var(--paper-white);
        }

        .panel-header {
          padding: 8px 12px;
          background-color: var(--grid-header);
          border-bottom: 1px solid var(--grid-line);
          font-size: 13px;
          font-weight: 600;
        }

        .panel-body {
          flex: 1;
          overflow-y: auto;
          padding: 8px;
        }

        .tree-search {
          padding: 8px;
          border-bottom: 1px solid var(--grid-line);
          background-color: var(--steel);
        }

        .tree-body {
          flex: 1;
          overflow-y: auto;
          background-color: var(--paper-white);
        }

        .tree-node {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          cursor: pointer;
          border-bottom: 1px solid var(--grid-line);
          font-size: 13px;
        }

        .tree-node:hover {
          background-color: var(--grid-zebra);
        }

        .tree-node.selected {
          background-color: var(--navy);
          color: white;
        }

        .tree-node.locked {
          background-color: var(--grid-header);
        }

        .tree-toggle {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 16px;
          height: 16px;
          padding: 0;
          border: none;
          background: none;
          cursor: pointer;
        }

        .tree-toggle:disabled {
          cursor: default;
          opacity: 0.3;
        }

        .tree-icon {
          display: flex;
          align-items: center;
        }

        .tree-label {
          flex: 1;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .tree-badge {
          font-size: 10px;
          padding: 1px 4px;
          background-color: var(--navy);
          color: white;
          font-weight: 600;
        }

        .tree-type-badge {
          font-size: 9px;
          padding: 1px 4px;
          font-weight: 600;
          text-transform: uppercase;
        }

        .tree-type-badge.type-federal {
          background-color: #0A2540;
          color: white;
        }

        .tree-type-badge.type-state {
          background-color: #15803D;
          color: white;
        }

        .tree-type-badge.type-bankruptcy {
          background-color: #B91C1C;
          color: white;
        }

        .tree-type-badge.type-appellate {
          background-color: #7C3AED;
          color: white;
        }

        .tree-type-badge.type-local {
          background-color: #D97706;
          color: white;
        }

        .rule-set-list {
          border-left: 1px dotted var(--ink-muted);
          margin-bottom: 4px;
        }

        .rule-set-item {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 8px;
          font-size: 12px;
          cursor: pointer;
          border-bottom: 1px solid var(--grid-line);
        }

        .rule-set-item:hover {
          background-color: var(--grid-zebra);
        }

        .rule-set-item.selected {
          background-color: #EEF2FF;
          border-left: 2px solid var(--navy);
        }

        .rule-set-item.locked {
          opacity: 0.7;
          cursor: not-allowed;
        }

        .rule-checkbox {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 14px;
          height: 14px;
          border: 1px solid var(--border-dark);
          background-color: var(--paper-white);
        }

        .rule-checkbox.checked {
          background-color: var(--navy);
          color: white;
        }

        .rule-checkbox.locked {
          background-color: var(--grid-header);
        }

        .rule-set-name {
          flex: 1;
        }

        .rule-set-code {
          font-size: 10px;
          color: var(--ink-muted);
        }

        .rule-local-badge {
          font-size: 9px;
          padding: 1px 3px;
          background-color: var(--amber);
          color: white;
          font-weight: 600;
        }

        .conflict-warning {
          background-color: #FEF3C7;
          border: 1px solid var(--amber);
          padding: 8px;
          margin-bottom: 12px;
        }

        .conflict-header {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11px;
          color: var(--amber);
          margin-bottom: 4px;
        }

        .conflict-item {
          padding: 4px 0;
          border-top: 1px solid #FCD34D;
        }

        .rule-section {
          margin-bottom: 12px;
        }

        .section-header {
          display: flex;
          align-items: center;
          font-size: 11px;
          font-weight: 600;
          color: var(--ink-muted);
          text-transform: uppercase;
          margin-bottom: 4px;
          padding-bottom: 4px;
          border-bottom: 1px solid var(--grid-line);
        }

        .active-rule-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 6px 8px;
          background-color: var(--steel);
          border: 1px solid var(--grid-line);
          margin-bottom: 4px;
        }

        .active-rule-item.locked {
          background-color: var(--grid-header);
          opacity: 0.8;
        }

        .rule-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .rule-name {
          font-size: 12px;
          font-weight: 500;
        }

        .rule-code {
          font-size: 10px;
          color: var(--ink-muted);
        }

        .rule-remove {
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          border: none;
          background: none;
          font-size: 16px;
          color: var(--ink-muted);
          cursor: pointer;
        }

        .rule-remove:hover {
          color: var(--alert);
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 24px;
          text-align: center;
        }

        .loading-state,
        .error-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          padding: 24px;
        }

        .loading-spinner {
          width: 24px;
          height: 24px;
          border: 2px solid var(--grid-line);
          border-top-color: var(--navy);
          animation: spin 1s linear infinite;
          margin-bottom: 8px;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}

export default SovereignTreeGrid;
