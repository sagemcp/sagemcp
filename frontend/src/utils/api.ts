import axios from 'axios'
import { Tenant, TenantCreate, Connector, ConnectorCreate, MCPServerInfo, OAuthProvider, OAuthCredential, OAuthConfig, MCPProcessStatus, PlatformStats, SessionInfo, PoolEntry, PoolSummary } from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth (when implemented)
api.interceptors.request.use((config) => {
  // Add auth token when available
  // const token = localStorage.getItem('auth_token')
  // if (token) {
  //   config.headers.Authorization = `Bearer ${token}`
  // }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      // window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const tenantsApi = {
  list: () => api.get<Tenant[]>('/admin/tenants'),
  get: (slug: string) => api.get<Tenant>(`/admin/tenants/${slug}`),
  create: (data: TenantCreate) => api.post<Tenant>('/admin/tenants', data),
  update: (slug: string, data: TenantCreate) => 
    api.put<Tenant>(`/admin/tenants/${slug}`, data),
  delete: (slug: string) => api.delete(`/admin/tenants/${slug}`),
}

export const connectorsApi = {
  list: (tenantSlug: string) =>
    api.get<Connector[]>(`/admin/tenants/${tenantSlug}/connectors`),
  get: (tenantSlug: string, connectorId: string) =>
    api.get<Connector>(`/admin/tenants/${tenantSlug}/connectors/${connectorId}`),
  create: (tenantSlug: string, data: ConnectorCreate) =>
    api.post<Connector>(`/admin/tenants/${tenantSlug}/connectors`, data),
  update: (tenantSlug: string, connectorId: string, data: ConnectorCreate) =>
    api.put<Connector>(`/admin/tenants/${tenantSlug}/connectors/${connectorId}`, data),
  delete: (tenantSlug: string, connectorId: string) =>
    api.delete(`/admin/tenants/${tenantSlug}/connectors/${connectorId}`),
  toggle: (tenantSlug: string, connectorId: string) =>
    api.patch<Connector>(`/admin/tenants/${tenantSlug}/connectors/${connectorId}/toggle`),
}

export interface ToolState {
  tool_name: string
  is_enabled: boolean
  description?: string
}

export interface ToolsListResponse {
  tools: ToolState[]
  summary: {
    total: number
    enabled: number
    disabled: number
  }
}

export interface BulkToolUpdate {
  tool_name: string
  is_enabled: boolean
}

export interface SyncToolsResponse {
  success: boolean
  added: string[]
  removed: string[]
  unchanged: number
  summary: string
}

export const toolsApi = {
  list: (tenantSlug: string, connectorId: string) =>
    api.get<ToolsListResponse>(`/admin/tenants/${tenantSlug}/connectors/${connectorId}/tools`),

  toggle: (tenantSlug: string, connectorId: string, toolName: string, isEnabled: boolean) =>
    api.patch<ToolState>(`/admin/tenants/${tenantSlug}/connectors/${connectorId}/tools/${toolName}`, {
      is_enabled: isEnabled
    }),

  bulkUpdate: (tenantSlug: string, connectorId: string, updates: BulkToolUpdate[]) =>
    api.post(`/admin/tenants/${tenantSlug}/connectors/${connectorId}/tools/bulk-update`, {
      updates
    }),

  enableAll: (tenantSlug: string, connectorId: string) =>
    api.post(`/admin/tenants/${tenantSlug}/connectors/${connectorId}/tools/enable-all`),

  disableAll: (tenantSlug: string, connectorId: string) =>
    api.post(`/admin/tenants/${tenantSlug}/connectors/${connectorId}/tools/disable-all`),

  sync: (tenantSlug: string, connectorId: string) =>
    api.post<SyncToolsResponse>(`/admin/tenants/${tenantSlug}/connectors/${connectorId}/tools/sync`),
}

export const mcpApi = {
  getInfo: (tenantSlug: string, connectorId: string) =>
    api.get<MCPServerInfo>(`/${tenantSlug}/connectors/${connectorId}/mcp/info`),
  sendMessage: (tenantSlug: string, connectorId: string, message: any) =>
    api.post(`/${tenantSlug}/connectors/${connectorId}/mcp`, message),
}

export const oauthApi = {
  listProviders: () => api.get<OAuthProvider[]>('/oauth/providers'),
  listCredentials: (tenantSlug: string) =>
    api.get<OAuthCredential[]>(`/oauth/${tenantSlug}/auth`),
  initiateOAuth: (tenantSlug: string, provider: string) => {
    // This should open a new window for OAuth flow
    const url = `/api/v1/oauth/${tenantSlug}/auth/${provider}`
    console.log('Opening OAuth popup for:', provider, 'URL:', url)
    const popup = window.open(url, 'oauth', 'width=600,height=700,scrollbars=yes,resizable=yes')
    console.log('OAuth popup opened:', popup)
    return popup
  },
  revokeCredential: (tenantSlug: string, provider: string) =>
    api.delete(`/oauth/${tenantSlug}/auth/${provider}`),
  // OAuth Configuration Management
  listConfigs: (tenantSlug: string) =>
    api.get<OAuthConfig[]>(`/oauth/${tenantSlug}/config`),
  createConfig: (tenantSlug: string, config: { provider: string; client_id: string; client_secret: string }) =>
    api.post<OAuthConfig>(`/oauth/${tenantSlug}/config`, config),
  deleteConfig: (tenantSlug: string, provider: string) =>
    api.delete(`/oauth/${tenantSlug}/config/${provider}`),
}

export const processApi = {
  getStatus: (connectorId: string) =>
    api.get<MCPProcessStatus | null>(`/admin/connectors/${connectorId}/process/status`),
  restart: (connectorId: string) =>
    api.post(`/admin/connectors/${connectorId}/process/restart`),
  terminate: (connectorId: string) =>
    api.delete(`/admin/connectors/${connectorId}/process`),
}

export const healthApi = {
  check: () => api.get('/health'),
}

export const settingsApi = {
  get: () => api.get('/admin/settings'),
}

export const statsApi = {
  get: () => api.get<PlatformStats>('/admin/stats'),
}

export const poolApi = {
  list: (tenantSlug?: string) => {
    const params = tenantSlug ? { tenant_slug: tenantSlug } : {}
    return api.get<PoolEntry[]>('/admin/pool', { params })
  },
  summary: () => api.get<PoolSummary>('/admin/pool/summary'),
  evict: (tenantSlug: string, connectorId: string) =>
    api.delete(`/admin/pool/${tenantSlug}/${connectorId}`),
  evictIdle: (idleSeconds = 600) =>
    api.post('/admin/pool/evict-idle', null, { params: { idle_seconds: idleSeconds } }),
}

export const sessionsApi = {
  list: (tenantSlug?: string) => {
    const params = tenantSlug ? { tenant_slug: tenantSlug } : {}
    return api.get<SessionInfo[]>('/admin/sessions', { params })
  },
  delete: (sessionId: string) => api.delete(`/admin/sessions/${sessionId}`),
}

// Legacy function exports for tests
export const fetchTenants = () => tenantsApi.list()
export const createTenant = (data: TenantCreate) => tenantsApi.create(data)
export const fetchConnectors = (tenantSlug: string) => connectorsApi.list(tenantSlug)
export const createConnector = (tenantSlug: string, data: ConnectorCreate) => connectorsApi.create(tenantSlug, data)

export default api