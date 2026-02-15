/**
 * Shared Left Panel for Login & Signup pages
 * Branding, hero text, dashboard preview card, footer
 */

import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

const CHART_BARS = [
  { day: 'MON', height: '45%', value: '$14.2k', highlight: false },
  { day: 'TUE', height: '65%', value: '$18.1k', highlight: false },
  { day: 'WED', height: '85%', value: '$24.9k', highlight: true },
  { day: 'THU', height: '50%', value: '$15.4k', highlight: false },
  { day: 'FRI', height: '75%', value: '$21.8k', highlight: false },
];

interface AuthLeftPanelProps {
  className?: string;
}

export default function AuthLeftPanel({ className }: AuthLeftPanelProps) {
  return (
    <section
      className={cn(
        'w-7/12 p-12 flex-col justify-between relative border-r border-white/5',
        className
      )}
    >
      {/* Top: Logo + Status */}
      <div className="space-y-8">
        <div className="flex items-center space-x-3">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 bg-[#00c7be] rounded-lg flex items-center justify-center shadow-lg shadow-[#00c7be]/20">
              <span className="font-display font-bold text-white text-xl uppercase">S</span>
            </div>
            <div>
              <h1 className="font-display font-bold text-lg leading-tight tracking-tight text-white">
                Stratum AI
              </h1>
              <p className="text-[10px] tracking-widest text-[#00c7be] font-bold uppercase">
                Revenue OS
              </p>
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#00c7be]/5 border border-[#00c7be]/20 rounded-full text-[11px] font-bold uppercase tracking-wider text-[#00c7be]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#22C55E] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#22C55E]" />
            </span>
            Platform Status: <span className="text-white ml-1">Optimized</span>
          </div>
        </div>
      </div>

      {/* Center: Hero + Dashboard Preview */}
      <div className="max-w-2xl">
        <h2 className="text-5xl font-display font-bold leading-tight mb-8 text-white">
          Experience the{' '}
          <span className="text-[#00c7be]">Next Generation</span> of Revenue
          Intelligence
        </h2>

        {/* Dashboard Preview Card */}
        <div className="auth-glass-card p-8 rounded-[2rem] relative overflow-hidden group">
          <div className="flex items-center justify-between mb-10">
            <div>
              <h3 className="font-display font-bold text-lg text-white">
                Revenue Lift Dashboard
              </h3>
              <p className="text-xs text-white/40">
                Real-time AI autonomous performance
              </p>
            </div>
            <div className="px-3 py-1 bg-[#00c7be]/20 rounded text-[10px] font-bold text-[#00c7be] uppercase border border-[#00c7be]/20">
              Live Sync
            </div>
          </div>

          {/* Bar Chart */}
          <div
            className="flex items-end justify-between h-48 gap-4 px-4"
            role="img"
            aria-label="Revenue bar chart showing daily performance from Monday to Friday"
          >
            {CHART_BARS.map((bar, i) => (
              <div
                key={bar.day}
                className="group/bar relative flex-1 flex flex-col items-center justify-end h-full"
                role="presentation"
                aria-label={`${bar.day}: ${bar.value}`}
              >
                {/* Tooltip */}
                <div className="absolute -top-10 bg-[#00c7be] text-[#0b1215] text-[11px] font-bold py-1 px-2 rounded opacity-0 group-hover/bar:opacity-100 transition-all pointer-events-none z-20 shadow-xl">
                  {bar.value}
                </div>
                {/* Bar */}
                <div
                  className={cn(
                    'auth-bar-grow w-full rounded-t-lg transition-all duration-500 border-x border-t',
                    bar.highlight
                      ? 'bg-[#00c7be]/60 border-white/20 auth-chart-glow group-hover/bar:bg-[#00c7be]/80'
                      : 'bg-white/[0.06] border-white/5 group-hover/bar:bg-[#00c7be]/30'
                  )}
                  style={{
                    height: bar.height,
                    animationDelay: `${i * 0.15}s`,
                  }}
                />
                <div
                  className={cn(
                    'mt-3 text-[10px] font-bold',
                    bar.highlight ? 'text-[#00c7be]' : 'text-white/30'
                  )}
                >
                  {bar.day}
                </div>
              </div>
            ))}
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-3 gap-6 mt-10 pt-8 border-t border-white/10">
            <div>
              <p className="text-[10px] text-white/30 uppercase font-bold tracking-widest mb-1">
                ROAS LIFT
              </p>
              <p className="text-xl font-display font-bold text-[#00c7be]">
                +34.2%
              </p>
            </div>
            <div>
              <p className="text-[10px] text-white/30 uppercase font-bold tracking-widest mb-1">
                CAC REDUCTION
              </p>
              <p className="text-xl font-display font-bold text-white">
                -18.4%
              </p>
            </div>
            <div>
              <p className="text-[10px] text-white/30 uppercase font-bold tracking-widest mb-1">
                AI PRECISION
              </p>
              <p className="text-xl font-display font-bold text-white">
                99.2%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center gap-8 text-[11px] text-white/30 font-medium uppercase tracking-widest">
        <span>&copy; 2026 Stratum AI</span>
        <div className="flex gap-6">
          <a
            className="hover:text-[#00c7be] transition-colors"
            href="/security"
          >
            Security
          </a>
          <a
            className="hover:text-[#00c7be] transition-colors"
            href="/privacy"
          >
            Privacy
          </a>
        </div>
      </div>
    </section>
  );
}
