import { cn } from '@/utils/cn'
import { StatusDot } from './status-dot'

interface LiveIndicatorProps {
  className?: string
}

export function LiveIndicator({ className }: LiveIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      <StatusDot variant="healthy" size="sm" />
      <span className="text-xs font-medium text-success-400">Live</span>
    </div>
  )
}
