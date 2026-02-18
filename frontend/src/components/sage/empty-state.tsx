import { cn } from '@/utils/cn'
import { Button } from '@/components/ui/button'
import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 px-4', className)}>
      <div className="rounded-full bg-theme-elevated p-4 mb-4">
        <Icon className="h-8 w-8 text-theme-muted" />
      </div>
      <h3 className="text-sm font-medium text-theme-secondary mb-1">{title}</h3>
      <p className="text-xs text-theme-muted text-center max-w-sm">{description}</p>
      {action && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  )
}
