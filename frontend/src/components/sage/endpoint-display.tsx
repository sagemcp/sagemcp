import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Badge } from '@/components/ui/badge'

interface EndpointDisplayProps {
  url: string
  protocol?: string
  className?: string
}

export function EndpointDisplay({ url, protocol, className }: EndpointDisplayProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn(
      'flex items-center gap-2 rounded-md bg-theme-surface border border-theme-default px-3 py-2',
      className
    )}>
      <code className="text-sm font-mono text-theme-secondary truncate flex-1">{url}</code>
      {protocol && (
        <Badge variant="accent" className="shrink-0">{protocol}</Badge>
      )}
      <button
        onClick={handleCopy}
        className="shrink-0 p-1 rounded hover:bg-theme-elevated text-theme-muted hover:text-theme-secondary transition-colors"
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-success-400" />
        ) : (
          <Copy className="h-3.5 w-3.5" />
        )}
      </button>
    </div>
  )
}
