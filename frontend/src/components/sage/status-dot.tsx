import { cn } from '@/utils/cn'

type StatusDotVariant = 'healthy' | 'warning' | 'error' | 'idle'

const dotColors: Record<StatusDotVariant, string> = {
  healthy: 'bg-success-500',
  warning: 'bg-warning-500',
  error: 'bg-error-500',
  idle: 'bg-zinc-500',
}

const glowColors: Record<StatusDotVariant, string> = {
  healthy: 'shadow-[0_0_6px_rgba(34,197,94,0.6)]',
  warning: 'shadow-[0_0_6px_rgba(245,158,11,0.6)]',
  error: 'shadow-[0_0_6px_rgba(239,68,68,0.6)]',
  idle: '',
}

interface StatusDotProps {
  variant?: StatusDotVariant
  pulse?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizes = {
  sm: 'h-1.5 w-1.5',
  md: 'h-2 w-2',
  lg: 'h-3 w-3',
}

export function StatusDot({ variant = 'healthy', pulse = true, size = 'md', className }: StatusDotProps) {
  return (
    <span
      className={cn(
        'inline-block rounded-full',
        sizes[size],
        dotColors[variant],
        glowColors[variant],
        pulse && variant !== 'idle' && 'animate-status-pulse',
        className
      )}
    />
  )
}
