import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Building2,
  Plug,
  Activity,
  Plus,
  MoreVertical,
  Edit,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Info,
  X,
  Wrench,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { toast } from 'sonner'
import { tenantsApi, connectorsApi } from '@/utils/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { EndpointDisplay } from '@/components/sage/endpoint-display'
import { CodeBlock } from '@/components/sage/code-block'
import { EmptyState } from '@/components/sage/empty-state'
import { StatusDot } from '@/components/sage/status-dot'
import ConnectorModal from '@/components/ConnectorModal'
import ExternalMCPModal from '@/components/ExternalMCPModal'
import ProcessStatus from '@/components/ProcessStatus'
import ConnectorEditModal from '@/components/ConnectorEditModal'
import OAuthManager from '@/components/OAuthManager'
import ToolManagement from '@/components/ToolManagement'
import TenantEditModal from '@/components/TenantEditModal'
import { useSessions, useTerminateSession } from '@/hooks/use-sessions'

const ConnectionInfoDialog = ({
  open,
  onOpenChange,
  connector,
  tenantSlug
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  connector: any
  tenantSlug: string
}) => {
  const mcpHttpUrl = `${window.location.protocol}//${window.location.host}/api/v1/${tenantSlug}/connectors/${connector.id}/mcp`

  const claudeConfig = JSON.stringify({
    mcpServers: {
      [connector.name]: {
        command: 'npx',
        args: ['-y', 'mcp-remote', mcpHttpUrl]
      }
    }
  }, null, 2)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Connection Info</DialogTitle>
          <p className="text-sm text-zinc-400 mt-1">{connector.name}</p>
        </DialogHeader>
        <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">MCP Endpoint</label>
            <EndpointDisplay url={mcpHttpUrl} protocol="HTTP" />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Claude Desktop Config</label>
            <CodeBlock code={claudeConfig} language="json" />
            <p className="text-xs text-zinc-500 mt-2">
              Add to: <code className="text-zinc-400">~/Library/Application Support/Claude/claude_desktop_config.json</code>
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const DeleteConfirmDialog = ({
  open,
  onOpenChange,
  onConfirm,
  connectorName,
  isDeleting
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  connectorName: string
  isDeleting: boolean
}) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent onClose={() => onOpenChange(false)} className="max-w-md">
      <div className="px-6 py-4">
        <h3 className="text-lg font-semibold text-zinc-100 mb-2">Delete Connector</h3>
        <p className="text-sm text-zinc-400 mb-6">
          Are you sure you want to delete <span className="font-medium text-zinc-200">"{connectorName}"</span>? This action cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isDeleting}>Cancel</Button>
          <Button variant="destructive" onClick={onConfirm} disabled={isDeleting}>
            {isDeleting ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
)

const ConnectorCard = ({ connector, tenantSlug }: { connector: any; tenantSlug: string }) => {
  const [showMenu, setShowMenu] = useState(false)
  const [showConnectionInfo, setShowConnectionInfo] = useState(false)
  const [showTools, setShowTools] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const queryClient = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: () => connectorsApi.delete(tenantSlug, connector.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors', tenantSlug] })
      toast.success('Connector deleted successfully')
      setShowDeleteDialog(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete connector')
    }
  })

  const toggleMutation = useMutation({
    mutationFn: () => connectorsApi.toggle(tenantSlug, connector.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors', tenantSlug] })
      toast.success(connector.is_enabled ? 'Connector disabled' : 'Connector enabled')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to toggle connector')
    }
  })

  return (
    <>
      <DeleteConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onConfirm={() => deleteMutation.mutate()}
        connectorName={connector.name}
        isDeleting={deleteMutation.isPending}
      />
      <ConnectionInfoDialog
        open={showConnectionInfo}
        onOpenChange={setShowConnectionInfo}
        connector={connector}
        tenantSlug={tenantSlug}
      />
      <ConnectorEditModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        connector={connector}
        tenantSlug={tenantSlug}
      />

      <div className="rounded-lg border border-zinc-800 bg-surface-elevated self-start">
        <div className="p-4">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-zinc-100">{connector.name}</h4>
              <p className="text-xs text-zinc-500 capitalize">{connector.connector_type.replace('_', ' ')}</p>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <Badge variant={connector.is_enabled ? 'healthy' : 'idle'}>
                {connector.is_enabled ? 'Enabled' : 'Disabled'}
              </Badge>
              <button
                onClick={() => toggleMutation.mutate()}
                disabled={toggleMutation.isPending}
                className="p-1 rounded hover:bg-zinc-800 disabled:opacity-50 transition-colors"
              >
                {connector.is_enabled ? (
                  <ToggleRight className="h-5 w-5 text-success-400" />
                ) : (
                  <ToggleLeft className="h-5 w-5 text-zinc-500" />
                )}
              </button>
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="p-1 rounded hover:bg-zinc-800 text-zinc-500 transition-colors"
                >
                  <MoreVertical className="h-4 w-4" />
                </button>
                {showMenu && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
                    <div className="absolute right-0 mt-1 w-40 rounded-md bg-zinc-800 border border-zinc-700 py-1 z-20 shadow-elevated">
                      <button
                        onClick={() => { setShowEditModal(true); setShowMenu(false) }}
                        className="flex items-center w-full px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
                      >
                        <Edit className="h-3.5 w-3.5 mr-2" />
                        Edit
                      </button>
                      <button
                        onClick={() => { setShowDeleteDialog(true); setShowMenu(false) }}
                        className="flex items-center w-full px-3 py-2 text-sm text-error-400 hover:bg-zinc-700"
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-2" />
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {connector.description && (
            <p className="text-sm text-zinc-400 mb-3">{connector.description}</p>
          )}

          {/* Process Status */}
          <ProcessStatus
            connectorId={connector.id}
            runtimeType={connector.runtime_type}
            showControls={true}
          />

          {/* Actions */}
          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-zinc-800">
            <button
              onClick={() => setShowConnectionInfo(true)}
              className="inline-flex items-center text-xs text-accent hover:text-accent-hover font-medium transition-colors"
            >
              <Info className="h-3.5 w-3.5 mr-1" />
              Connection Info
            </button>
            <button
              onClick={() => setShowTools(!showTools)}
              className="inline-flex items-center text-xs text-zinc-400 hover:text-zinc-200 font-medium transition-colors"
            >
              <Wrench className="h-3.5 w-3.5 mr-1" />
              Tools
              {showTools ? <ChevronUp className="h-3 w-3 ml-0.5" /> : <ChevronDown className="h-3 w-3 ml-0.5" />}
            </button>
          </div>
        </div>

        {/* Expandable tools */}
        {showTools && (
          <div className="border-t border-zinc-800 px-4 py-4 bg-zinc-900/50">
            <ToolManagement
              tenantSlug={tenantSlug}
              connectorId={connector.id}
              connectorName={connector.name}
            />
          </div>
        )}
      </div>
    </>
  )
}

function SessionsTab({ tenantSlug }: { tenantSlug: string }) {
  const { data: sessions = [], isLoading } = useSessions(tenantSlug)
  const terminateMutation = useTerminateSession()

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No active sessions"
        description="Sessions will appear here when clients connect via MCP."
      />
    )
  }

  return (
    <div className="rounded-lg border border-zinc-800 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/50">
            <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Session ID</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Connector</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Version</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Age</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">Idle</th>
            <th className="text-right px-4 py-2.5"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {sessions.map((session) => (
            <tr key={session.session_id} className="hover:bg-zinc-800/50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-zinc-400">{session.session_id.slice(0, 12)}...</td>
              <td className="px-4 py-3 text-zinc-300">{session.connector_id}</td>
              <td className="px-4 py-3">
                {session.negotiated_version ? (
                  <Badge variant="accent">{session.negotiated_version}</Badge>
                ) : (
                  <span className="text-zinc-500">—</span>
                )}
              </td>
              <td className="px-4 py-3 text-zinc-400">{Math.round(session.created_at)}s</td>
              <td className="px-4 py-3 text-zinc-400">{Math.round(session.last_access)}s</td>
              <td className="px-4 py-3 text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => terminateMutation.mutate(session.session_id)}
                  disabled={terminateMutation.isPending}
                  className="text-error-400 hover:text-error-300"
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function TenantDetail() {
  const { slug } = useParams<{ slug: string }>()
  const [activeTab, setActiveTab] = useState('overview')
  const [showConnectorModal, setShowConnectorModal] = useState(false)
  const [showExternalMCPModal, setShowExternalMCPModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)

  const { data: tenant, isLoading: tenantLoading } = useQuery({
    queryKey: ['tenant', slug],
    queryFn: () => tenantsApi.get(slug!).then(res => res.data),
    enabled: !!slug
  })

  const { data: connectors = [] } = useQuery({
    queryKey: ['connectors', slug],
    queryFn: () => connectorsApi.list(slug!).then(res => res.data),
    enabled: !!slug
  })

  if (tenantLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-6 w-48" />
        </div>
        <Skeleton className="h-4 w-96" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (!tenant) {
    return (
      <EmptyState
        icon={Building2}
        title="Tenant not found"
        description="The tenant you're looking for doesn't exist."
        action={{ label: 'Back to Tenants', onClick: () => window.history.back() }}
      />
    )
  }

  const mcpEndpoint = `${window.location.protocol}//${window.location.host}/api/v1/${tenant.slug}`

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/tenants" className="p-2 rounded-md hover:bg-zinc-800 transition-colors">
            <ArrowLeft className="h-5 w-5 text-zinc-400" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-zinc-100">{tenant.name}</h1>
              <Badge variant={tenant.is_active ? 'healthy' : 'idle'}>
                {tenant.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            <p className="text-sm text-zinc-500 font-mono mt-0.5">{tenant.slug}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setShowEditModal(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button asChild>
            <Link to={`/mcp-test?tenant=${tenant.slug}`}>
              <Activity className="h-4 w-4 mr-2" />
              Test MCP
            </Link>
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="connectors">Connectors ({connectors.length})</TabsTrigger>
          <TabsTrigger value="tools">Tool Policy</TabsTrigger>
          <TabsTrigger value="sessions">Sessions</TabsTrigger>
          <TabsTrigger value="oauth">OAuth</TabsTrigger>
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview">
          <div className="space-y-6">
            {/* Endpoint */}
            <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-6">
              <h3 className="text-sm font-medium text-zinc-200 mb-3">MCP Endpoint</h3>
              <EndpointDisplay url={mcpEndpoint} protocol="Streamable HTTP" />
              {tenant.description && (
                <p className="text-sm text-zinc-400 mt-4">{tenant.description}</p>
              )}
              {tenant.contact_email && (
                <p className="text-xs text-zinc-500 mt-2">Contact: {tenant.contact_email}</p>
              )}
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-400">Total Connectors</p>
                    <p className="text-2xl font-bold font-mono text-zinc-100 mt-1">{connectors.length}</p>
                  </div>
                  <Plug className="h-8 w-8 text-accent/60" />
                </div>
              </div>
              <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-400">Active</p>
                    <p className="text-2xl font-bold font-mono text-zinc-100 mt-1">
                      {connectors.filter((c: any) => c.is_enabled).length}
                    </p>
                  </div>
                  <StatusDot variant="healthy" size="lg" />
                </div>
              </div>
              <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-400">Types</p>
                    <p className="text-2xl font-bold font-mono text-zinc-100 mt-1">
                      {new Set(connectors.map((c: any) => c.connector_type)).size}
                    </p>
                  </div>
                  <Building2 className="h-8 w-8 text-accent/60" />
                </div>
              </div>
            </div>

            {/* Claude Desktop config */}
            {connectors.length > 0 && (
              <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-6">
                <h3 className="text-sm font-medium text-zinc-200 mb-3">Claude Desktop Config</h3>
                <CodeBlock
                  language="json"
                  code={JSON.stringify({
                    mcpServers: Object.fromEntries(
                      connectors.map((c: any) => [
                        c.name,
                        {
                          command: 'npx',
                          args: ['-y', 'mcp-remote', `${window.location.protocol}//${window.location.host}/api/v1/${tenant.slug}/connectors/${c.id}/mcp`]
                        }
                      ])
                    )
                  }, null, 2)}
                />
              </div>
            )}
          </div>
        </TabsContent>

        {/* Connectors */}
        <TabsContent value="connectors">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-zinc-200">Connectors</h3>
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={() => setShowConnectorModal(true)}>
                  <Plus className="h-3.5 w-3.5 mr-1.5" />
                  Native
                </Button>
                <Button size="sm" onClick={() => setShowExternalMCPModal(true)}>
                  <Plus className="h-3.5 w-3.5 mr-1.5" />
                  External MCP
                </Button>
              </div>
            </div>

            {connectors.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 items-start">
                {connectors.map((connector: any) => (
                  <ConnectorCard key={connector.id} connector={connector} tenantSlug={slug!} />
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Plug}
                title="No connectors configured"
                description="Add your first connector to get started"
                action={{ label: 'Add Connector', onClick: () => setShowConnectorModal(true) }}
              />
            )}
          </div>
        </TabsContent>

        {/* Tool Policy */}
        <TabsContent value="tools">
          <div className="space-y-6">
            {connectors.length > 0 ? (
              connectors.map((connector: any) => (
                <div key={connector.id} className="rounded-lg border border-zinc-800 bg-surface-elevated p-6">
                  <ToolManagement
                    tenantSlug={slug!}
                    connectorId={connector.id}
                    connectorName={connector.name}
                  />
                </div>
              ))
            ) : (
              <EmptyState
                icon={Wrench}
                title="No tools to manage"
                description="Add connectors first, then manage their tool policies here."
              />
            )}
          </div>
        </TabsContent>

        {/* Sessions */}
        <TabsContent value="sessions">
          <SessionsTab tenantSlug={slug!} />
        </TabsContent>

        {/* OAuth */}
        <TabsContent value="oauth">
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-zinc-200">OAuth Configuration</h3>
              <p className="text-xs text-zinc-500 mt-1">Configure OAuth providers for this tenant</p>
            </div>
            <OAuthManager tenantSlug={slug!} />
          </div>
        </TabsContent>
      </Tabs>

      {/* Modals */}
      <ConnectorModal
        isOpen={showConnectorModal}
        onClose={() => setShowConnectorModal(false)}
        preselectedTenant={tenant?.slug}
      />
      <ExternalMCPModal
        isOpen={showExternalMCPModal}
        onClose={() => setShowExternalMCPModal(false)}
        preselectedTenant={tenant?.slug}
      />
      {tenant && (
        <TenantEditModal
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          tenant={tenant}
        />
      )}
    </div>
  )
}
