/**
 * BackgroundEffects - 2026 Dark Theme Background Effects
 *
 * Includes:
 * - Mesh gradient background with multiple radial gradients
 * - Noise texture overlay for depth
 * - Floating morphing orbs for visual interest
 *
 * Respects prefers-reduced-motion for accessibility
 */

import { cn } from '@/lib/utils'

interface BackgroundEffectsProps {
  className?: string
  showOrbs?: boolean
}

export function BackgroundEffects({
  className,
  showOrbs = true
}: BackgroundEffectsProps) {
  return (
    <>
      {/* Mesh Gradient Background */}
      <div
        className={cn("mesh-gradient", className)}
        aria-hidden="true"
      />

      {/* Noise Texture Overlay */}
      <div
        className="noise-overlay"
        aria-hidden="true"
      />

      {/* Floating Orbs */}
      {showOrbs && (
        <div
          className="fixed inset-0 pointer-events-none overflow-hidden z-[-1]"
          aria-hidden="true"
        >
          {/* Purple Orb - Top Left */}
          <div
            className={cn(
              "absolute top-1/4 left-1/4 w-96 h-96",
              "bg-purple-500/10 rounded-full blur-3xl",
              "animate-morph motion-reduce:animate-none"
            )}
          />

          {/* Cyan Orb - Bottom Right */}
          <div
            className={cn(
              "absolute bottom-1/4 right-1/4 w-80 h-80",
              "bg-cyan-500/10 rounded-full blur-3xl",
              "animate-morph motion-reduce:animate-none"
            )}
            style={{ animationDelay: '-4s' }}
          />

          {/* Orange Orb - Center Right */}
          <div
            className={cn(
              "absolute top-1/2 right-1/3 w-64 h-64",
              "bg-orange-500/8 rounded-full blur-3xl",
              "animate-float motion-reduce:animate-none"
            )}
          />
        </div>
      )}
    </>
  )
}

export default BackgroundEffects
