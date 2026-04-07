/**
 * Shared Left Panel for Login & Signup pages
 * Cyberpunk Dark theme — Trust Gauge, spectral gradient, brand metrics
 */

import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface AuthLeftPanelProps {
  className?: string;
}

export default function AuthLeftPanel({ className }: AuthLeftPanelProps) {
  return (
    <section
      className={cn(
        'w-7/12 bg-[#050B18] relative overflow-hidden items-center justify-center border-r border-white/5',
        className
      )}
      style={{
        backgroundImage:
          'radial-gradient(circle at 1px 1px, rgba(255, 31, 109, 0.05) 1px, transparent 0)',
        backgroundSize: '40px 40px',
      }}
    >
      {/* Hero glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(circle at 50% 50%, rgba(255, 31, 109, 0.1) 0%, transparent 70%)',
        }}
      />

      {/* Top: Logo */}
      <div className="absolute top-12 left-12 flex items-center gap-2 z-20">
        <Link to="/" className="flex items-center gap-2 group">
          <img src="/images/stratum-logo.svg" alt="Stratum AI" className="h-9" style={{ filter: 'invert(1) brightness(2)' }} />
        </Link>
      </div>

      {/* Center: Trust Gauge Card */}
      <div className="relative z-10 w-full max-w-lg">
        <div className="auth-glass-card rounded-3xl p-10 border-white/10 shadow-2xl">
          {/* Window chrome */}
          <div className="flex items-center justify-between mb-12">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-[#FF3D00]" />
              <div className="w-3 h-3 rounded-full bg-[#FF8C00]" />
              <div className="w-3 h-3 rounded-full bg-[#00F5FF]" />
            </div>
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-widest bg-white/5 px-3 py-1 rounded-full">
              System Monitoring Active
            </div>
          </div>

          {/* Trust Gauge SVG */}
          <div className="flex flex-col items-center justify-center mb-12">
            <div className="relative w-64 h-64 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90 auth-spectral-ring" viewBox="0 0 256 256">
                <circle
                  cx="128"
                  cy="128"
                  r="110"
                  fill="transparent"
                  stroke="rgba(255,255,255,0.05)"
                  strokeWidth="10"
                />
                <circle
                  cx="128"
                  cy="128"
                  r="110"
                  fill="transparent"
                  stroke="url(#spectralGrad)"
                  strokeWidth="16"
                  strokeDasharray="690"
                  strokeDashoffset="36"
                  strokeLinecap="round"
                />
                <defs>
                  <linearGradient id="spectralGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#FF3D00" />
                    <stop offset="33%" stopColor="#FF8C00" />
                    <stop offset="66%" stopColor="#FFD700" />
                    <stop offset="100%" stopColor="#FF1F6D" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute text-center">
                <div className="text-6xl font-display font-black text-white tracking-tighter">
                  94.7<span className="text-[#FF1F6D] text-3xl">%</span>
                </div>
                <div className="text-[12px] uppercase font-bold tracking-[0.2em] text-slate-400 mt-1">
                  Trust Score
                </div>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-white/5 rounded-2xl p-5 border border-white/5">
              <div className="text-[10px] uppercase font-bold tracking-widest text-[#FF8C00] mb-2">
                Revenue Growth
              </div>
              <div className="text-2xl font-mono font-bold text-white">+124.8%</div>
            </div>
            <div className="bg-white/5 rounded-2xl p-5 border border-white/5">
              <div className="text-[10px] uppercase font-bold tracking-widest text-[#00F5FF] mb-2">
                AI Efficiency
              </div>
              <div className="text-2xl font-mono font-bold text-white">99.2%</div>
            </div>
          </div>
        </div>

        {/* Ambient blurs behind card */}
        <div className="absolute -top-12 -right-12 w-32 h-32 bg-[#FF1F6D]/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-16 -left-16 w-48 h-48 bg-[#FF8C00]/10 rounded-full blur-3xl" />
      </div>

      {/* Bottom: Protocol text */}
      <div className="absolute bottom-12 left-12 text-[10px] font-mono text-slate-500 uppercase tracking-widest z-20">
        Protocol v4.0.26 // Quantum Encrypted Session
      </div>
    </section>
  );
}
