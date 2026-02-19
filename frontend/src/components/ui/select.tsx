import * as React from 'react'
import { cn } from '@/utils/cn'

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <select
      className={cn(
        'flex h-9 w-full rounded-md border border-theme-default bg-theme-surface px-3 py-1 text-sm text-theme-primary transition-colors',
        'focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      ref={ref}
      {...props}
    >
      {children}
    </select>
  )
)
Select.displayName = 'Select'

export { Select }
