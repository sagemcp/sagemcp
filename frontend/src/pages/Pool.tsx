import {
  Server,
  Zap,
  Clock,
  Trash2,
  Activity,
  HardDrive,
} from 'lucide-react'
import { toast } from 'sonner'
import { MetricCard } from '@/components/sage/metric-card'
import { PoolGrid } from '@/components/sage/pool-grid'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/sage/empty-state'
import { usePoolEntries, usePoolSummary, useEvictPoolEntry, useEvictIdle } from '@/hooks/use-pool'

export default function Pool() {
  const { data: entries = [], isLoading: entriesLoading } = usePoolEntries()
  const { data: summary, isLoading: summaryLoading } = usePoolSummary()
  const evictEntry = useEvictPoolEntry()
  const evictIdle = useEvictIdle()

  const handleEvict = (tenantSlug: string, connectorId: string) => {
    evictEntry.mutate({ tenantSlug, connectorId }, {
      onSuccess: () => toast.success(`Evicted ${tenantSlug}:${connectorId}`),
      onError: () => toast.error('Failed to evict entry'),
    })
  }

  const handleEvictIdle = () => {
    evictIdle.mutate(600, {
      onSuccess: (res: any) => {
        const count = res.data?.evicted_count ?? 0
        toast.success(`Evicted ${count} idle entr${count === 1 ? 'y' : 'ies'}`)
      },
      onError: () => toast.error('Failed to evict idle entries'),
    })
  }

  const isLoading = entriesLoading || summaryLoading

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Server Pool</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Cached MCP server instances — LRU eviction with TTL expiry
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleEvictIdle}
            disabled={evictIdle.isPending}
          >
            <Trash2 className="h-4 w-4 mr-1.5" />
            {evictIdle.isPending ? 'Evicting...' : 'Evict Idle'}
          </Button>
        </div>
      </div>

      {/* Stat cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-lg" />
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Pool Size"
            value={summary.total}
            subtitle={`of ${summary.max_size} max`}
            icon={Server}
          />
          <MetricCard
            label="Hit Rate"
            value={`${summary.hit_rate}%`}
            subtitle={`${summary.hits} hits / ${summary.misses} misses`}
            icon={Zap}
          />
          <MetricCard
            label="Healthy"
            value={summary.by_status.healthy}
            subtitle={`${summary.by_status.expiring} expiring, ${summary.by_status.expired} expired`}
            icon={Activity}
          />
          <MetricCard
            label="Memory Est."
            value={`${summary.memory_estimate_kb} KB`}
            subtitle={`TTL: ${Math.round(summary.ttl_seconds / 60)}m`}
            icon={HardDrive}
          />
        </div>
      ) : null}

      {/* Pool utilization bar */}
      {summary && summary.max_size > 0 && (
        <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-zinc-300">Pool Utilization</span>
            <span className="text-xs text-zinc-500">
              {summary.total} / {summary.max_size} slots
            </span>
          </div>
          <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-accent transition-all duration-500"
              style={{ width: `${Math.min(100, (summary.total / summary.max_size) * 100)}%` }}
            />
          </div>
          <div className="flex items-center gap-4 mt-3">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
              <span className="text-xs text-zinc-400">Healthy ({summary.by_status.healthy})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
              <span className="text-xs text-zinc-400">Expiring ({summary.by_status.expiring})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
              <span className="text-xs text-zinc-400">Expired ({summary.by_status.expired})</span>
            </div>
          </div>
        </div>
      )}

      {/* Tenant breakdown */}
      {summary && Object.keys(summary.by_tenant).length > 0 && (
        <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-4">
          <h3 className="text-sm font-medium text-zinc-300 mb-3">By Tenant</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.by_tenant)
              .sort(([, a], [, b]) => b - a)
              .map(([tenant, count]) => (
                <Badge key={tenant} variant="default" className="font-mono text-xs">
                  {tenant}: {count}
                </Badge>
              ))}
          </div>
        </div>
      )}

      {/* Pool Grid */}
      <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-zinc-300">Instance Grid</h3>
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <Clock className="h-3 w-3" />
            Refreshes every 5s
          </div>
        </div>
        {entriesLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </div>
        ) : entries.length > 0 ? (
          <PoolGrid entries={entries} onEvict={handleEvict} />
        ) : (
          <EmptyState
            icon={Server}
            title="Pool is empty"
            description="MCP server instances will appear here as they are created on demand"
          />
        )}
      </div>
    </div>
  )
}
