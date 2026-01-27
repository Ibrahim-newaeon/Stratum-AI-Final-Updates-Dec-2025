import * as React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Dialog, DialogContent } from './dialog';
import { cn } from '@/lib/utils';
import {
  Activity,
  ArrowRight,
  BarChart3,
  Bell,
  Brain,
  Command,
  Database,
  FileText,
  FlaskConical,
  GitBranch,
  Hash,
  Layers,
  LayoutDashboard,
  LineChart,
  Network,
  PieChart,
  Search,
  Settings,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Workflow,
  Zap,
} from 'lucide-react';

interface CommandItem {
  id: string;
  title: string;
  description?: string;
  icon: React.ReactNode;
  category: string;
  action: () => void;
  keywords?: string[];
  shortcut?: string;
}

interface CommandPaletteProps {
  tenantId?: string;
}

export function CommandPalette({ tenantId }: CommandPaletteProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listRef = React.useRef<HTMLDivElement>(null);

  // Determine base path based on context
  const basePath = tenantId ? `/app/${tenantId}` : '/dashboard';

  // Command items organized by category
  const commands: CommandItem[] = React.useMemo(
    () => [
      // Navigation
      {
        id: 'dashboard',
        title: 'Go to Dashboard',
        description: 'Main overview dashboard',
        icon: <LayoutDashboard className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate(`${basePath}/overview`),
        keywords: ['home', 'main', 'overview'],
        shortcut: 'G D',
      },
      {
        id: 'campaigns',
        title: 'Go to Campaigns',
        description: 'Manage your campaigns',
        icon: <Target className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate(`${basePath}/campaigns`),
        keywords: ['ads', 'advertising'],
        shortcut: 'G C',
      },
      {
        id: 'cdp',
        title: 'Go to CDP',
        description: 'Customer Data Platform',
        icon: <Database className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate('/dashboard/cdp'),
        keywords: ['customer', 'data', 'profiles'],
        shortcut: 'G P',
      },
      {
        id: 'segments',
        title: 'Go to Segments',
        description: 'CDP audience segments',
        icon: <Users className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate('/dashboard/cdp/segments'),
        keywords: ['audience', 'targeting'],
      },
      {
        id: 'events',
        title: 'Go to Events',
        description: 'CDP event tracking',
        icon: <Activity className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate('/dashboard/cdp/events'),
        keywords: ['tracking', 'analytics'],
      },
      {
        id: 'identity',
        title: 'Go to Identity Graph',
        description: 'Customer identity resolution',
        icon: <Network className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate('/dashboard/cdp/identity'),
        keywords: ['graph', 'resolution', 'merge'],
      },
      {
        id: 'audience-sync',
        title: 'Go to Audience Sync',
        description: 'Sync to ad platforms',
        icon: <GitBranch className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate('/dashboard/cdp/audience-sync'),
        keywords: ['meta', 'google', 'tiktok', 'snapchat'],
      },
      {
        id: 'rfm',
        title: 'Go to RFM Analysis',
        description: 'Customer segmentation',
        icon: <PieChart className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate('/dashboard/cdp/rfm'),
        keywords: ['recency', 'frequency', 'monetary'],
      },
      {
        id: 'benchmarks',
        title: 'Go to Benchmarks',
        description: 'Industry benchmarks',
        icon: <BarChart3 className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate(`${basePath}/benchmarks`),
        keywords: ['compare', 'industry'],
      },
      {
        id: 'settings',
        title: 'Go to Settings',
        description: 'Account settings',
        icon: <Settings className="h-4 w-4" />,
        category: 'Navigation',
        action: () => navigate(`${basePath}/settings`),
        keywords: ['preferences', 'account'],
        shortcut: 'G S',
      },

      // AI Features
      {
        id: 'predictions',
        title: 'AI Predictions',
        description: 'LTV and churn predictions',
        icon: <Brain className="h-4 w-4" />,
        category: 'AI Features',
        action: () => navigate(`${basePath}/predictions`),
        keywords: ['ltv', 'churn', 'forecast'],
      },
      {
        id: 'ab-testing',
        title: 'A/B Testing',
        description: 'Bayesian experiment analysis',
        icon: <FlaskConical className="h-4 w-4" />,
        category: 'AI Features',
        action: () => navigate(`${basePath}/ab-testing`),
        keywords: ['experiment', 'bayesian', 'test'],
      },
      {
        id: 'explainability',
        title: 'Model Explainability',
        description: 'SHAP feature importance',
        icon: <Sparkles className="h-4 w-4" />,
        category: 'AI Features',
        action: () => navigate(`${basePath}/explainability`),
        keywords: ['shap', 'lime', 'explain'],
      },
      {
        id: 'churn',
        title: 'Predictive Churn',
        description: 'Churn risk analysis',
        icon: <TrendingUp className="h-4 w-4" />,
        category: 'AI Features',
        action: () => navigate('/dashboard/cdp/predictive-churn'),
        keywords: ['risk', 'retention'],
      },

      // Trust Engine
      {
        id: 'trust',
        title: 'Trust Overview',
        description: 'Signal health & trust gates',
        icon: <Shield className="h-4 w-4" />,
        category: 'Trust Engine',
        action: () => navigate(`${basePath}/trust`),
        keywords: ['signal', 'health', 'gate'],
      },
      {
        id: 'signal-hub',
        title: 'Signal Hub',
        description: 'All signals in one place',
        icon: <Zap className="h-4 w-4" />,
        category: 'Trust Engine',
        action: () => navigate(`${basePath}/signal-hub`),
        keywords: ['data', 'quality'],
      },
      {
        id: 'rules',
        title: 'Automation Rules',
        description: 'Autopilot rules engine',
        icon: <Workflow className="h-4 w-4" />,
        category: 'Trust Engine',
        action: () => navigate(`${basePath}/rules`),
        keywords: ['automation', 'autopilot'],
      },

      // Analytics
      {
        id: 'reporting',
        title: 'Reporting',
        description: 'Custom reports & analytics',
        icon: <FileText className="h-4 w-4" />,
        category: 'Analytics',
        action: () => navigate(`${basePath}/reporting`),
        keywords: ['report', 'export'],
      },
      {
        id: 'attribution',
        title: 'Attribution',
        description: 'Multi-touch attribution',
        icon: <LineChart className="h-4 w-4" />,
        category: 'Analytics',
        action: () => navigate(`${basePath}/attribution`),
        keywords: ['mta', 'touchpoint'],
      },
      {
        id: 'funnels',
        title: 'Conversion Funnels',
        description: 'Funnel analysis',
        icon: <Layers className="h-4 w-4" />,
        category: 'Analytics',
        action: () => navigate('/dashboard/cdp/funnels'),
        keywords: ['conversion', 'journey'],
      },

      // Quick Actions
      {
        id: 'new-segment',
        title: 'Create New Segment',
        description: 'Build a new audience segment',
        icon: <Hash className="h-4 w-4" />,
        category: 'Quick Actions',
        action: () => navigate('/dashboard/cdp/segments?action=create'),
        keywords: ['add', 'audience'],
      },
      {
        id: 'new-campaign',
        title: 'Create Campaign',
        description: 'Launch a new campaign',
        icon: <Target className="h-4 w-4" />,
        category: 'Quick Actions',
        action: () => navigate(`${basePath}/campaigns/new`),
        keywords: ['launch', 'ad'],
      },
    ],
    [basePath, navigate]
  );

  // Filter commands based on search
  const filteredCommands = React.useMemo(() => {
    if (!search) return commands;
    const query = search.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.title.toLowerCase().includes(query) ||
        cmd.description?.toLowerCase().includes(query) ||
        cmd.keywords?.some((k) => k.includes(query)) ||
        cmd.category.toLowerCase().includes(query)
    );
  }, [commands, search]);

  // Group by category
  const groupedCommands = React.useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    filteredCommands.forEach((cmd) => {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  // Keyboard shortcut to open
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Focus input when open
  React.useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 0);
      setSearch('');
      setSelectedIndex(0);
    }
  }, [open]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredCommands[selectedIndex]) {
        filteredCommands[selectedIndex].action();
        setOpen(false);
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  // Scroll selected item into view
  React.useEffect(() => {
    const selected = listRef.current?.querySelector('[data-selected="true"]');
    selected?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  let currentIndex = -1;

  return (
    <>
      {/* Trigger button - can be placed in header */}
      <button
        onClick={() => setOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground bg-muted/50 hover:bg-muted rounded-lg border border-border/50 transition-colors"
      >
        <Search className="h-4 w-4" />
        <span>Search...</span>
        <kbd className="ml-2 px-1.5 py-0.5 text-[10px] font-medium bg-background border rounded">
          <Command className="h-3 w-3 inline" />K
        </kbd>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="overflow-hidden p-0 max-w-2xl top-[20%] translate-y-0">
          <div className="flex flex-col">
            {/* Search input */}
            <div className="flex items-center border-b px-4 py-3">
              <Search className="h-5 w-5 text-muted-foreground mr-3" />
              <input
                ref={inputRef}
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setSelectedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Type a command or search..."
                className="flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground"
              />
              <kbd className="px-2 py-1 text-xs text-muted-foreground bg-muted rounded">ESC</kbd>
            </div>

            {/* Command list */}
            <div ref={listRef} className="max-h-[400px] overflow-y-auto p-2">
              {Object.entries(groupedCommands).length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">No results found.</div>
              ) : (
                Object.entries(groupedCommands).map(([category, items]) => (
                  <div key={category} className="mb-2">
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {category}
                    </div>
                    {items.map((cmd) => {
                      currentIndex++;
                      const isSelected = currentIndex === selectedIndex;
                      const itemIndex = currentIndex;
                      return (
                        <button
                          key={cmd.id}
                          data-selected={isSelected}
                          onClick={() => {
                            cmd.action();
                            setOpen(false);
                          }}
                          onMouseEnter={() => setSelectedIndex(itemIndex)}
                          className={cn(
                            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
                            isSelected ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
                          )}
                        >
                          <div
                            className={cn(
                              'flex items-center justify-center w-8 h-8 rounded-md',
                              isSelected ? 'bg-primary-foreground/20' : 'bg-muted'
                            )}
                          >
                            {cmd.icon}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{cmd.title}</div>
                            {cmd.description && (
                              <div
                                className={cn(
                                  'text-sm truncate',
                                  isSelected
                                    ? 'text-primary-foreground/70'
                                    : 'text-muted-foreground'
                                )}
                              >
                                {cmd.description}
                              </div>
                            )}
                          </div>
                          {cmd.shortcut && (
                            <kbd
                              className={cn(
                                'px-2 py-0.5 text-xs rounded',
                                isSelected
                                  ? 'bg-primary-foreground/20 text-primary-foreground'
                                  : 'bg-muted text-muted-foreground'
                              )}
                            >
                              {cmd.shortcut}
                            </kbd>
                          )}
                          <ArrowRight
                            className={cn(
                              'h-4 w-4 opacity-0 transition-opacity',
                              isSelected && 'opacity-100'
                            )}
                          />
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between border-t px-4 py-2 text-xs text-muted-foreground">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">↑</kbd>
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">↓</kbd>
                  Navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">↵</kbd>
                  Select
                </span>
              </div>
              <span className="text-muted-foreground/70">Stratum AI Command Palette</span>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default CommandPalette;
