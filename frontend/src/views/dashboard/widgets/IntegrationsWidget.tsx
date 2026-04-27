/**
 * Stratum AI — Gap #6: Integration Ecosystem Widget
 * Embedded in dashboard: Connected services status + quick actions
 */
import { useNavigate } from 'react-router-dom';
import { Plug, ArrowRight, Zap, Cloud, MessageCircle, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const SERVICES = [
  { id: 'zapier', name: 'Zapier', icon: Zap, status: 'connected', events: 3 },
  { id: 'bigquery', name: 'BigQuery', icon: Cloud, status: 'connected', last_sync: '2m ago' },
  { id: 'teams', name: 'Teams', icon: MessageCircle, status: 'connected', alerts: 5 },
  { id: 'slack', name: 'Slack', icon: MessageCircle, status: 'disconnected', alerts: 0 },
  { id: 'snowflake', name: 'Snowflake', icon: Cloud, status: 'paused', alerts: 0 },
  { id: 'hubspot', name: 'HubSpot', icon: Plug, status: 'connected', last_sync: '1h ago' },
];

export function IntegrationsWidget() {
  const navigate = useNavigate();
  const connected = SERVICES.filter((s) => s.status === 'connected').length;

  return (
    <div className="dashboard-card h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-blue-500 flex items-center justify-center">
            <Plug className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Integrations</h3>
            <p className="text-xs text-muted-foreground">{connected}/{SERVICES.length} connected</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/integration-hub')}
          className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
        >
          Hub <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* Services Grid */}
      <div className="flex-1 overflow-auto">
        <div className="grid grid-cols-2 gap-2">
          {SERVICES.map((service) => {
            const Icon = service.icon;
            return (
              <div
                key={service.id}
                className={cn(
                  'bg-white/[0.02] border border-white/[0.04] rounded-lg p-2.5 flex items-start gap-2 transition-colors',
                  service.status === 'connected' ? 'hover:bg-white/[0.04]' : 'opacity-60'
                )}
              >
                <div className={cn(
                  'w-7 h-7 rounded-md flex items-center justify-center shrink-0',
                  service.status === 'connected' ? 'bg-emerald-500/15' :
                  service.status === 'paused' ? 'bg-yellow-500/15' :
                  'bg-red-500/10'
                )}>
                  <Icon className={cn(
                    'w-3.5 h-3.5',
                    service.status === 'connected' ? 'text-emerald-400' :
                    service.status === 'paused' ? 'text-yellow-400' :
                    'text-red-400'
                  )} />
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-medium text-foreground truncate">{service.name}</div>
                  <div className="flex items-center gap-1 mt-0.5">
                    {service.status === 'connected' ? (
                      <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                    ) : (
                      <XCircle className="w-2.5 h-2.5 text-red-400/60" />
                    )}
                    <span className={cn(
                      'text-[10px]',
                      service.status === 'connected' ? 'text-emerald-400' :
                      service.status === 'paused' ? 'text-yellow-400' :
                      'text-red-400/60'
                    )}>
                      {service.status}
                    </span>
                  </div>
                  {service.last_sync && (
                    <div className="text-[10px] text-muted-foreground mt-0.5">Synced {service.last_sync}</div>
                  )}
                  {service.events && (
                    <div className="text-[10px] text-muted-foreground mt-0.5">{service.events} webhooks</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2 mt-3 pt-3 border-t border-white/[0.04]">
        <button
          onClick={() => navigate('/integration-hub')}
          className="flex-1 text-xs text-center py-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-colors"
        >
          + Add Integration
        </button>
        <button
          onClick={() => navigate('/integration-hub')}
          className="flex-1 text-xs text-center py-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] text-muted-foreground hover:text-foreground transition-colors"
        >
          Sync Now
        </button>
      </div>
    </div>
  );
}
