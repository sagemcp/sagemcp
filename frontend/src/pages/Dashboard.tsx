import { Link } from 'react-router-dom'
import {
  Server,
  Users,
  Wrench,
  Zap,
  Building2,
  Activity,
  ArrowRight,
} from 'lucide-react'
import { MetricCard } from '@/components/sage/metric-card'
import { StatusDot } from '@/components/sage/status-dot'
import { EmptyState } from '@/components/sage/empty-state'
import { LiveIndicator } from '@/components/sage/live-indicator'
import { useStats } from '@/hooks/use-stats'

export default function Dashboard() {
  const { data: stats, isLoading } = useStats()

  const poolHitRate = stats && (stats.pool_hits + stats.pool_misses) > 0
    ? Math.round((stats.pool_hits / (stats.pool_hits + stats.pool_misses)) * 100)
    : 0

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Dashboard</h1>
          <p className="text-sm text-zinc-500 mt-1">Platform overview and health</p>
        </div>
        <LiveIndicator />
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Instances"
          value={stats?.active_instances ?? 0}
          icon={Server}
          loading={isLoading}
          trend={stats ? { value: `${poolHitRate}% hit rate`, direction: poolHitRate > 80 ? 'up' : 'neutral' } : undefined}
        />
        <MetricCard
          label="Active Sessions"
          value={stats?.active_sessions ?? 0}
          icon={Users}
          loading={isLoading}
        />
        <MetricCard
          label="Tool Calls Today"
          value={stats?.tool_calls_today ?? 0}
          icon={Wrench}
          loading={isLoading}
        />
        <MetricCard
          label="Connectors"
          value={stats?.connectors ?? 0}
          icon={Zap}
          loading={isLoading}
        />
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pool Health - 2/3 width */}
        <div className="lg:col-span-2">
          <div className="rounded-lg border border-zinc-800 bg-surface-elevated">
            <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
              <h3 className="text-sm font-medium text-zinc-200">Pool Health</h3>
              <Link to="/pool" className="text-xs text-zinc-500 hover:text-accent flex items-center gap-1 transition-colors">
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="p-6">
              {stats && stats.active_instances > 0 ? (
                <div className="space-y-4">
                  {/* Pool stats summary */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center">
                      <p className="text-2xl font-mono font-bold text-zinc-100">{stats.active_instances}</p>
                      <p className="text-xs text-zinc-500 mt-1">Pooled</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-mono font-bold text-success-400">{stats.pool_hits}</p>
                      <p className="text-xs text-zinc-500 mt-1">Hits</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-mono font-bold text-zinc-400">{stats.pool_misses}</p>
                      <p className="text-xs text-zinc-500 mt-1">Misses</p>
                    </div>
                  </div>
                  {/* Hit rate bar */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-zinc-500">Hit Rate</span>
                      <span className="text-xs font-mono text-zinc-300">{poolHitRate}%</span>
                    </div>
                    <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full transition-all duration-500"
                        style={{ width: `${poolHitRate}%` }}
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={Server}
                  title="No active pool entries"
                  description="Server instances will appear here when tenants start making MCP requests."
                />
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions + System Status - 1/3 width */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="rounded-lg border border-zinc-800 bg-surface-elevated">
            <div className="px-6 py-4 border-b border-zinc-800">
              <h3 className="text-sm font-medium text-zinc-200">Quick Actions</h3>
            </div>
            <div className="p-4 space-y-1">
              <Link
                to="/tenants"
                className="flex items-center gap-3 rounded-md px-3 py-2.5 hover:bg-zinc-800 transition-colors group"
              >
                <Building2 className="h-4 w-4 text-zinc-500 group-hover:text-accent" />
                <div>
                  <p className="text-sm text-zinc-200">Manage Tenants</p>
                  <p className="text-xs text-zinc-500">Create and configure tenants</p>
                </div>
              </Link>
              <Link
                to="/mcp-test"
                className="flex items-center gap-3 rounded-md px-3 py-2.5 hover:bg-zinc-800 transition-colors group"
              >
                <Activity className="h-4 w-4 text-zinc-500 group-hover:text-accent" />
                <div>
                  <p className="text-sm text-zinc-200">Test MCP Protocol</p>
                  <p className="text-xs text-zinc-500">Debug and test connections</p>
                </div>
              </Link>
            </div>
          </div>

          {/* System Status */}
          <div className="rounded-lg border border-zinc-800 bg-surface-elevated">
            <div className="px-6 py-4 border-b border-zinc-800">
              <h3 className="text-sm font-medium text-zinc-200">System Status</h3>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-400">API Server</span>
                <div className="flex items-center gap-1.5">
                  <StatusDot variant="healthy" size="sm" />
                  <span className="text-xs text-zinc-300">Healthy</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-400">Database</span>
                <div className="flex items-center gap-1.5">
                  <StatusDot variant="healthy" size="sm" />
                  <span className="text-xs text-zinc-300">Connected</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-400">Tenants</span>
                <span className="text-xs font-mono text-zinc-300">{stats?.tenants ?? '—'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
