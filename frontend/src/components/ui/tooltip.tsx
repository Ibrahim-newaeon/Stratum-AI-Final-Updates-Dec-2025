"use client"

import * as React from "react"
import * as TooltipPrimitive from "@radix-ui/react-tooltip"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const TooltipProvider = TooltipPrimitive.Provider

const Tooltip = TooltipPrimitive.Root

const TooltipTrigger = TooltipPrimitive.Trigger

// Tooltip content variants
const tooltipContentVariants = cva(
  "z-50 overflow-hidden rounded-md px-3 py-1.5 text-xs animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-[--radix-tooltip-content-transform-origin]",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        dark: "bg-popover text-popover-foreground border shadow-md",
        light: "bg-background text-foreground border shadow-md",
        info: "bg-info/90 text-white",
        success: "bg-success/90 text-white",
        warning: "bg-warning/90 text-black",
        destructive: "bg-destructive/90 text-white",
      },
      size: {
        default: "px-3 py-1.5 text-xs",
        sm: "px-2 py-1 text-xs",
        lg: "px-4 py-2 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface TooltipContentProps
  extends React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>,
    VariantProps<typeof tooltipContentVariants> {
  shortcut?: string | string[]
}

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  TooltipContentProps
>(({ className, sideOffset = 4, variant, size, shortcut, children, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(tooltipContentVariants({ variant, size }), className)}
      {...props}
    >
      <div className="flex items-center gap-2">
        <span>{children}</span>
        {shortcut && (
          <TooltipShortcut keys={Array.isArray(shortcut) ? shortcut : [shortcut]} />
        )}
      </div>
    </TooltipPrimitive.Content>
  </TooltipPrimitive.Portal>
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName

// Keyboard shortcut display
interface TooltipShortcutProps {
  keys: string[]
}

const TooltipShortcut = ({ keys }: TooltipShortcutProps) => (
  <span className="flex items-center gap-0.5 ml-1">
    {keys.map((key, index) => (
      <kbd
        key={index}
        className="pointer-events-none inline-flex h-4 select-none items-center justify-center rounded border border-current/20 bg-current/10 px-1 font-mono text-[10px] font-medium opacity-70"
      >
        {key}
      </kbd>
    ))}
  </span>
)
TooltipShortcut.displayName = "TooltipShortcut"

// Arrow component
const TooltipArrow = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Arrow>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Arrow>
>(({ className, ...props }, ref) => (
  <TooltipPrimitive.Arrow
    ref={ref}
    className={cn("fill-primary", className)}
    {...props}
  />
))
TooltipArrow.displayName = TooltipPrimitive.Arrow.displayName

// Simple tooltip component for quick use
export interface SimpleTooltipProps {
  children: React.ReactNode
  content: React.ReactNode
  shortcut?: string | string[]
  side?: "top" | "right" | "bottom" | "left"
  align?: "start" | "center" | "end"
  variant?: TooltipContentProps["variant"]
  size?: TooltipContentProps["size"]
  delayDuration?: number
  disabled?: boolean
  asChild?: boolean
}

const SimpleTooltip = ({
  children,
  content,
  shortcut,
  side = "top",
  align = "center",
  variant = "default",
  size = "default",
  delayDuration = 200,
  disabled = false,
  asChild = true,
}: SimpleTooltipProps) => {
  if (disabled || !content) {
    return <>{children}</>
  }

  return (
    <TooltipProvider>
      <Tooltip delayDuration={delayDuration}>
        <TooltipTrigger asChild={asChild}>{children}</TooltipTrigger>
        <TooltipContent
          side={side}
          align={align}
          variant={variant}
          size={size}
          shortcut={shortcut}
        >
          {content}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
SimpleTooltip.displayName = "SimpleTooltip"

export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
  TooltipArrow,
  TooltipShortcut,
  SimpleTooltip,
}
