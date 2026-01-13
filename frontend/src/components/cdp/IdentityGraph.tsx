/**
 * CDP Identity Graph Visualization Component
 * Interactive graph showing profile identities and their relationships
 */

import { useState, useMemo } from 'react'
import {
  Network,
  User,
  Mail,
  Phone,
  Smartphone,
  Globe,
  Key,
  Link2,
  GitMerge,
  History,
  Search,
  Loader2,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Eye,
  RefreshCw,
  Shield,
  Clock,
  ArrowRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useIdentityGraph,
  useCanonicalIdentity,
  useMergeProfiles,
  useMergeHistory,
  useProfileMergeHistory,
  useCDPProfile,
  IdentityGraphNode,
  IdentityGraphEdge,
  ProfileMerge,
  IdentifierType,
} from '@/api/cdp'

// Icon mapping for identifier types
const IDENTIFIER_ICONS: Record<IdentifierType, React.ReactNode> = {
  email: <Mail className="w-4 h-4" />,
  phone: <Phone className="w-4 h-4" />,
  device_id: <Smartphone className="w-4 h-4" />,
  anonymous_id: <Globe className="w-4 h-4" />,
  external_id: <Key className="w-4 h-4" />,
}

// Color mapping for identifier types
const IDENTIFIER_COLORS: Record<IdentifierType, string> = {
  email: 'bg-blue-500',
  phone: 'bg-green-500',
  device_id: 'bg-purple-500',
  anonymous_id: 'bg-gray-500',
  external_id: 'bg-amber-500',
}

interface GraphNodeProps {
  node: IdentityGraphNode
  isSelected: boolean
  isPrimary: boolean
  onClick: () => void
  position: { x: number; y: number }
}

function GraphNode({ node, isSelected, isPrimary, onClick, position }: GraphNodeProps) {
  return (
    <div
      className={cn(
        'absolute flex items-center gap-2 px-3 py-2 rounded-lg border-2 cursor-pointer transition-all transform -translate-x-1/2 -translate-y-1/2',
        isSelected ? 'border-primary ring-2 ring-primary/20 scale-110 z-10' : 'border-border hover:border-primary/50',
        isPrimary ? 'bg-primary/10' : 'bg-card'
      )}
      style={{ left: position.x, top: position.y }}
      onClick={onClick}
    >
      <div className={cn('p-1.5 rounded-full text-white', IDENTIFIER_COLORS[node.type])}>
        {IDENTIFIER_ICONS[node.type]}
      </div>
      <div className="min-w-0">
        <div className="text-xs text-muted-foreground uppercase tracking-wider">{node.type}</div>
        <div className="text-sm font-mono truncate max-w-[120px]" title={node.hash}>
          {node.hash.slice(0, 12)}...
        </div>
      </div>
      {isPrimary && (
        <Shield className="w-4 h-4 text-primary ml-1" />
      )}
    </div>
  )
}

interface GraphEdgeProps {
  from: { x: number; y: number }
  to: { x: number; y: number }
  edge: IdentityGraphEdge
  isHighlighted: boolean
}

function GraphEdge({ from, to, edge, isHighlighted }: GraphEdgeProps) {
  // Calculate midpoint for label
  const midX = (from.x + to.x) / 2
  const midY = (from.y + to.y) / 2

  return (
    <svg className="absolute inset-0 pointer-events-none overflow-visible">
      <line
        x1={from.x}
        y1={from.y}
        x2={to.x}
        y2={to.y}
        className={cn(
          'transition-all',
          isHighlighted ? 'stroke-primary stroke-2' : 'stroke-muted-foreground/30 stroke-1'
        )}
        strokeDasharray={edge.type === 'inferred' ? '4 2' : undefined}
      />
      {/* Confidence indicator */}
      <circle
        cx={midX}
        cy={midY}
        r={4}
        className={cn(
          'fill-background stroke-1',
          isHighlighted ? 'stroke-primary' : 'stroke-muted-foreground/50'
        )}
      />
      <text
        x={midX}
        y={midY + 3}
        textAnchor="middle"
        className="text-[8px] fill-muted-foreground font-medium"
      >
        {Math.round(edge.confidence * 100)}
      </text>
    </svg>
  )
}

interface MergeHistoryItemProps {
  merge: ProfileMerge
}

function MergeHistoryItem({ merge }: MergeHistoryItemProps) {
  const getReasonLabel = (reason: string) => {
    const labels: Record<string, string> = {
      identity_match: 'Identity Match',
      manual_merge: 'Manual Merge',
      login_event: 'Login Event',
      cross_device: 'Cross-Device',
    }
    return labels[reason] || reason
  }

  return (
    <div className={cn(
      'p-3 rounded-lg border',
      merge.is_rolled_back ? 'bg-muted/30 opacity-60' : 'bg-card'
    )}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">{getReasonLabel(merge.merge_reason)}</span>
        {merge.is_rolled_back ? (
          <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 text-xs font-medium">
            Rolled Back
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium">
            Active
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
        <div>
          <span className="block font-medium text-foreground">Events Merged</span>
          {merge.merged_event_count}
        </div>
        <div>
          <span className="block font-medium text-foreground">Identifiers Merged</span>
          {merge.merged_identifier_count}
        </div>
      </div>
      <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
        <Clock className="w-3 h-3" />
        {new Date(merge.created_at).toLocaleString()}
      </div>
    </div>
  )
}

interface IdentityGraphVisualizationProps {
  profileId: string
  onClose?: () => void
}

export function IdentityGraphVisualization({ profileId, onClose: _onClose }: IdentityGraphVisualizationProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [showMergeHistory, setShowMergeHistory] = useState(false)

  const { data: profile, isLoading: profileLoading } = useCDPProfile(profileId)
  const { data: graph, isLoading: graphLoading, refetch: refetchGraph } = useIdentityGraph(profileId)
  const { data: canonical, isLoading: canonicalLoading } = useCanonicalIdentity(profileId)
  const { data: mergeHistory, isLoading: historyLoading } = useProfileMergeHistory(profileId)

  const isLoading = profileLoading || graphLoading || canonicalLoading

  // Calculate node positions in a circular layout
  const nodePositions = useMemo(() => {
    if (!graph?.nodes) return {}

    const positions: Record<string, { x: number; y: number }> = {}
    const centerX = 250
    const centerY = 200
    const radius = 150

    graph.nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / graph.nodes.length - Math.PI / 2
      positions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      }
    })

    return positions
  }, [graph?.nodes])

  // Get edges connected to selected node
  const highlightedEdges = useMemo(() => {
    if (!selectedNode || !graph?.edges) return new Set<string>()

    return new Set(
      graph.edges
        .filter(e => e.source === selectedNode || e.target === selectedNode)
        .map(e => `${e.source}-${e.target}`)
    )
  }, [selectedNode, graph?.edges])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!graph || !profile) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <AlertCircle className="w-12 h-12 text-muted-foreground mb-4" />
        <h3 className="font-semibold mb-2">Profile Not Found</h3>
        <p className="text-sm text-muted-foreground">
          Unable to load identity graph for this profile
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Network className="w-6 h-6 text-primary" />
            Identity Graph
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {graph.total_identifiers} identifiers · {graph.total_links} links
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowMergeHistory(!showMergeHistory)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors',
              showMergeHistory ? 'bg-primary/10 border-primary text-primary' : 'hover:bg-muted'
            )}
          >
            <History className="w-4 h-4" />
            Merge History
          </button>
          <button
            onClick={() => refetchGraph()}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Graph visualization */}
        <div className="lg:col-span-2">
          <div className="relative h-[400px] bg-card rounded-xl border overflow-hidden">
            {/* Edges */}
            {graph.edges.map((edge, index) => {
              const fromPos = nodePositions[edge.source]
              const toPos = nodePositions[edge.target]
              if (!fromPos || !toPos) return null

              return (
                <GraphEdge
                  key={index}
                  from={fromPos}
                  to={toPos}
                  edge={edge}
                  isHighlighted={highlightedEdges.has(`${edge.source}-${edge.target}`)}
                />
              )
            })}

            {/* Nodes */}
            {graph.nodes.map((node) => (
              <GraphNode
                key={node.id}
                node={node}
                isSelected={selectedNode === node.id}
                isPrimary={node.is_primary}
                onClick={() => setSelectedNode(selectedNode === node.id ? null : node.id)}
                position={nodePositions[node.id]}
              />
            ))}

            {/* Legend */}
            <div className="absolute bottom-3 left-3 p-3 bg-background/90 rounded-lg border text-xs space-y-2">
              <div className="font-medium mb-2">Identifier Types</div>
              {Object.entries(IDENTIFIER_ICONS).map(([type, icon]) => (
                <div key={type} className="flex items-center gap-2">
                  <div className={cn('p-1 rounded text-white', IDENTIFIER_COLORS[type as IdentifierType])}>
                    {icon}
                  </div>
                  <span className="capitalize">{type.replace('_', ' ')}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Details panel */}
        <div className="space-y-4">
          {/* Canonical Identity */}
          {canonical && (
            <div className="p-4 rounded-xl border bg-card">
              <h3 className="font-medium flex items-center gap-2 mb-3">
                <Shield className="w-4 h-4 text-primary" />
                Canonical Identity
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Type</span>
                  <span className="font-medium capitalize">{canonical.canonical_type || 'None'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Priority Score</span>
                  <span className="font-medium">{canonical.priority_score}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Verified</span>
                  {canonical.is_verified ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : (
                    <span className="text-muted-foreground">No</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Profile Summary */}
          <div className="p-4 rounded-xl border bg-card">
            <h3 className="font-medium flex items-center gap-2 mb-3">
              <User className="w-4 h-4 text-primary" />
              Profile Summary
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Lifecycle Stage</span>
                <span className="font-medium capitalize">{profile.lifecycle_stage}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Total Events</span>
                <span className="font-medium">{profile.total_events.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Total Revenue</span>
                <span className="font-medium">${profile.total_revenue.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Last Seen</span>
                <span className="font-medium text-xs">
                  {new Date(profile.last_seen_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* Selected Node Details */}
          {selectedNode && (
            <div className="p-4 rounded-xl border bg-primary/5 border-primary/20">
              <h3 className="font-medium flex items-center gap-2 mb-3">
                <Link2 className="w-4 h-4 text-primary" />
                Selected Identifier
              </h3>
              {(() => {
                const node = graph.nodes.find(n => n.id === selectedNode)
                if (!node) return null

                return (
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Type</span>
                      <span className="font-medium capitalize">{node.type}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Priority</span>
                      <span className="font-medium">{node.priority}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Primary</span>
                      {node.is_primary ? (
                        <CheckCircle2 className="w-4 h-4 text-green-500" />
                      ) : (
                        <span className="text-muted-foreground">No</span>
                      )}
                    </div>
                    <div className="pt-2 border-t">
                      <span className="text-muted-foreground block mb-1">Hash</span>
                      <code className="text-xs bg-muted px-2 py-1 rounded block break-all">
                        {node.hash}
                      </code>
                    </div>
                  </div>
                )
              })()}
            </div>
          )}
        </div>
      </div>

      {/* Merge History Panel */}
      {showMergeHistory && (
        <div className="p-4 rounded-xl border bg-card">
          <h3 className="font-medium flex items-center gap-2 mb-4">
            <GitMerge className="w-4 h-4 text-primary" />
            Profile Merge History
          </h3>
          {historyLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            </div>
          ) : mergeHistory?.merges && mergeHistory.merges.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {mergeHistory.merges.map((merge) => (
                <MergeHistoryItem key={merge.id} merge={merge} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <GitMerge className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No merge history for this profile</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Main IdentityGraph component for searching/selecting profiles
export function IdentityGraph() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null)
  const [sourceProfileId, setSourceProfileId] = useState('')
  const [targetProfileId, setTargetProfileId] = useState('')
  const [showMergeForm, setShowMergeForm] = useState(false)

  const { data: globalMergeHistory, isLoading: globalHistoryLoading } = useMergeHistory({ limit: 10 })
  const mergeMutation = useMergeProfiles()

  const handleMerge = async () => {
    if (!sourceProfileId || !targetProfileId) return

    try {
      await mergeMutation.mutateAsync({
        source_profile_id: sourceProfileId,
        target_profile_id: targetProfileId,
      })
      setSourceProfileId('')
      setTargetProfileId('')
      setShowMergeForm(false)
    } catch (error) {
      console.error('Merge failed:', error)
    }
  }

  if (selectedProfileId) {
    return (
      <div>
        <button
          onClick={() => setSelectedProfileId(null)}
          className="flex items-center gap-2 mb-4 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronRight className="w-4 h-4 rotate-180" />
          Back to Overview
        </button>
        <IdentityGraphVisualization
          profileId={selectedProfileId}
          onClose={() => setSelectedProfileId(null)}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Network className="w-6 h-6 text-primary" />
            Identity Graph
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            View and manage profile identity resolution
          </p>
        </div>
        <button
          onClick={() => setShowMergeForm(!showMergeForm)}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
            showMergeForm
              ? 'bg-primary text-primary-foreground'
              : 'border hover:bg-muted'
          )}
        >
          <GitMerge className="w-4 h-4" />
          Manual Merge
        </button>
      </div>

      {/* Manual Merge Form */}
      {showMergeForm && (
        <div className="p-4 rounded-xl border bg-card">
          <h3 className="font-medium mb-4">Merge Two Profiles</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label className="block text-sm font-medium mb-1.5">Source Profile ID</label>
              <input
                type="text"
                value={sourceProfileId}
                onChange={(e) => setSourceProfileId(e.target.value)}
                placeholder="Profile to merge from..."
                className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div className="flex items-center justify-center">
              <ArrowRight className="w-5 h-5 text-muted-foreground" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Target Profile ID</label>
              <input
                type="text"
                value={targetProfileId}
                onChange={(e) => setTargetProfileId(e.target.value)}
                placeholder="Profile to merge into..."
                className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>
          <div className="flex items-center justify-end gap-3 mt-4 pt-4 border-t">
            <button
              onClick={() => setShowMergeForm(false)}
              className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleMerge}
              disabled={!sourceProfileId || !targetProfileId || mergeMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {mergeMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <GitMerge className="w-4 h-4" />
              )}
              Merge Profiles
            </button>
          </div>
        </div>
      )}

      {/* Profile Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Enter a Profile ID to view its identity graph..."
          className="w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && searchQuery) {
              setSelectedProfileId(searchQuery)
            }
          }}
        />
        {searchQuery && (
          <button
            onClick={() => setSelectedProfileId(searchQuery)}
            className="absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors"
          >
            View Graph
          </button>
        )}
      </div>

      {/* Recent Merges */}
      <div>
        <h3 className="font-medium flex items-center gap-2 mb-4">
          <History className="w-4 h-4 text-primary" />
          Recent Profile Merges
        </h3>
        {globalHistoryLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : globalMergeHistory?.merges && globalMergeHistory.merges.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Merged Profile</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Surviving Profile</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Reason</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Events</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Identifiers</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Date</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {globalMergeHistory.merges.map((merge) => (
                  <tr key={merge.id} className="border-b hover:bg-muted/30">
                    <td className="py-3 px-4">
                      <code className="text-xs bg-muted px-2 py-1 rounded">
                        {merge.merged_profile_id.slice(0, 8)}...
                      </code>
                    </td>
                    <td className="py-3 px-4">
                      {merge.surviving_profile_id ? (
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {merge.surviving_profile_id.slice(0, 8)}...
                        </code>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4 capitalize text-sm">
                      {merge.merge_reason.replace('_', ' ')}
                    </td>
                    <td className="py-3 px-4 text-sm">{merge.merged_event_count}</td>
                    <td className="py-3 px-4 text-sm">{merge.merged_identifier_count}</td>
                    <td className="py-3 px-4">
                      {merge.is_rolled_back ? (
                        <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 text-xs font-medium">
                          Rolled Back
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm text-muted-foreground">
                      {new Date(merge.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {merge.surviving_profile_id && (
                        <button
                          onClick={() => setSelectedProfileId(merge.surviving_profile_id!)}
                          className="p-1.5 rounded-md hover:bg-muted transition-colors"
                          title="View Identity Graph"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 bg-card border rounded-xl">
            <GitMerge className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-semibold mb-2">No Recent Merges</h3>
            <p className="text-sm text-muted-foreground">
              Profile merges will appear here when identities are resolved
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default IdentityGraph
