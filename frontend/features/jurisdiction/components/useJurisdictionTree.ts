'use client';

/**
 * useJurisdictionTree Hook
 *
 * Fetches jurisdictions and rule sets from Supabase, organizes them into
 * a hierarchical tree structure with dependency tracking.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { supabase } from '@/lib/supabase';
import type {
  JurisdictionTreeNode,
  JurisdictionTreeState,
  JurisdictionSelection,
  SelectionWarning,
  RuleSetWithDependencies,
} from './types';

interface UseJurisdictionTreeOptions {
  filterByState?: string;
  expandedByDefault?: boolean;
}

interface UseJurisdictionTreeReturn extends JurisdictionTreeState {
  // Selection management
  selectedIds: Set<string>;
  autoSelectedIds: Set<string>;
  toggleNode: (nodeId: string) => void;
  expandNode: (nodeId: string) => void;
  collapseNode: (nodeId: string) => void;
  toggleExpand: (nodeId: string) => void;
  // Get current selection with dependencies resolved
  getSelection: () => JurisdictionSelection;
  // Validation
  validateSelection: () => SelectionWarning[];
  // Reset
  clearSelection: () => void;
  setSelection: (ruleSetIds: string[]) => void;
}

export function useJurisdictionTree(
  options: UseJurisdictionTreeOptions = {}
): UseJurisdictionTreeReturn {
  const { filterByState, expandedByDefault = false } = options;

  // State
  const [nodes, setNodes] = useState<JurisdictionTreeNode[]>([]);
  const [flatNodes, setFlatNodes] = useState<Map<string, JurisdictionTreeNode>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [autoSelectedIds, setAutoSelectedIds] = useState<Set<string>>(new Set());
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Dependency map: rule_set_id -> required_rule_set_ids[]
  const [dependencyMap, setDependencyMap] = useState<Map<string, string[]>>(new Map());
  // Reverse dependency map: rule_set_id -> rule_sets that require it
  const [reverseDependencyMap, setReverseDependencyMap] = useState<Map<string, string[]>>(new Map());

  // Fetch and build tree
  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        // Fetch jurisdictions
        let jurisdictionQuery = supabase
          .from('jurisdictions')
          .select('*')
          .eq('is_active', true)
          .order('name');

        if (filterByState) {
          jurisdictionQuery = jurisdictionQuery.or(`state.eq.${filterByState},jurisdiction_type.eq.federal`);
        }

        const { data: jurisdictions, error: jError } = await jurisdictionQuery;
        if (jError) throw jError;

        // Fetch rule sets with dependencies
        const { data: ruleSets, error: rsError } = await supabase
          .from('rule_sets')
          .select(`
            *,
            dependencies:rule_set_dependencies(
              required_rule_set_id,
              dependency_type,
              priority
            )
          `)
          .eq('is_active', true)
          .order('code');

        if (rsError) throw rsError;

        // Build dependency maps
        const depMap = new Map<string, string[]>();
        const reverseDepMap = new Map<string, string[]>();

        for (const rs of ruleSets || []) {
          const deps = rs.dependencies?.map((d: { required_rule_set_id: string }) => d.required_rule_set_id) || [];
          depMap.set(rs.id, deps);

          // Build reverse map
          for (const depId of deps) {
            const existing = reverseDepMap.get(depId) || [];
            existing.push(rs.id);
            reverseDepMap.set(depId, existing);
          }
        }

        setDependencyMap(depMap);
        setReverseDependencyMap(reverseDepMap);

        // Build tree structure
        const { tree, flat } = buildTree(jurisdictions || [], ruleSets || [], expandedByDefault);
        setNodes(tree);
        setFlatNodes(flat);

        // Auto-expand root nodes
        if (expandedByDefault) {
          const rootIds = tree.map(n => n.id);
          setExpandedIds(new Set(rootIds));
        }

      } catch (err) {
        console.error('Error fetching jurisdiction tree:', err);
        setError(err instanceof Error ? err.message : 'Failed to load jurisdictions');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [filterByState, expandedByDefault]);

  // Build tree from flat data
  function buildTree(
    jurisdictions: Array<{
      id: string;
      code: string;
      name: string;
      jurisdiction_type: string;
      parent_jurisdiction_id: string | null;
    }>,
    ruleSets: Array<{
      id: string;
      code: string;
      name: string;
      jurisdiction_id: string;
      court_type: string;
      is_local: boolean;
      dependencies?: Array<{
        required_rule_set_id: string;
        dependency_type: string;
        priority: number;
      }>;
    }>,
    expanded: boolean
  ): { tree: JurisdictionTreeNode[]; flat: Map<string, JurisdictionTreeNode> } {
    const flat = new Map<string, JurisdictionTreeNode>();
    const childrenMap = new Map<string, JurisdictionTreeNode[]>();

    // Create jurisdiction nodes
    for (const j of jurisdictions) {
      const node: JurisdictionTreeNode = {
        id: j.id,
        code: j.code,
        name: j.name,
        type: 'jurisdiction',
        nodeType: j.jurisdiction_type as JurisdictionTreeNode['nodeType'],
        parentId: j.parent_jurisdiction_id,
        children: [],
        isSelected: false,
        isAutoSelected: false,
        isExpanded: expanded,
      };
      flat.set(j.id, node);

      // Track children by parent
      const parentId = j.parent_jurisdiction_id || 'root';
      const siblings = childrenMap.get(parentId) || [];
      siblings.push(node);
      childrenMap.set(parentId, siblings);
    }

    // Create rule set nodes under their jurisdictions
    for (const rs of ruleSets) {
      const node: JurisdictionTreeNode = {
        id: rs.id,
        code: rs.code,
        name: rs.name,
        type: 'rule_set',
        nodeType: 'rules',
        parentId: rs.jurisdiction_id,
        children: [],
        isLocal: rs.is_local,
        courtType: rs.court_type,
        requiredRuleSets: rs.dependencies?.map(d => d.required_rule_set_id) || [],
        isSelected: false,
        isAutoSelected: false,
        isExpanded: false,
      };
      flat.set(rs.id, node);

      // Add to jurisdiction's children
      const siblings = childrenMap.get(rs.jurisdiction_id) || [];
      siblings.push(node);
      childrenMap.set(rs.jurisdiction_id, siblings);
    }

    // Wire up children
    for (const [parentId, children] of childrenMap) {
      if (parentId === 'root') continue;
      const parent = flat.get(parentId);
      if (parent) {
        // Sort: jurisdictions first, then rule sets by code
        parent.children = children.sort((a, b) => {
          if (a.type !== b.type) return a.type === 'jurisdiction' ? -1 : 1;
          return a.code.localeCompare(b.code);
        });
      }
    }

    // Get root nodes (no parent)
    const tree = childrenMap.get('root') || [];
    return { tree: tree.sort((a, b) => a.name.localeCompare(b.name)), flat };
  }

  // Toggle node selection
  const toggleNode = useCallback((nodeId: string) => {
    const node = flatNodes.get(nodeId);
    if (!node) return;

    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, [flatNodes]);

  // Calculate auto-selected IDs based on dependencies
  useEffect(() => {
    const auto = new Set<string>();

    // For each selected rule set, add its dependencies
    for (const id of selectedIds) {
      const deps = dependencyMap.get(id) || [];
      for (const depId of deps) {
        if (!selectedIds.has(depId)) {
          auto.add(depId);
        }
      }
    }

    setAutoSelectedIds(auto);
  }, [selectedIds, dependencyMap]);

  // Expand/collapse
  const expandNode = useCallback((nodeId: string) => {
    setExpandedIds(prev => new Set([...prev, nodeId]));
  }, []);

  const collapseNode = useCallback((nodeId: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      next.delete(nodeId);
      return next;
    });
  }, []);

  const toggleExpand = useCallback((nodeId: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  // Validate selection
  const validateSelection = useCallback((): SelectionWarning[] => {
    const warnings: SelectionWarning[] = [];

    // Check if local rules are selected without base rules
    for (const id of selectedIds) {
      const node = flatNodes.get(id);
      if (!node || node.type !== 'rule_set') continue;

      if (node.isLocal && node.requiredRuleSets?.length) {
        const missingBase = node.requiredRuleSets.filter(
          depId => !selectedIds.has(depId) && !autoSelectedIds.has(depId)
        );

        if (missingBase.length > 0) {
          const missingNames = missingBase
            .map(id => flatNodes.get(id)?.name || id)
            .join(', ');

          warnings.push({
            type: 'missing_base_rules',
            message: `"${node.name}" requires base rules: ${missingNames}`,
            suggestedAction: 'These will be auto-selected',
            relatedRuleSetIds: missingBase,
          });
        }
      }
    }

    return warnings;
  }, [selectedIds, autoSelectedIds, flatNodes]);

  // Get final selection
  const getSelection = useCallback((): JurisdictionSelection => {
    const allActiveIds = new Set([...selectedIds, ...autoSelectedIds]);
    const activeRuleSetIds: string[] = [];
    const activeRuleSetCodes: string[] = [];
    let primaryJurisdictionId: string | null = null;

    for (const id of allActiveIds) {
      const node = flatNodes.get(id);
      if (node?.type === 'rule_set') {
        activeRuleSetIds.push(id);
        activeRuleSetCodes.push(node.code);
      }
    }

    // Find primary jurisdiction (deepest selected jurisdiction)
    for (const id of selectedIds) {
      const node = flatNodes.get(id);
      if (node?.type === 'jurisdiction') {
        primaryJurisdictionId = id;
      }
    }

    const warnings = validateSelection();

    return {
      primaryJurisdictionId,
      primaryRuleSetIds: [...selectedIds].filter(id => flatNodes.get(id)?.type === 'rule_set'),
      activeRuleSetIds,
      activeRuleSetCodes,
      isValid: warnings.length === 0,
      warnings,
    };
  }, [selectedIds, autoSelectedIds, flatNodes, validateSelection]);

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    setAutoSelectedIds(new Set());
  }, []);

  // Set selection programmatically
  const setSelection = useCallback((ruleSetIds: string[]) => {
    setSelectedIds(new Set(ruleSetIds));
  }, []);

  // Update nodes with current selection/expansion state
  const nodesWithState = useMemo(() => {
    function updateNodeState(node: JurisdictionTreeNode): JurisdictionTreeNode {
      return {
        ...node,
        isSelected: selectedIds.has(node.id),
        isAutoSelected: autoSelectedIds.has(node.id),
        isExpanded: expandedIds.has(node.id),
        children: node.children.map(updateNodeState),
      };
    }
    return nodes.map(updateNodeState);
  }, [nodes, selectedIds, autoSelectedIds, expandedIds]);

  return {
    nodes: nodesWithState,
    flatNodes,
    loading,
    error,
    selectedIds,
    autoSelectedIds,
    toggleNode,
    expandNode,
    collapseNode,
    toggleExpand,
    getSelection,
    validateSelection,
    clearSelection,
    setSelection,
  };
}
