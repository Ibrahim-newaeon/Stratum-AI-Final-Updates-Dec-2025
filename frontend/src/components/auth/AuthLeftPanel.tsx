/**
 * Shared Left Panel for Authentication pages
 * Command Center design system — deep void, testimonial, trust badge
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
        'hidden lg:flex w-2/5 bg-[#05080F] relative flex-col justify-between p-12 border-r border-[#1E2740]',
        className
      )}
      style={{
        backgroundImage:
          'linear-gradient(rgba(30,39,64,0.12) 1px, transparent 1px), linear-gradient(90deg, rgba(30,39,64,0.12) 1px, transparent 1px)',
        backgroundSize: '32px 32px',
      }}
    >
      {/* Logo */}
      <div className="relative z-10">
        <Link to="/" className="flex items-center gap-3">
          <img
            src="/images/stratum-logo.png"
            alt="Stratum AI"
            className="h-8"
            
            loading="lazy"
            decoding="async"
          />
        </Link>
      </div>

      {/* Testimonial */}
      <div className="relative z-10 max-w-sm">
        <blockquote className="text-2xl font-medium text-[#F0EDE5] leading-relaxed mb-6">
          "Stratum doesn't just manage our ads. It partners with us to grow revenue."
        </blockquote>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#1E2740] flex items-center justify-center text-[#8B92A8] text-sm font-semibold">
            JD
          </div>
          <div>
            <p className="text-sm font-medium text-[#F0EDE5]">Jane Doe</p>
            <p className="text-xs text-[#5A6278]">CMO, GrowthCo</p>
          </div>
        </div>
      </div>

      {/* Bottom trust badge */}
      <div className="relative z-10">
        <p className="text-xs text-[#5A6278] tracking-wide">
          Trusted by 500+ growth teams
        </p>
      </div>

      {/* Subtle ambient glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(201,162,39,0.04), transparent 70%)',
        }}
      />
    </section>
  );
}

