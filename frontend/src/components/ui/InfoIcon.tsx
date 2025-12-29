import { Info } from 'lucide-react'
import { cn } from '@/lib/utils'

interface InfoIconProps {
  className?: string
  size?: number
  tooltip?: string
  onClick?: () => void
}

export function InfoIcon({ className, size = 16, tooltip, onClick }: InfoIconProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center cursor-help text-gray-400 hover:text-gray-300 transition-colors',
        onClick && 'cursor-pointer',
        className
      )}
      title={tooltip}
      onClick={onClick}
    >
      <Info size={size} />
    </span>
  )
}

export default InfoIcon
