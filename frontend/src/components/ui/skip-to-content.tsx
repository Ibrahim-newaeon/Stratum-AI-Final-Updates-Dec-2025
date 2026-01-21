"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export interface SkipToContentProps
  extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  /**
   * The ID of the main content element to skip to
   * @default "main-content"
   */
  contentId?: string
  /**
   * Custom label for the skip link
   * @default "Skip to main content"
   */
  label?: string
}

/**
 * SkipToContent - Accessibility component for keyboard navigation
 *
 * This component provides a skip link that allows keyboard users to bypass
 * navigation menus and jump directly to the main content. It's hidden by
 * default and becomes visible when focused.
 *
 * @example
 * // In your App or Layout component:
 * <SkipToContent />
 * <Header />
 * <main id="main-content">...</main>
 *
 * @example
 * // With custom ID and label:
 * <SkipToContent contentId="content" label="Skip navigation" />
 */
const SkipToContent = React.forwardRef<HTMLAnchorElement, SkipToContentProps>(
  (
    {
      contentId = "main-content",
      label = "Skip to main content",
      className,
      ...props
    },
    ref
  ) => {
    return (
      <a
        ref={ref}
        href={`#${contentId}`}
        className={cn(
          // Hidden by default
          "sr-only",
          // Visible on focus
          "focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[9999]",
          // Styling when visible
          "focus:px-4 focus:py-2 focus:rounded-md",
          "focus:bg-primary focus:text-primary-foreground",
          "focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          // Animation
          "transition-all duration-150",
          className
        )}
        {...props}
      >
        {label}
      </a>
    )
  }
)
SkipToContent.displayName = "SkipToContent"

export { SkipToContent }
