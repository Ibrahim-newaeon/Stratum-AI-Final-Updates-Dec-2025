import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, PlayIcon } from '@heroicons/react/24/outline';

export function Hero() {
  const navigate = useNavigate();

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-surface-primary">
      {/* Background gradient effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 w-[800px] h-[800px] rounded-full bg-gradient-to-br from-stratum-500/20 to-transparent blur-3xl" />
        <div className="absolute -bottom-1/2 -right-1/4 w-[600px] h-[600px] rounded-full bg-gradient-to-tl from-cyan-500/15 to-transparent blur-3xl" />
        <div className="absolute top-1/4 right-1/3 w-[400px] h-[400px] rounded-full bg-stratum-500/5 blur-2xl" />
      </div>

      {/* Grid pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '64px 64px'
        }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-32 text-center">
        {/* Badge */}
        <div className="motion-enter inline-flex items-center gap-2 px-4 py-2 rounded-full bg-stratum-500/10 border border-stratum-500/20 mb-8">
          <span className="w-2 h-2 rounded-full bg-stratum-500 animate-pulse" />
          <span className="text-meta text-stratum-400">AI-Powered Marketing Intelligence</span>
        </div>

        {/* Main headline */}
        <h1 className="motion-enter text-h1 md:text-[48px] lg:text-[56px] font-bold text-white leading-tight mb-6" style={{ animationDelay: '0.1s' }}>
          A premium{' '}
          <span className="bg-gradient-stratum bg-clip-text text-transparent">
            AI command center
          </span>
        </h1>

        {/* Subheadline */}
        <p className="motion-enter text-h3 md:text-[24px] text-text-secondary mb-4" style={{ animationDelay: '0.2s' }}>
          Calm. Powerful. Unforgettable.
        </p>

        {/* Description */}
        <p className="motion-enter max-w-2xl mx-auto text-body text-text-muted mb-12" style={{ animationDelay: '0.3s' }}>
          Unify your ad operations across Meta, Google, TikTok, and Snapchat.
          Trust your data. Automate with confidence. Scale what works.
        </p>

        {/* CTA Buttons */}
        <div className="motion-enter flex flex-col sm:flex-row items-center justify-center gap-4 mb-16" style={{ animationDelay: '0.4s' }}>
          <button
            onClick={() => navigate('/signup')}
            className="group flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-stratum text-white font-semibold text-body
                       shadow-glow hover:shadow-glow-lg transition-all duration-base
                       hover:scale-[1.02] active:scale-[0.98]"
          >
            Get Started Free
            <ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>

          <button
            className="group flex items-center gap-2 px-8 py-4 rounded-xl border border-white/10 text-white font-medium text-body
                       hover:bg-white/5 hover:border-white/20 transition-all duration-base"
          >
            <PlayIcon className="w-5 h-5" />
            Watch Demo
          </button>
        </div>

        {/* Dashboard Preview */}
        <div className="motion-enter relative max-w-5xl mx-auto" style={{ animationDelay: '0.5s' }}>
          <div className="relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
            {/* Glow effect behind the preview */}
            <div className="absolute -inset-4 bg-gradient-stratum opacity-20 blur-2xl" />

            {/* Dashboard mockup placeholder */}
            <div className="relative bg-surface-secondary rounded-2xl p-1">
              <div className="bg-surface-primary rounded-xl overflow-hidden">
                {/* Browser chrome */}
                <div className="flex items-center gap-2 px-4 py-3 bg-surface-tertiary border-b border-white/5">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/60" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                    <div className="w-3 h-3 rounded-full bg-green-500/60" />
                  </div>
                  <div className="flex-1 flex justify-center">
                    <div className="px-4 py-1 rounded-md bg-surface-primary text-meta text-text-muted">
                      app.stratum.ai
                    </div>
                  </div>
                </div>

                {/* Dashboard content preview */}
                <div className="p-6 space-y-4">
                  {/* KPI Strip */}
                  <div className="grid grid-cols-4 gap-4">
                    {[
                      { label: 'Total Spend', value: '$124,580', delta: '+12.4%', positive: true },
                      { label: 'Revenue', value: '$892,340', delta: '+28.7%', positive: true },
                      { label: 'Blended ROAS', value: '7.16x', delta: '+0.42', positive: true },
                      { label: 'Signal Health', value: '94', delta: 'Reliable', positive: true },
                    ].map((kpi, i) => (
                      <div key={i} className="bg-surface-secondary rounded-lg p-4 border border-white/5">
                        <div className="text-meta text-text-muted mb-1">{kpi.label}</div>
                        <div className="text-h3 text-white font-semibold">{kpi.value}</div>
                        <div className={`text-micro ${kpi.positive ? 'text-success' : 'text-danger'}`}>
                          {kpi.delta}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Chart placeholder */}
                  <div className="bg-surface-secondary rounded-lg p-4 border border-white/5 h-48 flex items-end gap-1">
                    {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88].map((h, i) => (
                      <div
                        key={i}
                        className="flex-1 bg-gradient-to-t from-stratum-500/40 to-stratum-500/80 rounded-t"
                        style={{ height: `${h}%` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 motion-enter" style={{ animationDelay: '0.6s' }}>
          <div className="flex flex-col items-center gap-2 text-text-muted">
            <span className="text-micro">Scroll to explore</span>
            <div className="w-6 h-10 rounded-full border border-white/20 flex items-start justify-center p-2">
              <div className="w-1 h-2 rounded-full bg-white/40 animate-bounce" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
