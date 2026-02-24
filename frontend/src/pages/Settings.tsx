import { useQuery } from '@tanstack/react-query'
import {
  Settings as SettingsIcon,
  Server,
  Shield,
  Database,
  Info,
  Gauge,
  Globe,
  Zap,
} from 'lucide-react'
import { settingsApi } from '@/utils/api'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

function SettingRow({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-theme-default last:border-0">
      <span className="text-sm text-theme-secondary">{label}</span>
      <span className={`text-sm text-theme-primary ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  )
}

function SettingSection({ icon: Icon, title, children }: { icon: React.ElementType; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-theme-default bg-surface-elevated">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-theme-default">
        <Icon className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-medium text-theme-primary">{title}</h3>
      </div>
      <div className="px-5 py-2">
        {children}
      </div>
    </div>
  )
}

export default function Settings() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsApi.get().then(res => res.data),
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-theme-primary">Settings</h1>
          <p className="text-sm text-theme-muted mt-1">Platform configuration (read-only)</p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (!settings) return null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-theme-primary">Settings</h1>
        <p className="text-sm text-theme-muted mt-1">Platform configuration (read-only)</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Platform */}
        <SettingSection icon={Info} title="Platform">
          <SettingRow label="Name" value={settings.platform.app_name} />
          <SettingRow label="Version" value={settings.platform.app_version} mono />
          <SettingRow label="Environment" value={
            <Badge variant={settings.platform.environment === 'production' ? 'healthy' : 'idle'}>
              {settings.platform.environment}
            </Badge>
          } />
          <SettingRow label="Debug Mode" value={settings.platform.debug ? 'Enabled' : 'Disabled'} />
        </SettingSection>

        {/* Feature Flags */}
        <SettingSection icon={Zap} title="Feature Flags">
          <SettingRow label="Server Pool" value={
            <Badge variant={settings.features.server_pool ? 'healthy' : 'idle'}>
              {settings.features.server_pool ? 'Enabled' : 'Disabled'}
            </Badge>
          } />
          <SettingRow label="Session Management" value={
            <Badge variant={settings.features.session_management ? 'healthy' : 'idle'}>
              {settings.features.session_management ? 'Enabled' : 'Disabled'}
            </Badge>
          } />
          <SettingRow label="Prometheus Metrics" value={
            <Badge variant={settings.features.metrics ? 'healthy' : 'idle'}>
              {settings.features.metrics ? 'Enabled' : 'Disabled'}
            </Badge>
          } />
        </SettingSection>

        {/* Pool */}
        <SettingSection icon={Server} title="Server Pool">
          <SettingRow label="Max Size" value={settings.pool.max_size} mono />
          <SettingRow label="TTL" value={`${settings.pool.ttl_seconds}s (${Math.round(settings.pool.ttl_seconds / 60)}m)`} mono />
          <SettingRow label="Current Size" value={settings.pool.current_size} mono />
        </SettingSection>

        {/* Rate Limiting */}
        <SettingSection icon={Gauge} title="Rate Limiting">
          <SettingRow label="Requests per Minute" value={settings.rate_limit.rpm} mono />
        </SettingSection>

        {/* CORS */}
        <SettingSection icon={Globe} title="CORS Origins">
          {settings.cors.origins.length > 0 ? (
            settings.cors.origins.map((origin: string, i: number) => (
              <SettingRow key={i} label={`Origin ${i + 1}`} value={origin} mono />
            ))
          ) : (
            <SettingRow label="Origins" value="None configured" />
          )}
        </SettingSection>

        {/* MCP */}
        <SettingSection icon={Shield} title="MCP Configuration">
          <SettingRow label="Server Timeout" value={`${settings.mcp.server_timeout}s`} mono />
          <SettingRow label="Max Connections/Tenant" value={settings.mcp.max_connections_per_tenant} mono />
          <SettingRow label="Allowed Origins" value={
            settings.mcp.allowed_origins
              ? settings.mcp.allowed_origins.join(', ')
              : 'All (no restriction)'
          } />
        </SettingSection>

        {/* Database */}
        <SettingSection icon={Database} title="Database">
          <SettingRow label="Provider" value={settings.database.provider} />
          <SettingRow label="Active Sessions" value={settings.sessions.active} mono />
        </SettingSection>

        {/* About */}
        <SettingSection icon={SettingsIcon} title="About">
          <SettingRow label="Project" value="SageMCP" />
          <SettingRow label="Protocol" value="MCP (Model Context Protocol)" />
          <SettingRow label="License" value="MIT" />
        </SettingSection>
      </div>
    </div>
  )
}
