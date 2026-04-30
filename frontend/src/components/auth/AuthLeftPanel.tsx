/**
 * Shared Left Panel for Authentication pages
 * Stratum figma theme — ink surface, ember accent, Geist typography
 */

import { cn } from '@/lib/utils';

interface AuthLeftPanelProps {
  className?: string;
}

export default function AuthLeftPanel({ className }: AuthLeftPanelProps) {
  return (
    <section
      className={cn(
        'hidden lg:flex w-2/5 bg-[#0B0B0B] relative flex-col justify-between p-12 border-r border-[#1F1F1F] overflow-hidden',
        className
      )}
      style={{ fontFamily: 'Geist, system-ui, sans-serif' }}
    >
      {/* Side ember glow */}
      <div
        className="absolute inset-0 pointer-events-none opacity-70"
        style={{
          background:
            'radial-gradient(70% 60% at 0% 50%, rgba(255,90,31,0.18) 0%, rgba(255,90,31,0.04) 45%, transparent 75%)',
          filter: 'blur(40px)',
        }}
        aria-hidden="true"
      />

      {/* Top: logo + back-home (plain <a> for full page load → figma landing) */}
      <div className="relative z-10 flex items-center justify-between">
        <a href="/landing.html" className="flex items-center gap-2" aria-label="Stratum AI home">
          <span className="text-[19px] font-medium tracking-tight text-white">stratum.ai</span>
        </a>
        <a
          href="/landing.html"
          className="text-[12px] text-[#9A9A9A] hover:text-white transition-colors flex items-center gap-1"
        >
          ← Back to site
        </a>
      </div>

      {/* Center: testimonial */}
      <div className="relative z-10 max-w-md">
        <span
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11.5px] uppercase tracking-[0.06em] font-medium text-[#ECECEC] mb-6"
          style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid #1F1F1F',
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full bg-[#FF5A1F]"
            style={{ boxShadow: '0 0 8px #FF5A1F' }}
          />
          Trusted by 500+ growth teams
        </span>
        <blockquote className="text-[28px] leading-tight tracking-tight text-white mt-6 mb-8">
          &ldquo;Stratum doesn't just manage our ads. It partners with us to grow revenue — with
          every decision auditable and reversible.&rdquo;
        </blockquote>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#262626] flex items-center justify-center text-[#9A9A9A] text-sm font-medium">
            JD
          </div>
          <div>
            <p className="text-sm font-medium text-white">Jane Doe</p>
            <p className="text-xs text-[#6B6B6B]">CMO, GrowthCo</p>
          </div>
        </div>
      </div>

      {/* Bottom: status marker */}
      <div
        className="relative z-10 flex items-center gap-2 text-[11px] text-[#6B6B6B] uppercase tracking-[0.12em]"
        style={{ fontFamily: 'Geist Mono, monospace' }}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-[#FF5A1F]" />
        Trust engine — operational
      </div>
    </section>
  );
}
