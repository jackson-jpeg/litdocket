'use client';

import React, { useCallback, useEffect, useState, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  ConnectionMode,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { apiClient } from '@/lib/api-client';

interface RuleNode {
  id: string;
  rule_code: string;
  rule_name: string;
  trigger_type: string;
  authority_tier: string;
  jurisdiction_name: string;
  deadlines_count: number;
  is_verified: boolean;
  usage_count: number;
}

interface RuleEdge {
  source: string;
  target: string;
  type: 'conflict' | 'same_trigger' | 'supersedes' | 'related';
  label?: string;
  severity?: string;
}

interface GraphData {
  nodes: RuleNode[];
  edges: RuleEdge[];
  tiers: string[];
  jurisdictions: string[];
}

// Tier colors
const TIER_COLORS: Record<string, string> = {
  federal: '#1e40af', // Blue
  state: '#047857', // Green
  local: '#b45309', // Amber
  standing_order: '#7c3aed', // Purple
  firm: '#6b7280', // Gray
};

const TIER_ORDER = ['federal', 'state', 'local', 'standing_order', 'firm'];

// Custom node component
const RuleNodeComponent = ({ data }: { data: RuleNode & { selected?: boolean } }) => {
  const tierColor = TIER_COLORS[data.authority_tier] || '#6b7280';

  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 shadow-md min-w-[200px] max-w-[280px] ${
        data.selected ? 'ring-2 ring-blue-500' : ''
      }`}
      style={{
        borderColor: tierColor,
        backgroundColor: `${tierColor}10`,
      }}
    >
      <div className="flex items-center justify-between mb-1">
        <span
          className="text-xs font-semibold px-2 py-0.5 rounded"
          style={{ backgroundColor: tierColor, color: 'white' }}
        >
          {data.authority_tier.toUpperCase()}
        </span>
        {data.is_verified && (
          <span className="text-green-600 text-xs">✓ Verified</span>
        )}
      </div>
      <h3 className="font-semibold text-sm text-gray-900 truncate" title={data.rule_name}>
        {data.rule_name}
      </h3>
      <p className="text-xs text-gray-500 font-mono">{data.rule_code}</p>
      <div className="flex items-center gap-2 mt-2 text-xs text-gray-600">
        <span className="bg-gray-100 px-2 py-0.5 rounded">{data.trigger_type}</span>
        <span>{data.deadlines_count} deadlines</span>
      </div>
      {data.usage_count > 0 && (
        <div className="text-xs text-gray-500 mt-1">
          Used {data.usage_count} times
        </div>
      )}
    </div>
  );
};

const nodeTypes = {
  ruleNode: RuleNodeComponent,
};

interface RuleDependencyGraphProps {
  jurisdictionId?: string;
  triggerType?: string;
  showConflictsOnly?: boolean;
  onNodeClick?: (nodeId: string) => void;
  height?: string;
}

export default function RuleDependencyGraph({
  jurisdictionId,
  triggerType,
  showConflictsOnly = false,
  onNodeClick,
  height = '600px',
}: RuleDependencyGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedTiers, setSelectedTiers] = useState<string[]>(TIER_ORDER);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Fetch graph data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (jurisdictionId) params.append('jurisdiction_id', jurisdictionId);
        if (triggerType) params.append('trigger_type', triggerType);
        if (showConflictsOnly) params.append('conflicts_only', 'true');

        const response = await apiClient.get(`/api/v1/authority-core/visualization/graph?${params}`);
        setGraphData(response.data);
      } catch (err) {
        setError('Failed to load graph data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [jurisdictionId, triggerType, showConflictsOnly]);

  // Transform data to ReactFlow format
  useEffect(() => {
    if (!graphData) return;

    // Filter nodes by selected tiers
    const filteredNodes = graphData.nodes.filter(n =>
      selectedTiers.includes(n.authority_tier)
    );
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

    // Position nodes in a hierarchical layout by tier
    const tierGroups: Record<string, RuleNode[]> = {};
    TIER_ORDER.forEach(tier => {
      tierGroups[tier] = filteredNodes.filter(n => n.authority_tier === tier);
    });

    const flowNodes: Node[] = [];
    let yOffset = 0;
    const xSpacing = 320;
    const ySpacing = 180;

    TIER_ORDER.forEach(tier => {
      const tierNodes = tierGroups[tier] || [];
      if (tierNodes.length === 0) return;

      tierNodes.forEach((node, index) => {
        const row = Math.floor(index / 3);
        const col = index % 3;

        flowNodes.push({
          id: node.id,
          type: 'ruleNode',
          position: {
            x: col * xSpacing + 50,
            y: yOffset + row * ySpacing
          },
          data: { ...node, selected: node.id === selectedNode },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
        });
      });

      const rows = Math.ceil(tierNodes.length / 3);
      yOffset += rows * ySpacing + 80;
    });

    // Create edges
    const flowEdges: Edge[] = graphData.edges
      .filter(e => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target))
      .map((edge, index) => {
        let strokeColor = '#94a3b8';
        let strokeWidth = 1;
        let animated = false;
        let strokeDasharray = undefined;

        switch (edge.type) {
          case 'conflict':
            strokeColor = edge.severity === 'error' ? '#dc2626' : '#f59e0b';
            strokeWidth = 2;
            animated = true;
            break;
          case 'same_trigger':
            strokeColor = '#3b82f6';
            strokeDasharray = '5,5';
            break;
          case 'supersedes':
            strokeColor = '#8b5cf6';
            strokeWidth = 2;
            break;
          case 'related':
            strokeColor = '#94a3b8';
            strokeDasharray = '3,3';
            break;
        }

        return {
          id: `edge-${index}`,
          source: edge.source,
          target: edge.target,
          type: 'smoothstep',
          animated,
          style: { stroke: strokeColor, strokeWidth, strokeDasharray },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: strokeColor,
          },
          label: edge.label,
          labelStyle: { fontSize: 10 },
        };
      });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [graphData, selectedTiers, selectedNode, setNodes, setEdges]);

  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node.id);
    onNodeClick?.(node.id);
  }, [onNodeClick]);

  const toggleTier = (tier: string) => {
    setSelectedTiers(prev =>
      prev.includes(tier)
        ? prev.filter(t => t !== tier)
        : [...prev, tier]
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center text-red-600" style={{ height }}>
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col" style={{ height }}>
      {/* Tier filter controls */}
      <div className="flex items-center gap-4 p-3 bg-gray-50 border-b">
        <span className="text-sm font-medium text-gray-700">Filter by Tier:</span>
        <div className="flex gap-2">
          {TIER_ORDER.map(tier => (
            <button
              key={tier}
              onClick={() => toggleTier(tier)}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                selectedTiers.includes(tier)
                  ? 'text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
              style={{
                backgroundColor: selectedTiers.includes(tier)
                  ? TIER_COLORS[tier]
                  : undefined
              }}
            >
              {tier.replace('_', ' ').toUpperCase()}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div className="ml-auto flex items-center gap-4 text-xs text-gray-600">
          <div className="flex items-center gap-1">
            <div className="w-4 h-0.5 bg-red-600"></div>
            <span>Conflict</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-0.5 bg-blue-500" style={{ borderTop: '2px dashed #3b82f6' }}></div>
            <span>Same Trigger</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-0.5 bg-purple-500"></div>
            <span>Supersedes</span>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-6 px-3 py-2 bg-white border-b text-sm">
        <span className="text-gray-600">
          <strong>{nodes.length}</strong> rules
        </span>
        <span className="text-gray-600">
          <strong>{edges.filter(e => e.animated).length}</strong> conflicts
        </span>
        <span className="text-gray-600">
          <strong>{graphData?.jurisdictions.length || 0}</strong> jurisdictions
        </span>
      </div>

      {/* Graph */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={2}
        >
          <Background color="#e5e7eb" gap={20} />
          <Controls />
          <MiniMap
            nodeColor={(node) => TIER_COLORS[node.data?.authority_tier] || '#6b7280'}
            maskColor="rgba(0, 0, 0, 0.1)"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
