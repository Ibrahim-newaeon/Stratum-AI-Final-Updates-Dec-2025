/**
 * BackgroundEffects - 2026 Dark Theme Background Effects
 *
 * Updated for 2026 theme with:
 * - OLED-optimized mesh gradient with electric neon colors
 * - Noise texture overlay for depth
 * - Floating morphing orbs with 2026 electric palette
 *
 * Respects prefers-reduced-motion for accessibility
 */

import { cn } from '@/lib/utils';

interface BackgroundEffectsProps {
  className?: string;
  showOrbs?: boolean;
}

export function BackgroundEffects({ className, showOrbs = true }: BackgroundEffectsProps) {
  return (
    <>
      {/* 2026 Mesh Gradient Background */}
      <div className={cn('mesh-gradient', className)} aria-hidden="true" />

      {/* Noise Texture Overlay */}
      <div className="noise-overlay" aria-hidden="true" />

      {/* 2026 Floating Orbs - Electric Neon */}
      {showOrbs && (
        <div
          className="fixed inset-0 pointer-events-none overflow-hidden z-[-1]"
          aria-hidden="true"
        >
          {/* Electric Violet Orb - Top Left */}
          <div
            className={cn(
              'absolute top-1/4 left-1/4 w-96 h-96',
              'bg-[#8B5CF6]/10 rounded-full blur-3xl', // 2026 Electric violet
              'animate-morph motion-reduce:animate-none'
            )}
          />

          {/* Electric Cyan Orb - Bottom Right */}
          <div
            className={cn(
              'absolute bottom-1/4 right-1/4 w-80 h-80',
              'bg-[#00D4FF]/8 rounded-full blur-3xl', // 2026 Electric cyan
              'animate-morph motion-reduce:animate-none'
            )}
            style={{ animationDelay: '-4s' }}
          />

          {/* Coral Orb - Center Right */}
          <div
            className={cn(
              'absolute top-1/2 right-1/3 w-64 h-64',
              'bg-[#FF6B6B]/6 rounded-full blur-3xl', // 2026 Coral
              'animate-float motion-reduce:animate-none'
            )}
          />

          {/* Neon Green Orb - Bottom Left (subtle) */}
          <div
            className={cn(
              'absolute bottom-1/3 left-1/6 w-48 h-48',
              'bg-[#00FF88]/4 rounded-full blur-3xl', // 2026 Neon green
              'animate-float motion-reduce:animate-none'
            )}
            style={{ animationDelay: '-2s' }}
          />
        </div>
      )}
    </>
  );
}

export default BackgroundEffects;
