"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

// Toggle/Switch variants - pure CSS implementation (no external dependency)
const toggleVariants = cva(
  "peer relative inline-flex shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "",
        success: "",
        destructive: "",
        warning: "",
      },
      size: {
        default: "h-5 w-9",
        sm: "h-4 w-7",
        lg: "h-6 w-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const toggleThumbVariants = cva(
  "pointer-events-none absolute left-0.5 block rounded-full bg-background shadow-lg ring-0 transition-transform",
  {
    variants: {
      size: {
        default: "h-4 w-4",
        sm: "h-3 w-3",
        lg: "h-5 w-5",
      },
    },
    defaultVariants: {
      size: "default",
    },
  }
)

// Get variant colors
const getVariantColors = (variant: string | null | undefined, checked: boolean) => {
  if (!checked) return "bg-input"

  switch (variant) {
    case "success":
      return "bg-success"
    case "destructive":
      return "bg-destructive"
    case "warning":
      return "bg-warning"
    default:
      return "bg-primary"
  }
}

// Get translate distance based on size
const getTranslateX = (size: string | null | undefined, checked: boolean) => {
  if (!checked) return "translate-x-0"

  switch (size) {
    case "sm":
      return "translate-x-3"
    case "lg":
      return "translate-x-5"
    default:
      return "translate-x-4"
  }
}

export interface ToggleProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onChange">,
    VariantProps<typeof toggleVariants> {
  checked?: boolean
  defaultChecked?: boolean
  onCheckedChange?: (checked: boolean) => void
  label?: string
  description?: string
  labelPosition?: "left" | "right"
}

const Toggle = React.forwardRef<HTMLButtonElement, ToggleProps>(
  (
    {
      className,
      variant,
      size,
      checked: controlledChecked,
      defaultChecked = false,
      onCheckedChange,
      label,
      description,
      labelPosition = "right",
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const [internalChecked, setInternalChecked] = React.useState(defaultChecked)
    const isControlled = controlledChecked !== undefined
    const checked = isControlled ? controlledChecked : internalChecked

    const generatedId = React.useId()
    const switchId = id || generatedId

    const handleClick = () => {
      if (disabled) return

      const newValue = !checked
      if (!isControlled) {
        setInternalChecked(newValue)
      }
      onCheckedChange?.(newValue)
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault()
        handleClick()
      }
    }

    const switchElement = (
      <button
        id={switchId}
        ref={ref}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={cn(
          toggleVariants({ variant, size }),
          getVariantColors(variant, checked),
          className
        )}
        {...props}
      >
        <span
          className={cn(
            toggleThumbVariants({ size }),
            getTranslateX(size, checked)
          )}
        />
      </button>
    )

    // If no label, return just the switch
    if (!label) {
      return switchElement
    }

    // With label
    return (
      <div className="flex items-center gap-3">
        {labelPosition === "left" && (
          <div className="flex flex-col">
            <label
              htmlFor={switchId}
              className={cn(
                "text-sm font-medium leading-none cursor-pointer",
                disabled && "cursor-not-allowed opacity-70"
              )}
            >
              {label}
            </label>
            {description && (
              <p className="text-sm text-muted-foreground mt-1">{description}</p>
            )}
          </div>
        )}

        {switchElement}

        {labelPosition === "right" && (
          <div className="flex flex-col">
            <label
              htmlFor={switchId}
              className={cn(
                "text-sm font-medium leading-none cursor-pointer",
                disabled && "cursor-not-allowed opacity-70"
              )}
            >
              {label}
            </label>
            {description && (
              <p className="text-sm text-muted-foreground mt-1">{description}</p>
            )}
          </div>
        )}
      </div>
    )
  }
)
Toggle.displayName = "Toggle"

// Also export as Switch for compatibility
const Switch = Toggle

// ToggleGroup for multiple related toggles
export interface ToggleGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: string
  description?: string
}

const ToggleGroup = React.forwardRef<HTMLDivElement, ToggleGroupProps>(
  ({ className, label, description, children, ...props }, ref) => (
    <div
      ref={ref}
      role="group"
      aria-label={label}
      className={cn("space-y-4", className)}
      {...props}
    >
      {(label || description) && (
        <div className="space-y-1">
          {label && (
            <h4 className="text-sm font-medium leading-none">{label}</h4>
          )}
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      )}
      <div className="space-y-3">{children}</div>
    </div>
  )
)
ToggleGroup.displayName = "ToggleGroup"

// ToggleGroupItem for use within ToggleGroup
export interface ToggleGroupItemProps extends ToggleProps {}

const ToggleGroupItem = React.forwardRef<HTMLButtonElement, ToggleGroupItemProps>(
  ({ className, ...props }, ref) => (
    <Toggle
      ref={ref}
      className={cn(
        "flex items-center justify-between rounded-lg border border-border p-4 hover:bg-accent/50 transition-colors",
        className
      )}
      {...props}
    />
  )
)
ToggleGroupItem.displayName = "ToggleGroupItem"

export { Toggle, Switch, ToggleGroup, ToggleGroupItem }
