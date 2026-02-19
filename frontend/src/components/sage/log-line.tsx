import { cn } from '@/utils/cn'
import type { LogEntry } from '@/hooks/use-logs'

const levelColors: Record<string, string> = {
  DEBUG: 'text-theme-muted',
  INFO: 'text-blue-400',
  WARNING: 'text-amber-400',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-500 font-bold',
}

const levelBg: Record<string, string> = {
  DEBUG: 'bg-theme-elevated',
  INFO: 'bg-blue-500/10',
  WARNING: 'bg-amber-500/10',
  ERROR: 'bg-red-500/10',
  CRITICAL: 'bg-red-500/20',
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
    + '.' + String(d.getMilliseconds()).padStart(3, '0')
}

export function LogLine({ entry }: { entry: LogEntry }) {
  return (
    <div className={cn(
      'flex items-start gap-3 px-3 py-1.5 font-mono text-xs leading-relaxed hover:bg-theme-elevated/30',
      levelBg[entry.level] || ''
    )}>
      {/* Timestamp */}
      <span className="text-theme-muted shrink-0 w-[90px]">
        {formatTimestamp(entry.timestamp)}
      </span>

      {/* Level badge */}
      <span className={cn(
        'shrink-0 w-[52px] text-center rounded px-1',
        levelColors[entry.level] || 'text-theme-secondary'
      )}>
        {entry.level}
      </span>

      {/* Context */}
      {(entry.tenant_slug || entry.connector_id) && (
        <span className="text-theme-muted shrink-0">
          [{entry.tenant_slug}{entry.connector_id ? `:${entry.connector_id.slice(0, 8)}` : ''}]
        </span>
      )}

      {/* Message */}
      <span className="text-theme-secondary break-all flex-1">{entry.message}</span>
    </div>
  )
}
