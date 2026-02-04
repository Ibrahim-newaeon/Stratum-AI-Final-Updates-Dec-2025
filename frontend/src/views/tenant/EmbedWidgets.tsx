/**
 * Embed Widgets Management
 *
 * Allows users to create, manage, and configure embeddable widgets
 * with tier-appropriate branding levels.
 */

import { useState } from 'react';
import {
  ChartBarIcon,
  CheckIcon,
  ClipboardIcon,
  CodeBracketIcon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  GlobeAltIcon,
  KeyIcon,
  LockClosedIcon,
  PlusIcon,
  ShieldCheckIcon,
  TableCellsIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import {
  BrandingLevel,
  DomainWhitelist,
  EmbedToken,
  EmbedWidget,
  WIDGET_DIMENSIONS,
  WIDGET_TYPE_INFO,
  WidgetSize,
  WidgetType,
} from '@/types/embedWidgets';

// Mock data for demonstration
const mockWidgets: EmbedWidget[] = [
  {
    id: '1',
    name: 'Dashboard Signal Health',
    description: 'Signal health badge for client dashboard',
    widget_type: 'signal_health',
    widget_size: 'standard',
    branding_level: 'full',
    data_scope: { date_range_days: 30 },
    refresh_interval_seconds: 300,
    is_active: true,
    total_views: 1250,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: '2',
    name: 'ROAS Widget',
    description: 'ROAS display for stakeholder reports',
    widget_type: 'roas_display',
    widget_size: 'compact',
    branding_level: 'minimal',
    data_scope: { date_range_days: 7 },
    refresh_interval_seconds: 600,
    is_active: true,
    total_views: 890,
    created_at: '2024-01-10T14:30:00Z',
    updated_at: '2024-01-10T14:30:00Z',
  },
];

const mockDomains: DomainWhitelist[] = [
  {
    id: '1',
    domain_pattern: 'dashboard.example.com',
    is_verified: true,
    is_active: true,
    description: 'Main client dashboard',
    created_at: '2024-01-05T09:00:00Z',
  },
  {
    id: '2',
    domain_pattern: '*.internal.company.com',
    is_verified: true,
    is_active: true,
    description: 'Internal reporting portals',
    created_at: '2024-01-08T11:00:00Z',
  },
];

const mockTierInfo = {
  tier: 'professional',
  branding_level: 'minimal' as BrandingLevel,
  limits: { max_widgets: 10, max_domains: 10 },
  features: { basic_widgets: true, minimal_branding: true, white_label: false },
};

const widgetTypeIcons: Record<WidgetType, React.ReactNode> = {
  signal_health: <ShieldCheckIcon className="w-5 h-5" />,
  roas_display: <ChartBarIcon className="w-5 h-5" />,
  campaign_performance: <TableCellsIcon className="w-5 h-5" />,
  trust_gate_status: <LockClosedIcon className="w-5 h-5" />,
  spend_tracker: <CurrencyDollarIcon className="w-5 h-5" />,
  anomaly_alert: <ExclamationTriangleIcon className="w-5 h-5" />,
};

const brandingBadgeColors: Record<BrandingLevel, string> = {
  full: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  minimal: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  none: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
};

export default function EmbedWidgets() {
  const [widgets, setWidgets] = useState(mockWidgets);
  const [domains, setDomains] = useState(mockDomains);
  const [tierInfo] = useState(mockTierInfo);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDomainDialog, setShowDomainDialog] = useState(false);
  const [showEmbedCodeDialog, setShowEmbedCodeDialog] = useState(false);
  const [selectedWidget, setSelectedWidget] = useState<EmbedWidget | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // New widget form state
  const [newWidget, setNewWidget] = useState({
    name: '',
    description: '',
    widget_type: 'signal_health' as WidgetType,
    widget_size: 'standard' as WidgetSize,
  });

  // New domain form state
  const [newDomain, setNewDomain] = useState({
    domain_pattern: '',
    description: '',
  });

  const handleCreateWidget = () => {
    const widget: EmbedWidget = {
      id: Date.now().toString(),
      ...newWidget,
      branding_level: tierInfo.branding_level,
      data_scope: { date_range_days: 30 },
      refresh_interval_seconds: 300,
      is_active: true,
      total_views: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setWidgets([widget, ...widgets]);
    setShowCreateDialog(false);
    setNewWidget({
      name: '',
      description: '',
      widget_type: 'signal_health',
      widget_size: 'standard',
    });
  };

  const handleAddDomain = () => {
    const domain: DomainWhitelist = {
      id: Date.now().toString(),
      domain_pattern: newDomain.domain_pattern.toLowerCase(),
      is_verified: false,
      is_active: true,
      description: newDomain.description,
      created_at: new Date().toISOString(),
    };
    setDomains([domain, ...domains]);
    setShowDomainDialog(false);
    setNewDomain({ domain_pattern: '', description: '' });
  };

  const handleCopyCode = (code: string, type: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(type);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const generateIframeCode = (widget: EmbedWidget) => {
    const { width, height } =
      widget.widget_size === 'custom'
        ? { width: widget.custom_width, height: widget.custom_height }
        : WIDGET_DIMENSIONS[widget.widget_size];

    return `<iframe
  src="https://app.stratum.ai/embed/v1/widget/${widget.id}?token={YOUR_TOKEN}"
  width="${width}"
  height="${height}"
  frameborder="0"
  sandbox="allow-scripts allow-same-origin"
  loading="lazy"
  title="${widget.name}"
></iframe>`;
  };

  const generateScriptCode = (widget: EmbedWidget) => {
    return `<div id="stratum-widget-${widget.id}"></div>
<script>
(function() {
  var w = document.createElement('script');
  w.src = 'https://app.stratum.ai/embed/v1/loader.js';
  w.async = true;
  w.dataset.widgetId = '${widget.id}';
  w.dataset.token = '{YOUR_TOKEN}';
  document.head.appendChild(w);
})();
</script>`;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Embed Widgets</h1>
          <p className="text-gray-400 mt-1">
            Create embeddable widgets for external dashboards and reports
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className={brandingBadgeColors[tierInfo.branding_level]}>
            {tierInfo.branding_level === 'full' && 'Full Branding'}
            {tierInfo.branding_level === 'minimal' && 'Minimal Branding'}
            {tierInfo.branding_level === 'none' && 'White Label'}
          </Badge>
          <Button onClick={() => setShowCreateDialog(true)}>
            <PlusIcon className="w-4 h-4 mr-2" />
            Create Widget
          </Button>
        </div>
      </div>

      {/* Tier Info Card */}
      <Card className="bg-gradient-to-r from-gray-900/50 to-gray-800/50 border-white/10">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <div className="text-sm text-gray-500">Widgets Used</div>
                <div className="text-2xl font-bold text-white">
                  {widgets.length} / {tierInfo.limits.max_widgets}
                </div>
              </div>
              <Separator orientation="vertical" className="h-12 bg-white/10" />
              <div>
                <div className="text-sm text-gray-500">Domains Whitelisted</div>
                <div className="text-2xl font-bold text-white">
                  {domains.length} / {tierInfo.limits.max_domains}
                </div>
              </div>
              <Separator orientation="vertical" className="h-12 bg-white/10" />
              <div>
                <div className="text-sm text-gray-500">Branding Level</div>
                <div className="text-lg font-semibold text-white capitalize">
                  {tierInfo.branding_level === 'none' ? 'White Label' : tierInfo.branding_level}
                </div>
              </div>
            </div>
            {!tierInfo.features.white_label && (
              <Button
                variant="outline"
                className="text-purple-400 border-purple-500/30 hover:bg-purple-500/10"
              >
                Upgrade for White Label
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultValue="widgets" className="space-y-6">
        <TabsList className="bg-gray-900/50">
          <TabsTrigger value="widgets">Widgets</TabsTrigger>
          <TabsTrigger value="domains">Domain Whitelist</TabsTrigger>
        </TabsList>

        {/* Widgets Tab */}
        <TabsContent value="widgets" className="space-y-4">
          {widgets.length === 0 ? (
            <Card className="bg-gray-900/30 border-white/5">
              <CardContent className="p-12 text-center">
                <CodeBracketIcon className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">No widgets yet</h3>
                <p className="text-gray-500 mb-4">Create your first embeddable widget</p>
                <Button onClick={() => setShowCreateDialog(true)}>
                  <PlusIcon className="w-4 h-4 mr-2" />
                  Create Widget
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {widgets.map((widget) => (
                <Card
                  key={widget.id}
                  className="bg-gray-900/30 border-white/5 hover:border-white/10 transition-all"
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-white/5">
                          {widgetTypeIcons[widget.widget_type]}
                        </div>
                        <div>
                          <CardTitle className="text-base text-white">{widget.name}</CardTitle>
                          <CardDescription className="text-xs">
                            {WIDGET_TYPE_INFO[widget.widget_type].label}
                          </CardDescription>
                        </div>
                      </div>
                      <Badge
                        variant="outline"
                        className={
                          widget.is_active
                            ? 'text-green-400 border-green-500/30'
                            : 'text-gray-500 border-gray-600'
                        }
                      >
                        {widget.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Size</span>
                      <span className="text-gray-300 capitalize">{widget.widget_size}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Branding</span>
                      <Badge
                        variant="outline"
                        className={brandingBadgeColors[widget.branding_level]}
                      >
                        {widget.branding_level === 'none' ? 'None' : widget.branding_level}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Total Views</span>
                      <span className="text-gray-300">{widget.total_views.toLocaleString()}</span>
                    </div>
                    <Separator className="bg-white/5" />
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => {
                          setSelectedWidget(widget);
                          setShowEmbedCodeDialog(true);
                        }}
                      >
                        <CodeBracketIcon className="w-4 h-4 mr-1" />
                        Get Code
                      </Button>
                      <Button variant="ghost" size="sm">
                        <EyeIcon className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Domains Tab */}
        <TabsContent value="domains" className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">
              Domains must be whitelisted before they can be used with embed tokens.
            </p>
            <Button variant="outline" onClick={() => setShowDomainDialog(true)}>
              <GlobeAltIcon className="w-4 h-4 mr-2" />
              Add Domain
            </Button>
          </div>

          {domains.length === 0 ? (
            <Card className="bg-gray-900/30 border-white/5">
              <CardContent className="p-12 text-center">
                <GlobeAltIcon className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">No domains whitelisted</h3>
                <p className="text-gray-500 mb-4">
                  Add domains where your widgets will be embedded
                </p>
                <Button onClick={() => setShowDomainDialog(true)}>
                  <PlusIcon className="w-4 h-4 mr-2" />
                  Add Domain
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {domains.map((domain) => (
                <Card key={domain.id} className="bg-gray-900/30 border-white/5">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <GlobeAltIcon className="w-5 h-5 text-gray-500" />
                        <div>
                          <div className="font-mono text-white">{domain.domain_pattern}</div>
                          {domain.description && (
                            <div className="text-sm text-gray-500">{domain.description}</div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {domain.is_verified ? (
                          <Badge variant="outline" className="text-green-400 border-green-500/30">
                            <CheckIcon className="w-3 h-3 mr-1" />
                            Verified
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-yellow-400 border-yellow-500/30">
                            Pending
                          </Badge>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Create Widget Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="bg-gray-900 border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white">Create Embed Widget</DialogTitle>
            <DialogDescription>
              Create a new embeddable widget. Your branding level ({tierInfo.branding_level}) will
              be applied automatically.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm text-gray-400">Widget Name</label>
              <Input
                placeholder="e.g., Client Dashboard Signal Health"
                value={newWidget.name}
                onChange={(e) => setNewWidget({ ...newWidget, name: e.target.value })}
                className="bg-gray-800 border-white/10"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-400">Description (optional)</label>
              <Input
                placeholder="Brief description of where this widget will be used"
                value={newWidget.description}
                onChange={(e) => setNewWidget({ ...newWidget, description: e.target.value })}
                className="bg-gray-800 border-white/10"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-400">Widget Type</label>
              <Select
                value={newWidget.widget_type}
                onValueChange={(value: WidgetType) =>
                  setNewWidget({ ...newWidget, widget_type: value })
                }
              >
                <SelectTrigger className="bg-gray-800 border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-white/10">
                  {Object.entries(WIDGET_TYPE_INFO).map(([type, info]) => (
                    <SelectItem key={type} value={type}>
                      <div className="flex items-center gap-2">
                        {widgetTypeIcons[type as WidgetType]}
                        <span>{info.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500">
                {WIDGET_TYPE_INFO[newWidget.widget_type].description}
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-400">Widget Size</label>
              <Select
                value={newWidget.widget_size}
                onValueChange={(value: WidgetSize) =>
                  setNewWidget({ ...newWidget, widget_size: value })
                }
              >
                <SelectTrigger className="bg-gray-800 border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-white/10">
                  <SelectItem value="badge">Badge (120x40)</SelectItem>
                  <SelectItem value="compact">Compact (200x100)</SelectItem>
                  <SelectItem value="standard">Standard (300x200)</SelectItem>
                  <SelectItem value="large">Large (400x300)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateWidget} disabled={!newWidget.name}>
              Create Widget
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Domain Dialog */}
      <Dialog open={showDomainDialog} onOpenChange={setShowDomainDialog}>
        <DialogContent className="bg-gray-900 border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white">Add Domain to Whitelist</DialogTitle>
            <DialogDescription>
              Add a domain where your widgets will be embedded. Supports wildcards like
              *.example.com
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm text-gray-400">Domain Pattern</label>
              <Input
                placeholder="e.g., dashboard.example.com or *.example.com"
                value={newDomain.domain_pattern}
                onChange={(e) => setNewDomain({ ...newDomain, domain_pattern: e.target.value })}
                className="bg-gray-800 border-white/10 font-mono"
              />
              <p className="text-xs text-gray-500">Use *.domain.com to allow all subdomains</p>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-400">Description (optional)</label>
              <Input
                placeholder="e.g., Client reporting portal"
                value={newDomain.description}
                onChange={(e) => setNewDomain({ ...newDomain, description: e.target.value })}
                className="bg-gray-800 border-white/10"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowDomainDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddDomain} disabled={!newDomain.domain_pattern}>
              Add Domain
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Embed Code Dialog */}
      <Dialog open={showEmbedCodeDialog} onOpenChange={setShowEmbedCodeDialog}>
        <DialogContent className="bg-gray-900 border-white/10 max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-white">Embed Code</DialogTitle>
            <DialogDescription>
              Copy the embed code to add this widget to your site. Replace {'{YOUR_TOKEN}'} with
              your actual token.
            </DialogDescription>
          </DialogHeader>

          {selectedWidget && (
            <Tabs defaultValue="iframe" className="mt-4">
              <TabsList className="bg-gray-800">
                <TabsTrigger value="iframe">Iframe</TabsTrigger>
                <TabsTrigger value="script">Script</TabsTrigger>
              </TabsList>

              <TabsContent value="iframe" className="space-y-3">
                <div className="relative">
                  <pre className="p-4 bg-gray-800 rounded-lg text-sm text-gray-300 overflow-x-auto">
                    {generateIframeCode(selectedWidget)}
                  </pre>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={() => handleCopyCode(generateIframeCode(selectedWidget), 'iframe')}
                  >
                    {copiedCode === 'iframe' ? (
                      <CheckIcon className="w-4 h-4 text-green-400" />
                    ) : (
                      <ClipboardIcon className="w-4 h-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-gray-500">
                  Simple iframe embed. Best for basic integration.
                </p>
              </TabsContent>

              <TabsContent value="script" className="space-y-3">
                <div className="relative">
                  <pre className="p-4 bg-gray-800 rounded-lg text-sm text-gray-300 overflow-x-auto">
                    {generateScriptCode(selectedWidget)}
                  </pre>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={() => handleCopyCode(generateScriptCode(selectedWidget), 'script')}
                  >
                    {copiedCode === 'script' ? (
                      <CheckIcon className="w-4 h-4 text-green-400" />
                    ) : (
                      <ClipboardIcon className="w-4 h-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-gray-500">
                  Script embed with automatic loading. More flexible for styling.
                </p>
              </TabsContent>
            </Tabs>
          )}

          <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
            <div className="flex items-start gap-3">
              <KeyIcon className="w-5 h-5 text-yellow-400 mt-0.5" />
              <div>
                <div className="text-sm font-medium text-yellow-400">Token Required</div>
                <div className="text-xs text-yellow-400/70 mt-1">
                  Create an embed token in the Tokens section and replace {'{YOUR_TOKEN}'} with the
                  actual token value. Tokens are domain-bound for security.
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowEmbedCodeDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
