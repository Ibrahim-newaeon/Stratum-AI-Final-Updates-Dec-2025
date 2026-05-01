/**
 * Stratum AI — Gap #4: Advanced Analytics Widget
 * Embedded in dashboard: Funnel preview + quick stats
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, ArrowRight, TrendingDown, Users, MousePointer } from 'lucide-react';
import { cn } from '@/lib/utils';

const MOCK_FUNNEL = [
  { step: 'Impressions', count: 125000, rate: 100 },
  { step: 'Clicks', count: 8750, rate: 7.0 },
  { step: 'Conversions', count: 420, rate: 4.8 },
];

export function AnalyticsWidget() {
  const navigate = useNavigate();
  const [activeView, setActiveView] = useState<'funnel' | 'cohort'>('funnel');

  return (
    <div className="dashboard-card h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Advanced Analytics</h3>
            <p className="text-xs text-muted-foreground">Funnels & Cohorts</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/funnel-analysis')}
          className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
        >
          Explore <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* Mini Tabs */}
      <div className="flex gap-1 mb-3 bg-white/[0.03] rounded-lg p-0.5">
        {[
          { id: 'funnel', label: 'Funnel', icon: TrendingDown },
          { id: 'cohort', label: 'Cohorts', icon: Users },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveView(t.id as any)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium rounded-md transition-all',
              activeView === t.id ? 'bg-white/[0.08] text-foreground' : 'text-muted-foreground hover:text-foreground/70'
            )}
          >
            <t.icon className="w-3.5 h-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {activeView === 'funnel' && (
        <div className="flex-1 flex flex-col justify-center">
          <div className="space-y-2">
            {MOCK_FUNNEL.map((step, i) => {
              const prevCount = i > 0 ? MOCK_FUNNEL[i - 1].count : step.count;
              const dropOff = i > 0 ? (((prevCount - step.count) / prevCount) * 100).toFixed(1) : '0';
              return (
                <div key={step.step} className="relative">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs font-medium text-foreground">{step.step}</span>
                    <span className="text-xs text-muted-foreground">{step.count.toLocaleString()}</span>
                  </div>
                  <div className="h-6 bg-foreground/5 rounded-md overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-md transition-all flex items-center px-2',
                        i === 0 ? 'bg-emerald-500/40' : i === 1 ? 'bg-teal-500/40' : 'bg-primary/40'
                      )}
                      style={{ width: `${(step.count / MOCK_FUNNEL[0].count) * 100}%` }}
                    >
                      <span className="text-[10px] font-bold text-foreground/90">{step.rate}%</span>
                    </div>
                  </div>
                  {i > 0 && (
                    <div className="text-[10px] text-red-400/70 mt-0.5">↓ {dropOff}% drop-off</div>
                  )}
                </div>
              );
            })}
          </div>
          <button
            onClick={() => navigate('/funnel-analysis')}
            className="mt-3 text-xs text-primary hover:underline flex items-center gap-1 self-end"
          >
            <MousePointer className="w-3 h-3" /> Build custom funnel
          </button>
        </div>
      )}

      {activeView === 'cohort' && (
        <div className="flex-1 flex flex-col justify-center">
          <div className="text-xs text-muted-foreground mb-2">Weekly Retention Cohorts</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="text-left py-1">Cohort</th>
                  <th className="text-center py-1">Size</th>
                  <th className="text-center py-1">W0</th>
                  <th className="text-center py-1">W1</th>
                  <th className="text-center py-1">W2</th>
                  <th className="text-center py-1">W3</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { label: '2026-W14', size: 45, cells: [100, 78, 65, 52] },
                  { label: '2026-W15', size: 38, cells: [100, 82, 71, 58] },
                  { label: '2026-W16', size: 52, cells: [100, 75, 60, null] },
                ].map((row) => (
                  <tr key={row.label} className="border-t border-white/[0.04]">
                    <td className="py-1 text-foreground">{row.label}</td>
                    <td className="py-1 text-center text-muted-foreground">{row.size}</td>
                    {row.cells.map((cell, j) => (
                      <td key={j} className="py-1 text-center">
                        {cell !== null ? (
                          <span className={cn(
                            'px-1.5 py-0.5 rounded',
                            cell > 70 ? 'bg-emerald-500/15 text-emerald-400' :
                            cell > 40 ? 'bg-yellow-500/15 text-yellow-400' :
                            'bg-red-500/15 text-red-400'
                          )}>
                            {cell}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground/30">—</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            onClick={() => navigate('/cohort-analysis')}
            className="mt-2 text-xs text-primary hover:underline self-end"
          >
            Full cohort analysis →
          </button>
        </div>
      )}
    </div>
  );
}
