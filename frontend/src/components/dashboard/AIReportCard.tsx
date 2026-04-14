import { useState } from 'react';
import {
  FileText,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  X,
  Star,
  AlertTriangle,
  Lightbulb,
  Target,
  Trophy,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Sparkles,
  BarChart3,
  Globe,
  CheckCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAIReport } from '@/api/dashboard';
import type {
  ReportKPI,
  PlatformBreakdown,
  CampaignHighlight,
  ReportInsight,
} from '@/api/dashboard';

const gradeConfig = {
  A: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', ring: 'ring-emerald-200' },
  B: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', ring: 'ring-blue-200' },
  C: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', ring: 'ring-amber-200' },
  D: { color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', ring: 'ring-orange-200' },
  F: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', ring: 'ring-red-200' },
};

const insightConfig = {
  trend: { icon: TrendingUp, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  opportunity: { icon: Lightbulb, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  risk: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' },
  milestone: { icon: Trophy, color: 'text-violet-600', bg: 'bg-violet-50', border: 'border-violet-200' },
};

const severityColors = {
  info: 'text-blue-600',
  positive: 'text-emerald-600',
  warning: 'text-amber-600',
  critical: 'text-red-600',
};

function GradeBadge({ grade, label }: { grade: string; label: string }) {
  const config = gradeConfig[grade as keyof typeof gradeConfig] || gradeConfig.F;
  return (
    <div className={cn('flex items-center gap-2 px-3 py-1.5 rounded-lg border', config.bg, config.border)}>
      <span className={cn('text-xl font-display font-black', config.color)}>{grade}</span>
      <span className={cn('text-[10px] font-semibold uppercase tracking-wider', config.color)}>{label}</span>
    </div>
  );
}

function KPIGrid({ kpis }: { kpis: ReportKPI[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="rounded-lg border bg-background p-3 text-center">
          <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{kpi.label}</div>
          <div className="text-lg font-bold text-foreground mt-0.5">{kpi.formatted}</div>
          {kpi.change_pct !== 0 && (
            <div className={cn('text-[10px] font-semibold flex items-center justify-center gap-0.5 mt-0.5',
              kpi.is_good ? 'text-emerald-600' : 'text-red-500'
            )}>
              {kpi.trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : kpi.trend === 'down' ? <ArrowDownRight className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
              {Math.abs(kpi.change_pct).toFixed(1)}%
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function PlatformRow({ platform }: { platform: PlatformBreakdown }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg border bg-background">
      <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center flex-shrink-0">
        <Globe className="w-4 h-4 text-blue-500" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{platform.platform}</span>
          <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
            {platform.campaigns} campaigns
          </span>
        </div>
        <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
          <span>Spend: ${platform.spend.toLocaleString()}</span>
          <span>Revenue: ${platform.revenue.toLocaleString()}</span>
          <span className={cn('font-bold', platform.roas >= 3 ? 'text-emerald-600' : platform.roas >= 1 ? 'text-amber-600' : 'text-red-500')}>
            {platform.roas.toFixed(2)}x ROAS
          </span>
          <span>{platform.spend_share_pct.toFixed(0)}% of spend</span>
        </div>
      </div>
    </div>
  );
}

function HighlightRow({ campaign, isTop }: { campaign: CampaignHighlight; isTop: boolean }) {
  return (
    <div className={cn('flex items-start gap-3 p-3 rounded-lg border',
      isTop ? 'bg-emerald-50/30 border-emerald-200' : 'bg-amber-50/30 border-amber-200'
    )}>
      <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
        isTop ? 'bg-emerald-50 border border-emerald-200' : 'bg-amber-50 border border-amber-200'
      )}>
        {isTop ? <Star className="w-3.5 h-3.5 text-emerald-500" /> : <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground truncate">{campaign.campaign_name}</span>
          <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">{campaign.platform}</span>
          <span className={cn('text-xs font-bold', isTop ? 'text-emerald-600' : 'text-amber-600')}>
            {campaign.metric_value}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{campaign.insight}</p>
      </div>
    </div>
  );
}

function InsightCard({ insight }: { insight: ReportInsight }) {
  const config = insightConfig[insight.category] || insightConfig.trend;
  const Icon = config.icon;
  return (
    <div className={cn('flex items-start gap-2.5 p-3 rounded-lg border', config.border, config.bg + '/30')}>
      <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0', config.bg)}>
        <Icon className={cn('w-3.5 h-3.5', config.color)} />
      </div>
      <div className="min-w-0 flex-1">
        <div className={cn('text-xs font-bold', severityColors[insight.severity])}>{insight.title}</div>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{insight.narrative}</p>
      </div>
    </div>
  );
}

export function AIReportCard() {
  const { data, isLoading, error } = useAIReport();
  const [dismissed, setDismissed] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    kpi_grid: true,
    platform_breakdown: false,
    top_performers: false,
    underperformers: false,
    insights: false,
    recommendations: true,
  });

  if (dismissed || isLoading || error || !data) return null;
  if (data.total_campaigns === 0) return null;

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-50 to-violet-50 border border-blue-200 flex items-center justify-center flex-shrink-0 mt-0.5">
            <FileText className="w-5 h-5 text-blue-500" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
                {data.report_title}
              </h2>
              <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-200 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />AI-GENERATED
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.executive_summary}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <GradeBadge grade={data.health_grade} label={data.health_label} />
          <button
            onClick={() => setDismissed(true)}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="px-6 pb-4">
        <div className="flex items-center gap-6 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <BarChart3 className="w-3.5 h-3.5" />
            {data.total_campaigns} campaigns
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Globe className="w-3.5 h-3.5" />
            {data.platforms_count} platforms
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Target className="w-3.5 h-3.5" />
            {data.overall_roas.toFixed(2)}x ROAS
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <FileText className="w-3.5 h-3.5" />
            {data.period_label}
          </div>
        </div>
      </div>

      {/* Sections */}
      {data.sections.filter(s => s.section_type !== 'executive_summary').map((section) => {
        const key = section.section_type;
        const isExpanded = expandedSections[key] ?? false;
        const hasContent =
          section.kpis.length > 0 ||
          section.platforms.length > 0 ||
          section.highlights.length > 0 ||
          section.insights.length > 0 ||
          section.content.length > 0;

        if (!hasContent) return null;

        return (
          <div key={key} className="border-t">
            <button
              onClick={() => toggleSection(key)}
              className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
            >
              <span className="text-sm font-semibold text-foreground">{section.title}</span>
              {isExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
            </button>
            {isExpanded && (
              <div className="px-6 pb-4 space-y-2">
                {section.section_type === 'kpi_grid' && section.kpis.length > 0 && (
                  <KPIGrid kpis={section.kpis} />
                )}
                {section.section_type === 'platform_breakdown' && section.platforms.map((p) => (
                  <PlatformRow key={p.platform} platform={p} />
                ))}
                {section.section_type === 'top_performers' && section.highlights.map((h) => (
                  <HighlightRow key={h.campaign_id} campaign={h} isTop={true} />
                ))}
                {section.section_type === 'underperformers' && section.highlights.map((h) => (
                  <HighlightRow key={h.campaign_id} campaign={h} isTop={false} />
                ))}
                {section.section_type === 'insights' && section.insights.map((ins, i) => (
                  <InsightCard key={i} insight={ins} />
                ))}
                {section.section_type === 'recommendations' && section.content && (
                  <div className="space-y-2">
                    {section.content.split('\n').filter(Boolean).map((line, i) => (
                      <div key={i} className="flex items-start gap-2 p-2.5 rounded-lg bg-emerald-50/40 border border-emerald-200">
                        <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                        <span className="text-xs text-foreground leading-relaxed">{line.replace(/^[•\s]+/, '')}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
