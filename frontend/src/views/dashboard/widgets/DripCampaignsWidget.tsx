/**
 * Stratum AI — Drip Campaigns Dashboard Widget
 */
import { useNavigate } from 'react-router-dom';
import { Workflow, Plus, Play, Pause, Users, Mail, ArrowRight, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

const MOCK_SEQUENCES = [
  { id: 'drip_001', name: 'Welcome Series', trigger: 'user_subscribed', status: 'active', entries: 234, open_rate: 68, steps: 4 },
  { id: 'drip_002', name: 'Cart Recovery', trigger: 'cart_abandoned', status: 'active', entries: 89, open_rate: 45, steps: 3 },
  { id: 'drip_003', name: 'Re-engagement', trigger: 'days_since_login', status: 'paused', entries: 12, open_rate: 32, steps: 3 },
  { id: 'drip_004', name: 'ROAS Alert', trigger: 'campaign_roas_drop', status: 'draft', entries: 0, open_rate: 0, steps: 3 },
];

export function DripCampaignsWidget() {
  const navigate = useNavigate();

  return (
    <div className="dashboard-card h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
            <Workflow className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Drip Campaigns</h3>
            <p className="text-xs text-muted-foreground">Automated sequences</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/drip-campaigns')}
            className="text-xs bg-primary/15 text-primary px-3 py-1.5 rounded-lg hover:bg-primary/25 transition-colors flex items-center gap-1"
          >
            <Plus className="w-3 h-3" /> New
          </button>
          <button
            onClick={() => navigate('/drip-campaigns')}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            View All <ArrowRight className="w-3 h-3 inline" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto space-y-2">
        {MOCK_SEQUENCES.map((seq) => (
          <button
            key={seq.id}
            onClick={() => navigate('/drip-campaigns')}
            className="w-full text-left flex items-center gap-3 bg-foreground/[0.02] hover:bg-foreground/[0.05] border border-foreground/[0.04] rounded-lg p-3 transition-colors group"
          >
            <div className={cn(
              'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
              seq.status === 'active' ? 'bg-emerald-500/15' :
              seq.status === 'paused' ? 'bg-yellow-500/15' :
              'bg-gray-500/15'
            )}>
              {seq.status === 'active' ? <Play className="w-3.5 h-3.5 text-emerald-400" /> :
               seq.status === 'paused' ? <Pause className="w-3.5 h-3.5 text-yellow-400" /> :
               <Zap className="w-3.5 h-3.5 text-gray-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{seq.name}</div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                  <Users className="w-2.5 h-2.5" /> {seq.entries}
                </span>
                <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                  <Mail className="w-2.5 h-2.5" /> {seq.steps} steps
                </span>
                {seq.status === 'active' && (
                  <span className="text-[10px] text-emerald-400">{seq.open_rate}% open</span>
                )}
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-muted-foreground/60 transition-colors" />
          </button>
        ))}
      </div>

      {/* Pre-built Templates */}
      <div className="mt-3 pt-3 border-t border-foreground/[0.04]">
        <div className="text-[10px] text-muted-foreground uppercase mb-2">Quick Start Templates</div>
        <div className="flex gap-1.5">
          {['Welcome', 'Cart Recovery', 'Re-engage'].map((t) => (
            <button
              key={t}
              onClick={() => navigate('/drip-campaigns')}
              className="text-[10px] bg-foreground/[0.03] hover:bg-foreground/[0.08] text-muted-foreground hover:text-foreground px-2.5 py-1 rounded-full transition-colors"
            >
              {t}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
