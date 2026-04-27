/**
 * Stratum AI — Gap #3: AI Intelligence Widget
 * Embedded in dashboard: NLQ quick ask + predictions + anomaly alerts
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, MessageSquare, TrendingUp, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const SUGGESTIONS = [
  'Top campaigns by ROAS',
  'Compare Meta vs Google',
  'Underperforming campaigns',
  'Spend trend this month',
];

export function AIInsightsWidget() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'ask' | 'predict'>('ask');

  const getToken = () => sessionStorage.getItem('access_token') || '';
  const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';

  const askQuestion = async () => {
    const token = getToken();
    if (!question.trim() || !token) return;
    setIsAsking(true);
    try {
      const res = await fetch(`${API_URL}/analytics/insights/nlq`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (data.success) setResult(data.data);
    } catch { /* ignore */ }
    setIsAsking(false);
  };

  return (
    <div className="dashboard-card h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">AI Intelligence</h3>
            <p className="text-xs text-muted-foreground">Ask questions, get predictions</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/ai-insights')}
          className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
        >
          Full View <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-3 bg-white/[0.03] rounded-lg p-0.5">
        {[
          { id: 'ask', label: 'Ask', icon: MessageSquare },
          { id: 'predict', label: 'Predict', icon: TrendingUp },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium rounded-md transition-all',
              activeTab === t.id ? 'bg-white/[0.08] text-foreground' : 'text-muted-foreground hover:text-foreground/70'
            )}
          >
            <t.icon className="w-3.5 h-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'ask' && (
        <div className="flex-1 flex flex-col">
          {/* Input */}
          <div className="flex gap-2 mb-3">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && askQuestion()}
              placeholder="Ask about your data..."
              className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40"
            />
            <button
              onClick={askQuestion}
              disabled={isAsking || !question.trim()}
              className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {isAsking ? '...' : 'Ask'}
            </button>
          </div>

          {/* Suggestions */}
          {!result && (
            <div className="flex flex-wrap gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => { setQuestion(s); }}
                  className="text-xs bg-white/[0.03] hover:bg-white/[0.08] text-muted-foreground hover:text-foreground px-2.5 py-1 rounded-full transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="flex-1 overflow-auto space-y-2">
              <div className="text-xs text-muted-foreground flex items-center justify-between">
                <span>{result.result_count} results · {result.execution_time_ms}ms</span>
                <button onClick={() => setResult(null)} className="text-primary hover:underline">Clear</button>
              </div>
              {result.results.slice(0, 5).map((row: any, i: number) => (
                <div key={i} className="bg-white/[0.02] rounded-lg p-2 text-xs">
                  {Object.entries(row).slice(0, 4).map(([k, v]) => (
                    <span key={k} className="inline-flex items-center gap-1 mr-3">
                      <span className="text-muted-foreground">{k}:</span>
                      <span className="text-foreground font-medium">{String(v ?? '-')}</span>
                    </span>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'predict' && (
        <PredictWidget API_URL={API_URL} getToken={getToken} />
      )}
    </div>
  );
}

function PredictWidget({ API_URL, getToken }: { API_URL: string; getToken: () => string }) {
  const [campaignId, setCampaignId] = useState('');
  const [days] = useState(7);
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState<any>(null);

  const predict = async () => {
    const token = getToken();
    if (!token || !campaignId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/analytics/insights/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ campaign_id: parseInt(campaignId), days_ahead: days }),
      });
      const data = await res.json();
      if (data.success) setPrediction(data.data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex gap-2 mb-3">
        <input
          value={campaignId}
          onChange={(e) => setCampaignId(e.target.value)}
          placeholder="Campaign ID"
          className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40"
        />
        <button
          onClick={predict}
          disabled={loading || !campaignId}
          className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? '...' : 'Forecast'}
        </button>
      </div>

      {prediction && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-white/[0.03] rounded-lg p-2 text-center">
              <div className="text-lg font-bold text-emerald-400">{prediction.predicted_roas?.toFixed(1)}x</div>
              <div className="text-[10px] text-muted-foreground">ROAS</div>
            </div>
            <div className="bg-white/[0.03] rounded-lg p-2 text-center">
              <div className="text-lg font-bold text-sky-400">${(prediction.predicted_revenue / 1000).toFixed(1)}k</div>
              <div className="text-[10px] text-muted-foreground">Revenue</div>
            </div>
          </div>
          <div className={cn(
            'text-xs px-2 py-1 rounded-full text-center font-medium',
            prediction.trend === 'improving' ? 'bg-emerald-500/10 text-emerald-400' :
            prediction.trend === 'declining' ? 'bg-red-500/10 text-red-400' :
            'bg-yellow-500/10 text-yellow-400'
          )}>
            {prediction.trend} — {prediction.recommendation?.slice(0, 60)}...
          </div>
          <button
            onClick={() => setPrediction(null)}
            className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Reset
          </button>
        </div>
      )}

      {!prediction && (
        <div className="flex-1 flex flex-col items-center justify-center text-center text-muted-foreground/50">
          <TrendingUp className="w-8 h-8 mb-2 opacity-30" />
          <p className="text-xs">Enter a campaign ID to forecast performance</p>
        </div>
      )}
    </div>
  );
}
