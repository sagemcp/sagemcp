export interface Tenant {
  id: string
  slug: string
  name: string
  description?: string
  is_active: boolean
  contact_email?: string
  created_at?: string
  updated_at?: string
}

export interface TenantCreate {
  slug: string
  name: string
  description?: string
  contact_email?: string
  is_active?: boolean
}

export interface Connector {
  id: string
  connector_type: ConnectorType
  name: string
  description?: string
  is_enabled: boolean
  configuration?: any
  tenant_id: string
  created_at?: string
  updated_at?: string
  // Runtime configuration for external MCP servers
  runtime_type: ConnectorRuntimeType
  runtime_command?: string
  runtime_env?: Record<string, string>
  package_path?: string
}

export interface ConnectorCreate {
  connector_type: ConnectorType
  name: string
  description?: string
  configuration?: any
  // Runtime configuration for external MCP servers
  runtime_type?: ConnectorRuntimeType
  runtime_command?: string
  runtime_env?: Record<string, string>
  package_path?: string
}

export enum ConnectorType {
  GITHUB = 'github',
  GITLAB = 'gitlab',
  GOOGLE_DOCS = 'google_docs',
  NOTION = 'notion',
  CONFLUENCE = 'confluence',
  JIRA = 'jira',
  LINEAR = 'linear',
  SLACK = 'slack',
  TEAMS = 'teams',
  DISCORD = 'discord',
  ZOOM = 'zoom',
  CUSTOM = 'custom'  // For external MCP servers
}

export enum ConnectorRuntimeType {
  NATIVE = 'native',
  EXTERNAL_PYTHON = 'external_python',
  EXTERNAL_NODEJS = 'external_nodejs',
  EXTERNAL_GO = 'external_go',
  EXTERNAL_CUSTOM = 'external_custom'
}

export enum ProcessStatus {
  STARTING = 'starting',
  RUNNING = 'running',
  STOPPED = 'stopped',
  ERROR = 'error',
  RESTARTING = 'restarting'
}

export interface MCPProcessStatus {
  connector_id: string
  tenant_id: string
  pid?: number
  runtime_type: string
  status: ProcessStatus
  started_at: string
  last_health_check?: string
  error_message?: string
  restart_count: number
}

export interface MCPServerInfo {
  tenant: string
  connector_id: string
  connector_name: string
  connector_type: string
  server_name: string
  server_version: string
  protocol_version: string
  capabilities: {
    tools?: { listChanged?: boolean }
    resources?: { subscribe?: boolean; listChanged?: boolean }
    prompts?: { listChanged?: boolean }
  }
}

export interface APIResponse<T> {
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface OAuthProvider {
  id: string
  name: string
  scopes: string[]
  configured: boolean
  auth_url: string
}

export interface OAuthCredential {
  id: string
  provider: string
  provider_user_id: string
  provider_username?: string
  token_type: string
  scopes?: string
  is_active: boolean
  expires_at?: string
  created_at: string
}

export interface OAuthConfig {
  id: string
  provider: string
  client_id: string
  is_active: boolean
  created_at: string
}

export interface OAuthConfigCreate {
  provider: string
  client_id: string
  client_secret: string
}

export interface SessionInfo {
  session_id: string
  tenant_slug: string
  connector_id: string
  created_at: number
  last_access: number
  negotiated_version: string | null
}

export interface PlatformStats {
  tenants: number
  connectors: number
  active_instances: number
  active_sessions: number
  pool_hits: number
  pool_misses: number
  tool_calls_today: number
  timestamp: string
}

export interface PoolEntry {
  key: string
  tenant_slug: string
  connector_id: string
  created_at: number
  last_access: number
  hit_count: number
  ttl_remaining: number
  status: 'healthy' | 'expiring' | 'expired'
}

export interface PoolSummary {
  total: number
  max_size: number
  ttl_seconds: number
  hits: number
  misses: number
  hit_rate: number
  by_tenant: Record<string, number>
  by_status: { healthy: number; expiring: number; expired: number }
  memory_estimate_kb: number
}