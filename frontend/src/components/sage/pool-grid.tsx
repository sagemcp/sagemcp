import { useState } from 'react'
import { cn } from '@/utils/cn'
import type { PoolEntry } from '@/types'

const statusColors = {
  healthy: 'bg-green-500',
  expiring: 'bg-amber-500',
  expired: 'bg-red-500',
}

const statusGlow = {
  healthy: 'shadow-[0_0_6px_rgba(34,197,94,0.4)]',
  expiring: 'shadow-[0_0_6px_rgba(245,158,11,0.4)]',
  expired: 'shadow-[0_0_6px_rgba(239,68,68,0.4)]',
}

interface PoolGridProps {
  entries: PoolEntry[]
  onEvict?: (tenantSlug: string, connectorId: string) => void
}

export function PoolGrid({ entries, onEvict }: PoolGridProps) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null)

  // Group entries by tenant
  const byTenant: Record<string, PoolEntry[]> = {}
  for (const entry of entries) {
    const group = byTenant[entry.tenant_slug] || []
    group.push(entry)
    byTenant[entry.tenant_slug] = group
  }

  const tenants = Object.keys(byTenant).sort()

  if (entries.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-zinc-500 text-sm">
        No active pool entries
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {tenants.map(tenant => (
        <div key={tenant}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-zinc-400 font-mono">{tenant}</span>
            <span className="text-xs text-zinc-600">{byTenant[tenant].length} instance{byTenant[tenant].length !== 1 ? 's' : ''}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {byTenant[tenant].map(entry => (
              <div
                key={entry.key}
                className="relative"
                onMouseEnter={() => setHoveredKey(entry.key)}
                onMouseLeave={() => setHoveredKey(null)}
              >
                <button
                  onClick={() => onEvict?.(entry.tenant_slug, entry.connector_id)}
                  className={cn(
                    'h-4 w-4 rounded-full transition-all duration-300',
                    statusColors[entry.status],
                    statusGlow[entry.status],
                    'hover:scale-125 cursor-pointer'
                  )}
                  title={`${entry.connector_id} (${entry.status})`}
                />

                {/* Tooltip */}
                {hoveredKey === entry.key && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 pointer-events-none">
                    <div className="rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs shadow-elevated whitespace-nowrap">
                      <div className="font-mono text-zinc-200">{entry.connector_id}</div>
                      <div className="text-zinc-400 mt-1">
                        Hits: {entry.hit_count} | TTL: {Math.round(entry.ttl_remaining)}s
                      </div>
                      <div className="text-zinc-500">
                        Last access: {entry.last_access.toFixed(0)}s ago
                      </div>
                      <div className="text-zinc-600 text-[10px] mt-1">Click to evict</div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
