import { useNavigate } from 'react-router-dom';
import { ArrowRight, Play } from 'lucide-react';

export function Hero() {
  const navigate = useNavigate();

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-background pt-20">
      {/* Grid pattern background */}
      <div className="absolute inset-0 bg-grid-pattern opacity-50" />

      {/* Subtle radial glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[#FF8C00]/5 blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-24 lg:py-32 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#FF8C00]/10 border border-[#FF8C00]/20 mb-8 animate-enter">
          <span className="w-2 h-2 rounded-full bg-[#FF8C00] animate-pulse" />
          <span className="text-meta text-[#FF8C00]">
            Your AI Partner for Ad Growth
          </span>
        </div>

        {/* Main headline */}
        <h1
          className="text-display-sm md:text-display text-text-primary leading-tight mb-6 animate-enter"
          style={{ animationDelay: '0.1s' }}
        >
          Your AI Partner for{' '}
          <span className="text-gradient-primary">Unstoppable Ad Growth</span>
        </h1>

        {/* Subheadline */}
        <p
          className="text-h2 md:text-h1 text-text-secondary mb-4 animate-enter"
          style={{ animationDelay: '0.2s' }}
        >
          We optimize together. You stay in control.
        </p>

        {/* Description */}
        <p
          className="max-w-2xl mx-auto text-body text-text-muted mb-12 animate-enter"
          style={{ animationDelay: '0.3s' }}
        >
          Stratum AI partners with your growth team to unify ad operations across
          Meta, Google, TikTok, and Snapchat. Trust your data. Automate with
          confidence. Scale what works.
        </p>

        {/* CTA Buttons */}
        <div
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16 animate-enter"
          style={{ animationDelay: '0.4s' }}
        >
          <button
            onClick={() => navigate('/signup')}
            className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-white font-semibold text-body shadow-glow hover:shadow-glow-orange hover:scale-[1.02] active:scale-[0.98] transition-transform transition-shadow duration-200"
          >
            Start Free
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
          </button>

          <button className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl border border-border bg-card text-text-primary font-medium text-body hover:bg-white/5 hover:border-border/80 transition-colors duration-200">
            <Play className="w-5 h-5 text-[#FF8C00]" />
            See How We Partner
          </button>
        </div>

        {/* Dashboard Preview */}
        <div
          className="relative max-w-5xl mx-auto animate-enter"
          style={{ animationDelay: '0.5s' }}
        >
          <div className="relative rounded-2xl overflow-hidden border border-border shadow-elevated">
            <div className="absolute -inset-4 bg-[#FF8C00]/10 opacity-30 blur-2xl pointer-events-none" />

            <div className="relative bg-card rounded-2xl p-1">
              <div className="bg-background rounded-xl overflow-hidden">
                {/* Browser chrome */}
                <div className="flex items-center gap-2 px-4 py-3 bg-card border-b border-border">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-danger/60" />
                    <div className="w-3 h-3 rounded-full bg-warning/60" />
                    <div className="w-3 h-3 rounded-full bg-success/60" />
                  </div>
                  <div className="flex-1 flex justify-center">
                    <div className="px-4 py-1 rounded-md bg-background text-meta text-text-muted">
                      app.stratum.ai
                    </div>
                  </div>
                </div>

                {/* Dashboard content preview */}
                <div className="p-6 space-y-4">
                  {/* KPI Strip */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                      {
                        label: 'Total Spend',
                        value: '$124,580',
                        delta: '+12.4%',
                        positive: true,
                      },
                      {
                        label: 'Revenue',
                        value: '$892,340',
                        delta: '+28.7%',
                        positive: true,
                      },
                      {
                        label: 'Blended ROAS',
                        value: '7.16x',
                        delta: '+0.42',
                        positive: true,
                      },
                      {
                        label: 'Signal Health',
                        value: '94',
                        delta: 'Reliable',
                        positive: true,
                      },
                    ].map((kpi, i) => (
                      <div
                        key={i}
                        className="bg-card rounded-lg p-4 border border-border"
                      >
                        <div className="text-meta text-text-muted mb-1">
                          {kpi.label}
                        </div>
                        <div className="text-h3 text-text-primary font-semibold">
                          {kpi.value}
                        </div>
                        <div
                          className={`text-micro ${kpi.positive ? 'text-success' : 'text-danger'}`}
                        >
                          {kpi.delta}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Chart placeholder */}
                  <div className="bg-card rounded-lg p-4 border border-border h-48 flex items-end gap-1">
                    {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88].map(
                      (h, i) => (
                        <div
                          key={i}
                          className="flex-1 bg-gradient-to-t from-[#FF1F6D]/40 to-[#FF8C00]/80 rounded-t"
                          style={{ height: `${h}%` }}
                        />
                      ),
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
