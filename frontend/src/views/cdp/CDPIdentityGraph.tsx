/**
 * CDP Identity Graph - Identity resolution visualization
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ArrowPathIcon,
  CheckBadgeIcon,
  DevicePhoneMobileIcon,
  EnvelopeIcon,
  InformationCircleIcon,
  LinkIcon,
  MagnifyingGlassIcon,
  PhoneIcon,
  ShareIcon,
  UserCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import {
  type IdentifierType,
  type IdentityGraphEdge,
  type IdentityGraphNode,
  type ProfileMerge,
  useCDPProfile,
  useIdentityGraph,
  useMergeProfiles,
  useProfileMergeHistory,
} from '@/api/cdp';

// Node type configuration
const nodeConfig: Record<
  IdentifierType,
  { icon: React.ElementType; color: string; label: string }
> = {
  email: { icon: EnvelopeIcon, color: 'bg-blue-500', label: 'Email' },
  phone: { icon: PhoneIcon, color: 'bg-green-500', label: 'Phone' },
  device_id: { icon: DevicePhoneMobileIcon, color: 'bg-purple-500', label: 'Device' },
  anonymous_id: { icon: UserCircleIcon, color: 'bg-gray-500', label: 'Anonymous' },
  external_id: { icon: LinkIcon, color: 'bg-orange-500', label: 'External' },
};

// Graph Node Component
function GraphNode({
  node,
  x,
  y,
  isSelected,
  onClick,
}: {
  node: IdentityGraphNode;
  x: number;
  y: number;
  isSelected: boolean;
  onClick: () => void;
}) {
  const config = nodeConfig[node.type] || nodeConfig.anonymous_id;
  const Icon = config.icon;

  return (
    <g transform={`translate(${x}, ${y})`} onClick={onClick} className="cursor-pointer">
      {/* Selection ring */}
      {isSelected && (
        <circle
          r={32}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          className="text-primary animate-pulse"
        />
      )}

      {/* Node circle */}
      <circle r={24} className={cn(config.color, 'transition-transform hover:scale-110')} />

      {/* Icon */}
      <foreignObject x={-12} y={-12} width={24} height={24}>
        <Icon className="h-6 w-6 text-white" />
      </foreignObject>

      {/* Primary badge */}
      {node.is_primary && (
        <g transform="translate(16, -16)">
          <circle r={8} className="fill-yellow-400" />
          <foreignObject x={-6} y={-6} width={12} height={12}>
            <CheckBadgeIcon className="h-3 w-3 text-yellow-900" />
          </foreignObject>
        </g>
      )}

      {/* Label */}
      <text y={40} textAnchor="middle" className="text-xs fill-current text-muted-foreground">
        {config.label}
      </text>
    </g>
  );
}

// Graph Edge Component
function GraphEdge({
  edge,
  x1,
  y1,
  x2,
  y2,
}: {
  edge: IdentityGraphEdge;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}) {
  const confidence = edge.confidence * 100;

  return (
    <g>
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke="currentColor"
        strokeWidth={Math.max(1, confidence / 25)}
        className="text-muted-foreground/50"
        strokeDasharray={confidence < 50 ? '4 4' : undefined}
      />
      {/* Edge label */}
      <text
        x={(x1 + x2) / 2}
        y={(y1 + y2) / 2 - 8}
        textAnchor="middle"
        className="text-[10px] fill-current text-muted-foreground"
      >
        {edge.type.replace('_', ' ')}
      </text>
    </g>
  );
}

// Simple force-directed layout
function useGraphLayout(
  nodes: IdentityGraphNode[],
  edges: IdentityGraphEdge[],
  width: number,
  height: number
) {
  return useMemo(() => {
    if (nodes.length === 0) return { nodePositions: new Map<string, { x: number; y: number }>() };

    const positions = new Map<string, { x: number; y: number }>();
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 3;

    // Arrange nodes in a circle
    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      positions.set(node.id, { x, y });
    });

    return { nodePositions: positions };
  }, [nodes, edges, width, height]);
}

// Node Detail Panel
function NodeDetailPanel({ node, onClose }: { node: IdentityGraphNode; onClose: () => void }) {
  const config = nodeConfig[node.type] || nodeConfig.anonymous_id;

  return (
    <div className="absolute top-4 right-4 w-72 bg-card rounded-xl border shadow-lg p-4">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={cn('h-10 w-10 rounded-lg flex items-center justify-center', config.color)}
          >
            <config.icon className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="font-semibold">{config.label}</p>
            <p className="text-xs text-muted-foreground">
              {node.is_primary ? 'Primary' : 'Secondary'}
            </p>
          </div>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-muted rounded">
          <XMarkIcon className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-3 text-sm">
        <div>
          <p className="text-muted-foreground">Identifier Hash</p>
          <p className="font-mono text-xs break-all">{node.hash}</p>
        </div>
        <div>
          <p className="text-muted-foreground">Priority</p>
          <p className="font-medium">{node.priority}</p>
        </div>
        <div>
          <p className="text-muted-foreground">Status</p>
          <p className="font-medium">
            {node.is_primary ? 'Primary Identifier' : 'Linked Identifier'}
          </p>
        </div>
      </div>
    </div>
  );
}

// Merge History Component
function MergeHistory({ profileId }: { profileId: string }) {
  const { data, isLoading } = useProfileMergeHistory(profileId);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <div key={i} className="h-16 bg-muted animate-pulse rounded" />
        ))}
      </div>
    );
  }

  if (!data?.merges || data.merges.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No merge history for this profile
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {data.merges.map((merge) => (
        <div key={merge.id} className="p-3 bg-muted/50 rounded-lg">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium capitalize">
              {merge.merge_reason.replace('_', ' ')}
            </span>
            <span className="text-xs text-muted-foreground">
              {new Date(merge.created_at).toLocaleDateString()}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Merged {merge.merged_event_count} events, {merge.merged_identifier_count} identifiers
          </p>
          {merge.is_rolled_back && (
            <span className="mt-1 inline-block px-2 py-0.5 bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 rounded text-xs">
              Rolled back
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function CDPIdentityGraph() {
  const [searchParams] = useSearchParams();
  const initialProfileId = searchParams.get('profile') || '';

  const [profileId, setProfileId] = useState(initialProfileId);
  const [searchInput, setSearchInput] = useState(initialProfileId);
  const [selectedNode, setSelectedNode] = useState<IdentityGraphNode | null>(null);
  const [showMergeHistory, setShowMergeHistory] = useState(false);

  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });

  const {
    data: graphData,
    isLoading: graphLoading,
    refetch,
  } = useIdentityGraph(profileId, {
    enabled: !!profileId,
  });
  const { data: profile } = useCDPProfile(profileId, { enabled: !!profileId });

  // Update dimensions on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (svgRef.current?.parentElement) {
        const { width, height } = svgRef.current.parentElement.getBoundingClientRect();
        setDimensions({ width, height: Math.max(400, height) });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const { nodePositions } = useGraphLayout(
    graphData?.nodes || [],
    graphData?.edges || [],
    dimensions.width,
    dimensions.height
  );

  const handleSearch = () => {
    setProfileId(searchInput.trim());
    setSelectedNode(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Identity Graph</h1>
          <p className="text-muted-foreground mt-1">
            Visualize identity relationships and profile connections
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-md">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Enter profile ID..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:outline-none font-mono text-sm"
          />
        </div>
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
        >
          Load Graph
        </button>
        {profileId && (
          <button
            onClick={() => refetch()}
            className="p-2 border rounded-lg hover:bg-muted transition-colors"
            title="Refresh"
          >
            <ArrowPathIcon className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Profile Summary */}
      {profile && (
        <div className="bg-card rounded-xl border p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-gradient-stratum flex items-center justify-center">
                <UserCircleIcon className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="font-semibold font-mono">{profile.id.slice(0, 16)}...</p>
                <p className="text-sm text-muted-foreground capitalize">
                  {profile.lifecycle_stage} | {profile.total_events} events | $
                  {profile.total_revenue.toLocaleString()} revenue
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowMergeHistory(!showMergeHistory)}
                className={cn(
                  'px-3 py-1.5 text-sm border rounded-lg transition-colors',
                  showMergeHistory ? 'bg-primary/10 border-primary' : 'hover:bg-muted'
                )}
              >
                Merge History
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Graph Visualization */}
        <div
          className="lg:col-span-2 bg-card rounded-xl border relative"
          style={{ minHeight: 500 }}
        >
          {!profileId ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
              <ShareIcon className="h-16 w-16 mb-4 opacity-50" />
              <p className="text-lg font-medium">Enter a Profile ID</p>
              <p className="text-sm">to visualize identity connections</p>
            </div>
          ) : graphLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
            </div>
          ) : graphData?.nodes && graphData.nodes.length > 0 ? (
            <>
              <svg ref={svgRef} width="100%" height="100%" className="min-h-[500px]">
                {/* Edges */}
                {graphData.edges.map((edge, i) => {
                  const sourcePos = nodePositions.get(edge.source);
                  const targetPos = nodePositions.get(edge.target);
                  if (!sourcePos || !targetPos) return null;
                  return (
                    <GraphEdge
                      key={i}
                      edge={edge}
                      x1={sourcePos.x}
                      y1={sourcePos.y}
                      x2={targetPos.x}
                      y2={targetPos.y}
                    />
                  );
                })}

                {/* Nodes */}
                {graphData.nodes.map((node) => {
                  const pos = nodePositions.get(node.id);
                  if (!pos) return null;
                  return (
                    <GraphNode
                      key={node.id}
                      node={node}
                      x={pos.x}
                      y={pos.y}
                      isSelected={selectedNode?.id === node.id}
                      onClick={() => setSelectedNode(node)}
                    />
                  );
                })}
              </svg>

              {/* Node Detail Panel */}
              {selectedNode && (
                <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
              )}
            </>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
              <InformationCircleIcon className="h-16 w-16 mb-4 opacity-50" />
              <p className="text-lg font-medium">No Identity Graph Data</p>
              <p className="text-sm">This profile has no linked identifiers</p>
            </div>
          )}
        </div>

        {/* Side Panel */}
        <div className="space-y-4">
          {/* Graph Stats */}
          {graphData && (
            <div className="bg-card rounded-xl border p-4">
              <h3 className="font-semibold mb-3">Graph Statistics</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Identifiers</p>
                  <p className="text-xl font-bold">{graphData.total_identifiers}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Connections</p>
                  <p className="text-xl font-bold">{graphData.total_links}</p>
                </div>
              </div>
            </div>
          )}

          {/* Legend */}
          <div className="bg-card rounded-xl border p-4">
            <h3 className="font-semibold mb-3">Legend</h3>
            <div className="space-y-2">
              {Object.entries(nodeConfig).map(([type, config]) => (
                <div key={type} className="flex items-center gap-3">
                  <div
                    className={cn(
                      'h-6 w-6 rounded-full flex items-center justify-center',
                      config.color
                    )}
                  >
                    <config.icon className="h-3 w-3 text-white" />
                  </div>
                  <span className="text-sm">{config.label}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <div className="h-4 w-8 border-2 border-muted-foreground/50" />
                <span className="text-muted-foreground">High confidence</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-4 w-8 border-2 border-muted-foreground/50 border-dashed" />
                <span className="text-muted-foreground">Low confidence</span>
              </div>
            </div>
          </div>

          {/* Merge History */}
          {showMergeHistory && profileId && (
            <div className="bg-card rounded-xl border p-4">
              <h3 className="font-semibold mb-3">Merge History</h3>
              <MergeHistory profileId={profileId} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
