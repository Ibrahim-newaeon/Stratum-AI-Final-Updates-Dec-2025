import { Info } from 'lucide-react'
import { cn } from '@/lib/utils'

interface InfoIconProps {
  className?: string
  size?: number
  tooltip?: string
  onClick?: () => void
}

export function InfoIcon({ className, size = 16, tooltip, onClick }: InfoIconProps) {
  const Component = onClick ? 'button' : 'span'

  return (
    <Component
      className={cn(
        'inline-flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors',
        onClick ? 'cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded' : 'cursor-help',
        className
      )}
      title={tooltip}
      onClick={onClick}
      aria-label={tooltip || 'More information'}
      {...(onClick ? { type: 'button' as const } : {})}
    >
      <Info size={size} aria-hidden="true" />
    </Component>
  )
}

export default InfoIcon
