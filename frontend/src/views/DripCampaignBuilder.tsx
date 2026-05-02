// =============================================================================
// Stratum AI — Drip Campaign Builder (Drag & Drop Flow Editor)
// =============================================================================

import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  Workflow, Mail, Clock, GitBranch, Play, Pause, Trash2, Copy,
  Plus, Save, Zap, UserPlus, ShoppingCart,
  AlertTriangle, LogIn, Package, Bell, MousePointerClick,
  GripVertical, X, Settings
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────

interface FlowNode {
  id: string;
  type: 'trigger' | 'email' | 'wait' | 'condition' | 'notification' | 'end';
  position: { x: number; y: number };
  data: Record<string, any>;
}

interface FlowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

/*
interface DripSequence {
  id: string;
  name: string;
  description: string;
  trigger_type: string;
  status: 'draft' | 'active' | 'paused' | 'archived';
  nodes: FlowNode[];
  edges: FlowEdge[];
  entry_count: number;
}
*/

// ── Node Templates ─────────────────────────────────────────────────────────

const NODE_TEMPLATES = [
  {
    type: 'trigger' as const,
    label: 'Trigger',
    icon: Zap,
    color: 'bg-amber-500',
    description: 'Start the sequence',
    defaults: { trigger_type: 'user_subscribed' },
  },
  {
    type: 'email' as const,
    label: 'Send Email',
    icon: Mail,
    color: 'bg-blue-500',
    description: 'Send newsletter email',
    defaults: { subject: '', template_id: '' },
  },
  {
    type: 'wait' as const,
    label: 'Wait',
    icon: Clock,
    color: 'bg-slate-500',
    description: 'Delay before next step',
    defaults: { delay_hours: 24 },
  },
  {
    type: 'condition' as const,
    label: 'Condition',
    icon: GitBranch,
    color: 'bg-purple-500',
    description: 'Branch based on action',
    defaults: { condition: 'email_opened' },
  },
  {
    type: 'notification' as const,
    label: 'Push Notify',
    icon: Bell,
    color: 'bg-rose-500',
    description: 'Send push notification',
    defaults: { title: '', body: '' },
  },
  {
    type: 'end' as const,
    label: 'End',
    icon: X,
    color: 'bg-gray-500',
    description: 'End of sequence',
    defaults: {},
  },
];

const TRIGGER_OPTIONS = [
  { value: 'user_subscribed', label: 'User Subscribed', icon: UserPlus },
  { value: 'cart_abandoned', label: 'Cart Abandoned', icon: ShoppingCart },
  { value: 'campaign_roas_drop', label: 'ROAS Drops Below', icon: AlertTriangle },
  { value: 'days_since_login', label: 'Days Since Login', icon: LogIn },
  { value: 'post_purchase', label: 'Post Purchase', icon: Package },
  { value: 'custom_event', label: 'Custom Event', icon: Zap },
  { value: 'manual', label: 'Manual Trigger', icon: MousePointerClick },
];

const CONDITION_OPTIONS = [
  { value: 'email_opened', label: 'Email Opened' },
  { value: 'email_not_opened', label: 'Email Not Opened' },
  { value: 'link_clicked', label: 'Link Clicked' },
  { value: 'link_not_clicked', label: 'Link Not Clicked' },
  { value: 'roas_above', label: 'ROAS Above' },
  { value: 'roas_below', label: 'ROAS Below' },
];

// ── Component ──────────────────────────────────────────────────────────────

export default function DripCampaignBuilder() {
  useNavigate(); // imported for future navigation hooks
  const canvasRef = useRef<HTMLDivElement>(null);

  const [sequenceName, setSequenceName] = useState('New Drip Sequence');
  const [sequenceDesc, setSequenceDesc] = useState('');
  const [selectedTrigger, setSelectedTrigger] = useState('user_subscribed');
  const [status, setStatus] = useState<'draft' | 'active'>('draft');

  const [nodes, setNodes] = useState<FlowNode[]>([
    {
      id: 'node_trigger',
      type: 'trigger',
      position: { x: 400, y: 50 },
      data: { trigger_type: 'user_subscribed' },
    },
    {
      id: 'node_end',
      type: 'end',
      position: { x: 400, y: 500 },
      data: {},
    },
  ]);

  const [edges, setEdges] = useState<FlowEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [, setDraggedType] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // ── Drag & Drop ──────────────────────────────────────────────────────

  const onDragStart = (e: React.DragEvent, nodeType: string) => {
    e.dataTransfer.setData('application/node-type', nodeType);
    e.dataTransfer.effectAllowed = 'copy';
    setDraggedType(nodeType);
  };

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);

    const nodeType = e.dataTransfer.getData('application/node-type');
    if (!nodeType || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const template = NODE_TEMPLATES.find((t) => t.type === nodeType);
    if (!template) return;

    const newNode: FlowNode = {
      id: `node_${Date.now()}`,
      type: template.type,
      position: { x: x - 80, y: y - 30 },
      data: { ...template.defaults },
    };

    setNodes((prev) => [...prev, newNode]);
  }, []);

  // ── Node Selection & Config ──────────────────────────────────────────

  const selectedNodeData = nodes.find((n) => n.id === selectedNode);

  const updateNodeData = (nodeId: string, newData: Record<string, any>) => {
    setNodes((prev) =>
      prev.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...newData } } : n))
    );
  };

  const deleteNode = (nodeId: string) => {
    setNodes((prev) => prev.filter((n) => n.id !== nodeId));
    setEdges((prev) => prev.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedNode(null);
  };

  const duplicateNode = (nodeId: string) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    const newNode: FlowNode = {
      ...node,
      id: `node_${Date.now()}`,
      position: { x: node.position.x + 20, y: node.position.y + 20 },
    };
    setNodes((prev) => [...prev, newNode]);
  };

  // ── Edge Connection (simple: click source, click target) ─────────────

  const [connectingFrom, setConnectingFrom] = useState<string | null>(null);

  const handleNodeClick = (nodeId: string) => {
    if (connectingFrom && connectingFrom !== nodeId) {
      // Complete connection
      const edgeId = `edge_${connectingFrom}_${nodeId}`;
      if (!edges.find((e) => e.id === edgeId)) {
        setEdges((prev) => [...prev, { id: edgeId, source: connectingFrom, target: nodeId }]);
      }
      setConnectingFrom(null);
    } else {
      setSelectedNode(nodeId);
    }
  };

  const startConnection = (nodeId: string) => {
    setConnectingFrom(nodeId);
  };

  // ── Save ─────────────────────────────────────────────────────────────

  const saveSequence = async () => {
    const token = sessionStorage.getItem('access_token') || '';
    const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';

    const body = {
        name: sequenceName,
        description: sequenceDesc,
        trigger_type: selectedTrigger,
        trigger_config: {},
        nodes,
        edges,
        status: status,
      };

    try {
      const res = await fetch(`${API_URL}/drip-campaigns`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (data.success) {
        alert('Sequence saved successfully!');
        return;
      }
    } catch {
      // Save locally for demo
    }
    localStorage.setItem('drip_sequence', JSON.stringify(body));
    alert('Sequence saved locally (demo mode)');
  };

  // ── Render ───────────────────────────────────────────────────────────

  return (
    <div className="h-screen flex bg-[#050B18] text-white">
      {/* Left Sidebar — Node Palette */}
      <div className="w-64 border-r border-foreground/10 flex flex-col bg-[#0A1628]">
        <div className="p-4 border-b border-foreground/10">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <Workflow className="w-4 h-4 text-primary" />
            Flow Nodes
          </h2>
          <p className="text-[10px] text-muted-foreground mt-1">Drag to canvas</p>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {NODE_TEMPLATES.map((template) => {
            const Icon = template.icon;
            return (
              <div
                key={template.type}
                draggable
                onDragStart={(e) => onDragStart(e, template.type)}
                className="flex items-center gap-3 p-2.5 rounded-lg bg-foreground/[0.03] hover:bg-foreground/[0.08] border border-foreground/[0.06] hover:border-foreground/[0.12] cursor-grab active:cursor-grabbing transition-all group"
              >
                <div className={cn('w-8 h-8 rounded-md flex items-center justify-center', template.color)}>
                  <Icon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <div className="text-xs font-medium">{template.label}</div>
                  <div className="text-[10px] text-muted-foreground">{template.description}</div>
                </div>
                <GripVertical className="w-3 h-3 text-muted-foreground/30 ml-auto group-hover:text-muted-foreground/60" />
              </div>
            );
          })}
        </div>

        {/* Trigger Selector */}
        <div className="p-4 border-t border-foreground/10">
          <label className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2 block">
            Trigger Type
          </label>
          <select
            value={selectedTrigger}
            onChange={(e) => setSelectedTrigger(e.target.value)}
            className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-2 py-1.5 text-xs text-foreground"
          >
            {TRIGGER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-[#0A1628]">
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Center — Canvas */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="h-14 border-b border-foreground/10 flex items-center justify-between px-4 bg-[#0A1628]/50">
          <div className="flex items-center gap-3">
            <input
              value={sequenceName}
              onChange={(e) => setSequenceName(e.target.value)}
              className="bg-transparent text-sm font-semibold focus:outline-none focus:ring-1 focus:ring-primary/40 rounded px-2 py-1"
            />
            <span
              className={cn(
                'text-[10px] px-2 py-0.5 rounded-full',
                status === 'active' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-yellow-500/15 text-yellow-400'
              )}
            >
              {status}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {connectingFrom && (
              <span className="text-[10px] text-primary animate-pulse">
                Connecting from node... click target
              </span>
            )}
            <button
              onClick={() => setStatus(status === 'draft' ? 'active' : 'draft')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                status === 'draft'
                  ? 'bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25'
                  : 'bg-yellow-500/15 text-yellow-400 hover:bg-yellow-500/25'
              )}
            >
              {status === 'draft' ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
              {status === 'draft' ? 'Activate' : 'Pause'}
            </button>
            <button
              onClick={saveSequence}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
            >
              <Save className="w-3 h-3" />
              Save
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div
          ref={canvasRef}
          className={cn(
            'flex-1 relative overflow-auto',
            dragOver ? 'bg-primary/5' : 'bg-[#050B18]'
          )}
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          {/* Edges (SVG) */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minWidth: 800, minHeight: 600 }}>
            {edges.map((edge) => {
              const source = nodes.find((n) => n.id === edge.source);
              const target = nodes.find((n) => n.id === edge.target);
              if (!source || !target) return null;
              return (
                <g key={edge.id}>
                  <line
                    x1={source.position.x + 80}
                    y1={source.position.y + 30}
                    x2={target.position.x + 80}
                    y2={target.position.y + 30}
                    stroke="rgba(255,255,255,0.15)"
                    strokeWidth={2}
                    markerEnd="url(#arrowhead)"
                  />
                  {edge.label && (
                    <text
                      x={(source.position.x + target.position.x) / 2 + 80}
                      y={(source.position.y + target.position.y) / 2 + 25}
                      fill="rgba(255,255,255,0.5)"
                      fontSize={10}
                      textAnchor="middle"
                    >
                      {edge.label}
                    </text>
                  )}
                </g>
              );
            })}
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="rgba(255,255,255,0.3)" />
              </marker>
            </defs>
          </svg>

          {/* Nodes */}
          {nodes.map((node) => {
            const template = NODE_TEMPLATES.find((t) => t.type === node.type);
            if (!template) return null;
            const Icon = template.icon;
            const isSelected = selectedNode === node.id;
            const isConnecting = connectingFrom === node.id;

            return (
              <div
                key={node.id}
                className={cn(
                  'absolute cursor-pointer select-none transition-all',
                  isSelected && 'ring-2 ring-primary/50',
                  isConnecting && 'ring-2 ring-amber-400/50 animate-pulse'
                )}
                style={{ left: node.position.x, top: node.position.y }}
                onClick={() => handleNodeClick(node.id)}
              >
                <div className="flex items-center gap-2 bg-[#0A1628] border border-foreground/[0.08] hover:border-foreground/[0.15] rounded-xl px-3 py-2 shadow-lg shadow-black/20 min-w-[160px]">
                  <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center shrink-0', template.color)}>
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium truncate">{template.label}</div>
                    {node.data.subject && (
                      <div className="text-[10px] text-muted-foreground truncate">{node.data.subject}</div>
                    )}
                    {node.data.delay_hours && (
                      <div className="text-[10px] text-muted-foreground">Wait {node.data.delay_hours}h</div>
                    )}
                  </div>
                  {/* Connection handle */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      startConnection(node.id);
                    }}
                    className="w-5 h-5 rounded-full bg-foreground/10 hover:bg-primary/30 flex items-center justify-center transition-colors"
                    title="Connect to another node"
                  >
                    <Plus className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })}

          {/* Drop hint */}
          {dragOver && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="bg-primary/10 border-2 border-dashed border-primary/30 rounded-2xl px-8 py-4">
                <p className="text-sm text-primary">Drop node here</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Sidebar — Node Config */}
      <div className="w-72 border-l border-foreground/10 bg-[#0A1628] flex flex-col">
        <div className="p-4 border-b border-foreground/10">
          <h2 className="font-semibold text-sm">
            {selectedNodeData ? 'Node Configuration' : 'Sequence Settings'}
          </h2>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!selectedNodeData ? (
            // Sequence-level settings
            <>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1 block">
                  Sequence Name
                </label>
                <input
                  value={sequenceName}
                  onChange={(e) => setSequenceName(e.target.value)}
                  className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary/40"
                />
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1 block">
                  Description
                </label>
                <textarea
                  value={sequenceDesc}
                  onChange={(e) => setSequenceDesc(e.target.value)}
                  rows={3}
                  className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary/40 resize-none"
                  placeholder="What does this sequence do?"
                />
              </div>
              <div className="pt-2 border-t border-foreground/10">
                <div className="text-[10px] text-muted-foreground mb-2">FLOW STATS</div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-foreground/[0.02] rounded-lg p-2 text-center">
                    <div className="text-lg font-bold">{nodes.length}</div>
                    <div className="text-[10px] text-muted-foreground">Nodes</div>
                  </div>
                  <div className="bg-foreground/[0.02] rounded-lg p-2 text-center">
                    <div className="text-lg font-bold">{edges.length}</div>
                    <div className="text-[10px] text-muted-foreground">Connections</div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            // Node-specific config
            <>
              <div className="flex items-center gap-2 mb-2">
                {(() => {
                  const t = NODE_TEMPLATES.find((nt) => nt.type === selectedNodeData.type);
                  const Icon = t?.icon || Settings;
                  return (
                    <>
                      <div className={cn('w-6 h-6 rounded flex items-center justify-center', t?.color)}>
                        <Icon className="w-3 h-3 text-white" />
                      </div>
                      <span className="text-sm font-medium">{t?.label}</span>
                    </>
                  );
                })()}
              </div>

              {/* Email Config */}
              {selectedNodeData.type === 'email' && (
                <>
                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase mb-1 block">Subject Line</label>
                    <input
                      value={selectedNodeData.data.subject || ''}
                      onChange={(e) => updateNodeData(selectedNodeData.id, { subject: e.target.value })}
                      placeholder="Email subject..."
                      className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase mb-1 block">Template</label>
                    <select
                      value={selectedNodeData.data.template_id || ''}
                      onChange={(e) => updateNodeData(selectedNodeData.id, { template_id: e.target.value })}
                      className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="">Select template...</option>
                      <option value="welcome">Welcome Email</option>
                      <option value="promotional">Promotional</option>
                      <option value="alert">Alert</option>
                      <option value="digest">Weekly Digest</option>
                    </select>
                  </div>
                </>
              )}

              {/* Wait Config */}
              {selectedNodeData.type === 'wait' && (
                <>
                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase mb-1 block">
                      Delay: {selectedNodeData.data.delay_hours || 24} hours
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={168}
                      value={selectedNodeData.data.delay_hours || 24}
                      onChange={(e) =>
                        updateNodeData(selectedNodeData.id, { delay_hours: parseInt(e.target.value) })
                      }
                      className="w-full accent-primary"
                    />
                    <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                      <span>1h</span>
                      <span>7d</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-1 mt-2">
                    {[1, 24, 48, 72, 168].map((h) => (
                      <button
                        key={h}
                        onClick={() => updateNodeData(selectedNodeData.id, { delay_hours: h })}
                        className={cn(
                          'text-[10px] py-1 rounded transition-colors',
                          (selectedNodeData.data.delay_hours || 24) === h
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-foreground/[0.03] text-muted-foreground hover:bg-foreground/[0.08]'
                        )}
                      >
                        {h < 24 ? `${h}h` : `${h / 24}d`}
                      </button>
                    ))}
                  </div>
                </>
              )}

              {/* Condition Config */}
              {selectedNodeData.type === 'condition' && (
                <>
                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase mb-1 block">Condition</label>
                    <select
                      value={selectedNodeData.data.condition || 'email_opened'}
                      onChange={(e) => updateNodeData(selectedNodeData.id, { condition: e.target.value })}
                      className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-sm"
                    >
                      {CONDITION_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="text-[10px] text-muted-foreground mt-2 p-2 bg-foreground/[0.02] rounded-lg">
                    Connect two outgoing edges:
                    <br />• <span className="text-emerald-400">Yes branch</span> — condition met
                    <br />• <span className="text-red-400">No branch</span> — condition not met
                  </div>
                </>
              )}

              {/* Trigger Config */}
              {selectedNodeData.type === 'trigger' && (
                <>
                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase mb-1 block">Trigger Type</label>
                    <select
                      value={selectedNodeData.data.trigger_type || 'user_subscribed'}
                      onChange={(e) => {
                        updateNodeData(selectedNodeData.id, { trigger_type: e.target.value });
                        setSelectedTrigger(e.target.value);
                      }}
                      className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-sm"
                    >
                      {TRIGGER_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {/* Push Notification Config */}
              {selectedNodeData.type === 'notification' && (
                <>
                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase mb-1 block">Title</label>
                    <input
                      value={selectedNodeData.data.title || ''}
                      onChange={(e) => updateNodeData(selectedNodeData.id, { title: e.target.value })}
                      placeholder="Notification title..."
                      className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase mb-1 block">Body</label>
                    <textarea
                      value={selectedNodeData.data.body || ''}
                      onChange={(e) => updateNodeData(selectedNodeData.id, { body: e.target.value })}
                      rows={3}
                      placeholder="Notification body..."
                      className="w-full bg-foreground/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-sm resize-none"
                    />
                  </div>
                </>
              )}

              {/* Node Actions */}
              <div className="flex gap-2 pt-3 border-t border-foreground/10">
                <button
                  onClick={() => duplicateNode(selectedNodeData.id)}
                  className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded-lg bg-foreground/[0.03] hover:bg-foreground/[0.08] text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Copy className="w-3 h-3" /> Duplicate
                </button>
                <button
                  onClick={() => deleteNode(selectedNodeData.id)}
                  className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors"
                >
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
