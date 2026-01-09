'use client';

/**
 * JurisdictionTreeSelector
 *
 * CompuLaw-style hierarchical jurisdiction and rule set selector.
 * Windows Explorer "details view" aesthetic with concurrent rule logic.
 *
 * Features:
 * - Collapsible tree grid layout
 * - Auto-selects parent dependencies (FRCP + FRBP) when child selected
 * - Warnings for missing base rules
 * - Brutalist/Legacy Modern design
 */

import React, { useCallback, useEffect } from 'react';
import { useJurisdictionTree } from './useJurisdictionTree';
import type {
  JurisdictionTreeNode,
  JurisdictionTreeSelectorProps,
  SelectionWarning,
} from './types';

// Icons as simple SVG components for the brutalist look
const ChevronRight = ({ className }: { className?: string }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <path d="M4 2L8 6L4 10V2Z" />
  </svg>
);

const ChevronDown = ({ className }: { className?: string }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <path d="M2 4L6 8L10 4H2Z" />
  </svg>
);

const FolderIcon = ({ className }: { className?: string }) => (
  <svg className={className} width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M1 3H6L7 4H15V13H1V3Z" />
  </svg>
);

const FolderOpenIcon = ({ className }: { className?: string }) => (
  <svg className={className} width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M1 3H6L7 4H15V5H3L1 13V3Z" />
    <path d="M2 6H14L12 13H0L2 6Z" />
  </svg>
);

const RulesIcon = ({ className }: { className?: string }) => (
  <svg className={className} width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M2 1H14V15H2V1ZM4 3V5H12V3H4ZM4 7V9H12V7H4ZM4 11V13H9V11H4Z" />
  </svg>
);

const LinkIcon = ({ className }: { className?: string }) => (
  <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <path d="M4 3H2V10H9V8H4V3Z" />
    <path d="M6 2H10V6L8 4L5 7L4 6L7 3L6 2Z" />
  </svg>
);

// Checkbox with brutalist styling
const Checkbox = ({
  checked,
  indeterminate,
  autoSelected,
  onChange,
  disabled,
}: {
  checked: boolean;
  indeterminate?: boolean;
  autoSelected?: boolean;
  onChange: () => void;
  disabled?: boolean;
}) => (
  <button
    type="button"
    onClick={(e) => {
      e.stopPropagation();
      onChange();
    }}
    disabled={disabled}
    className={`
      w-4 h-4 flex items-center justify-center
      border-2 border-bevel-inset
      ${checked || autoSelected ? 'bg-navy' : 'bg-surface-panel'}
      ${autoSelected && !checked ? 'opacity-60' : ''}
      ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
    `}
    style={{
      borderColor: 'var(--bevel-dark) var(--bevel-light) var(--bevel-light) var(--bevel-dark)',
    }}
    title={autoSelected ? 'Auto-selected (required dependency)' : undefined}
  >
    {(checked || autoSelected) && (
      <svg width="10" height="10" viewBox="0 0 10 10" fill="white">
        <path d="M1 5L4 8L9 2" stroke="white" strokeWidth="2" fill="none" />
      </svg>
    )}
    {indeterminate && !checked && !autoSelected && (
      <div className="w-2 h-0.5 bg-navy" />
    )}
  </button>
);

// Single tree node row
const TreeNodeRow = ({
  node,
  depth,
  onToggleSelect,
  onToggleExpand,
  showDependencyBadges,
}: {
  node: JurisdictionTreeNode;
  depth: number;
  onToggleSelect: (id: string) => void;
  onToggleExpand: (id: string) => void;
  showDependencyBadges: boolean;
}) => {
  const hasChildren = node.children.length > 0;
  const isJurisdiction = node.type === 'jurisdiction';
  const isRuleSet = node.type === 'rule_set';

  // Determine if any children are selected
  const hasSelectedChildren = node.children.some(
    c => c.isSelected || c.isAutoSelected
  );

  // Node type badge text
  const getTypeBadge = () => {
    if (isJurisdiction) {
      switch (node.nodeType) {
        case 'federal': return 'FED';
        case 'state': return 'STATE';
        case 'local': return 'LOCAL';
        case 'bankruptcy': return 'BKCY';
        case 'appellate': return 'APP';
        default: return null;
      }
    }
    if (isRuleSet && node.isLocal) {
      return 'LOCAL';
    }
    return null;
  };

  const typeBadge = getTypeBadge();

  return (
    <>
      <div
        className={`
          tree-node flex items-center gap-2 py-1
          ${node.isSelected ? 'bg-navy text-white' : ''}
          ${node.isAutoSelected && !node.isSelected ? 'bg-surface' : ''}
          hover:bg-surface-dark
        `}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {/* Expand/collapse button */}
        <button
          type="button"
          onClick={() => onToggleExpand(node.id)}
          className={`
            w-4 h-4 flex items-center justify-center
            ${hasChildren ? 'cursor-pointer' : 'invisible'}
          `}
        >
          {hasChildren && (
            node.isExpanded ? <ChevronDown /> : <ChevronRight />
          )}
        </button>

        {/* Checkbox */}
        <Checkbox
          checked={node.isSelected}
          autoSelected={node.isAutoSelected}
          indeterminate={hasSelectedChildren && !node.isSelected}
          onChange={() => onToggleSelect(node.id)}
        />

        {/* Icon */}
        <span className={`${node.isSelected ? 'text-white' : 'text-navy'}`}>
          {isJurisdiction ? (
            node.isExpanded ? <FolderOpenIcon /> : <FolderIcon />
          ) : (
            <RulesIcon />
          )}
        </span>

        {/* Name */}
        <span
          className={`
            font-mono text-sm flex-1 truncate
            ${node.isSelected ? 'font-semibold' : ''}
          `}
          onClick={() => hasChildren && onToggleExpand(node.id)}
        >
          {node.code}
          <span className="ml-2 font-sans text-xs opacity-75">
            {node.name}
          </span>
        </span>

        {/* Type badge */}
        {typeBadge && (
          <span className={`
            text-xs px-1 py-0.5 font-mono
            ${node.isSelected ? 'bg-white/20 text-white' : 'badge-neutral'}
          `}>
            {typeBadge}
          </span>
        )}

        {/* Dependency indicator */}
        {showDependencyBadges && isRuleSet && node.requiredRuleSets && node.requiredRuleSets.length > 0 && (
          <span
            className={`
              text-xs flex items-center gap-1
              ${node.isSelected ? 'text-white/70' : 'text-grey-500'}
            `}
            title={`Requires ${node.requiredRuleSets.length} concurrent rule set(s)`}
          >
            <LinkIcon />
            {node.requiredRuleSets.length}
          </span>
        )}

        {/* Child count */}
        {hasChildren && (
          <span className={`
            text-xs font-mono
            ${node.isSelected ? 'text-white/70' : 'text-grey-400'}
          `}>
            ({node.children.length})
          </span>
        )}
      </div>

      {/* Render children if expanded */}
      {node.isExpanded && node.children.map(child => (
        <TreeNodeRow
          key={child.id}
          node={child}
          depth={depth + 1}
          onToggleSelect={onToggleSelect}
          onToggleExpand={onToggleExpand}
          showDependencyBadges={showDependencyBadges}
        />
      ))}
    </>
  );
};

// Warning banner
const WarningBanner = ({ warnings }: { warnings: SelectionWarning[] }) => {
  if (warnings.length === 0) return null;

  return (
    <div className="border-t border-grey-300 bg-warning/10 px-3 py-2">
      {warnings.map((warning, i) => (
        <div key={i} className="flex items-start gap-2 text-sm">
          <span className="text-warning font-bold">!</span>
          <div>
            <p className="text-grey-800">{warning.message}</p>
            {warning.suggestedAction && (
              <p className="text-xs text-grey-500">{warning.suggestedAction}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

// Selection summary footer
const SelectionSummary = ({
  selectedCount,
  autoSelectedCount,
  totalActive,
  codes,
}: {
  selectedCount: number;
  autoSelectedCount: number;
  totalActive: number;
  codes: string[];
}) => (
  <div className="border-t border-grey-300 bg-surface-dark px-3 py-2">
    <div className="flex items-center justify-between">
      <div className="text-xs text-grey-600">
        <span className="font-semibold text-grey-800">{totalActive}</span> active rule sets
        {autoSelectedCount > 0 && (
          <span className="ml-2 text-grey-500">
            ({autoSelectedCount} auto-selected)
          </span>
        )}
      </div>
      {codes.length > 0 && (
        <div className="text-xs font-mono text-navy truncate max-w-[200px]">
          {codes.slice(0, 3).join(' + ')}
          {codes.length > 3 && ` +${codes.length - 3}`}
        </div>
      )}
    </div>
  </div>
);

// Main component
export function JurisdictionTreeSelector({
  value,
  onChange,
  showRuleCounts = true,
  showDependencyBadges = true,
  expandedByDefault = false,
  filterByState,
  onNodeSelect,
  onValidationWarning,
  className = '',
  maxHeight = '400px',
}: JurisdictionTreeSelectorProps) {
  const {
    nodes,
    loading,
    error,
    selectedIds,
    autoSelectedIds,
    toggleNode,
    toggleExpand,
    getSelection,
    validateSelection,
    setSelection,
  } = useJurisdictionTree({
    filterByState,
    expandedByDefault,
  });

  // Sync with controlled value
  useEffect(() => {
    if (value?.primaryRuleSetIds) {
      setSelection(value.primaryRuleSetIds);
    }
  }, [value?.primaryRuleSetIds, setSelection]);

  // Notify parent of selection changes
  const handleToggleSelect = useCallback((nodeId: string) => {
    toggleNode(nodeId);

    // Defer to next tick to get updated selection
    setTimeout(() => {
      const selection = getSelection();
      onChange?.(selection);
      onValidationWarning?.(selection.warnings);
    }, 0);
  }, [toggleNode, getSelection, onChange, onValidationWarning]);

  const selection = getSelection();
  const warnings = validateSelection();

  // Loading state
  if (loading) {
    return (
      <div className={`window-frame ${className}`}>
        <div className="window-titlebar">
          <span className="window-titlebar-text">Jurisdiction Selector</span>
        </div>
        <div className="window-content flex items-center justify-center h-32">
          <span className="text-grey-500 text-sm">Loading jurisdictions...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`window-frame ${className}`}>
        <div className="window-titlebar">
          <span className="window-titlebar-text">Jurisdiction Selector</span>
        </div>
        <div className="window-content">
          <div className="badge-critical p-2">
            Error: {error}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`window-frame ${className}`}>
      {/* Title bar */}
      <div className="window-titlebar flex items-center justify-between">
        <span className="window-titlebar-text">Jurisdiction Selector</span>
        <span className="text-xs font-mono opacity-75">
          {nodes.length} root items
        </span>
      </div>

      {/* Column headers */}
      <div className="flex items-center gap-2 px-3 py-1 bg-surface-dark border-b border-grey-300 text-xs font-semibold text-grey-600 uppercase">
        <span className="w-4" /> {/* Expand spacer */}
        <span className="w-4" /> {/* Checkbox spacer */}
        <span className="w-4" /> {/* Icon spacer */}
        <span className="flex-1">Code / Name</span>
        <span className="w-12 text-center">Type</span>
        {showDependencyBadges && <span className="w-8">Deps</span>}
        {showRuleCounts && <span className="w-12 text-right">Items</span>}
      </div>

      {/* Tree content */}
      <div
        className="window-content overflow-y-auto classic-scrollbar"
        style={{ maxHeight }}
      >
        {nodes.length === 0 ? (
          <div className="text-center py-8 text-grey-500 text-sm">
            No jurisdictions found
          </div>
        ) : (
          <div className="tree-view">
            {nodes.map(node => (
              <TreeNodeRow
                key={node.id}
                node={node}
                depth={0}
                onToggleSelect={handleToggleSelect}
                onToggleExpand={toggleExpand}
                showDependencyBadges={showDependencyBadges}
              />
            ))}
          </div>
        )}
      </div>

      {/* Warnings */}
      <WarningBanner warnings={warnings} />

      {/* Selection summary */}
      <SelectionSummary
        selectedCount={selectedIds.size}
        autoSelectedCount={autoSelectedIds.size}
        totalActive={selection.activeRuleSetIds.length}
        codes={selection.activeRuleSetCodes}
      />
    </div>
  );
}

export default JurisdictionTreeSelector;
