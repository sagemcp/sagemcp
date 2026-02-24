import * as React from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/utils/cn'

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, ...props }, ref) => {
    const generatedId = React.useId()
    const inputId = id || generatedId

    return (
      <div className="flex items-center gap-2">
        <div className="relative">
          <input
            type="checkbox"
            id={inputId}
            ref={ref}
            className={cn(
              'peer h-4 w-4 shrink-0 rounded border border-theme-hover bg-theme-surface appearance-none cursor-pointer',
              'checked:bg-accent checked:border-accent',
              'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:ring-offset-1 focus:ring-offset-zinc-900',
              'disabled:cursor-not-allowed disabled:opacity-50',
              className
            )}
            {...props}
          />
          <Check className="absolute top-0 left-0 h-4 w-4 text-zinc-900 pointer-events-none opacity-0 peer-checked:opacity-100" />
        </div>
        {label && (
          <label htmlFor={inputId} className="text-sm text-theme-secondary cursor-pointer select-none">
            {label}
          </label>
        )}
      </div>
    )
  }
)
Checkbox.displayName = 'Checkbox'

export { Checkbox }
