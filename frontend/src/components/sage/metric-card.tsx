import { cn } from '@/utils/cn'
import { Skeleton } from '@/components/ui/skeleton'
import type { LucideIcon } from 'lucide-react'

export interface MetricCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  subtitle?: string
  trend?: { value: string; direction: 'up' | 'down' | 'neutral' }
  loading?: boolean
  className?: string
}

export function MetricCard({ label, value, icon: Icon, subtitle, trend, loading, className }: MetricCardProps) {
  if (loading) {
    return (
      <div className={cn('rounded-lg border border-zinc-800 bg-surface-elevated p-6', className)}>
        <Skeleton className="h-4 w-24 mb-3" />
        <Skeleton className="h-8 w-16 mb-2" />
        <Skeleton className="h-3 w-20" />
      </div>
    )
  }

  return (
    <div className={cn('rounded-lg border border-zinc-800 bg-surface-elevated p-6 transition-colors hover:border-zinc-700', className)}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-zinc-400">{label}</span>
        <div className="rounded-md bg-accent/10 p-2">
          <Icon className="h-4 w-4 text-accent" />
        </div>
      </div>
      <p className="text-3xl font-bold font-mono text-zinc-100 tracking-tight">{value}</p>
      {subtitle && (
        <p className="text-xs text-zinc-500 mt-1">{subtitle}</p>
      )}
      {trend && (
        <p className={cn(
          'text-xs mt-1',
          trend.direction === 'up' && 'text-success-400',
          trend.direction === 'down' && 'text-error-400',
          trend.direction === 'neutral' && 'text-zinc-500',
        )}>
          {trend.direction === 'up' && '+'}{trend.value}
        </p>
      )}
    </div>
  )
}
