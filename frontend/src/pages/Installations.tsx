import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '@/utils/api'

interface Installation {
  connector_id: string
  name: string
  status: string
  container_status: string
  container_ip: string | null
  installed_version: string | null
  installed_at: string | null
  last_health_check: string | null
}

interface Tenant {
  id: string
  name: string
  slug: string
}

export default function Installations() {
  const [installations, setInstallations] = useState<Record<string, Installation[]>>({})
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [selectedTenant, setSelectedTenant] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [uninstalling, setUninstalling] = useState<string | null>(null)
  const navigate = useNavigate()

  const loadTenants = useCallback(async () => {
    try {
      const response = await api.get('/admin/tenants')
      setTenants(response.data)
    } catch (error) {
      console.error('Failed to load tenants:', error)
    }
  }, [])

  const loadInstallations = useCallback(async () => {
    try {
      setLoading(true)
      const installationsByTenant: Record<string, Installation[]> = {}

      const tenantsToLoad = selectedTenant === 'all'
        ? tenants
        : tenants.filter(t => t.id === selectedTenant)

      for (const tenant of tenantsToLoad) {
        try {
          // Get connectors for tenant
          const connectorsResponse = await api.get(`/admin/tenants/${tenant.slug}/connectors`)
          const connectors = connectorsResponse.data

          // Get installation status for each connector
          const installationPromises = connectors.map(async (connector: any) => {
            try {
              const statusResponse = await api.get(
                `/registry/installations/${connector.id}/status?tenant_id=${tenant.id}`
              )
              return statusResponse.data
            } catch (error) {
              // Connector might not be from registry
              return null
            }
          })

          const installationsData = await Promise.all(installationPromises)
          const validInstallations = installationsData.filter((i): i is Installation => i !== null)

          if (validInstallations.length > 0) {
            installationsByTenant[tenant.id] = validInstallations
          }
        } catch (error) {
          console.error(`Failed to load installations for tenant ${tenant.name}:`, error)
        }
      }

      setInstallations(installationsByTenant)
    } catch (error) {
      console.error('Failed to load installations:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedTenant, tenants])

  useEffect(() => {
    loadTenants()
  }, [loadTenants])

  useEffect(() => {
    if (tenants.length > 0) {
      loadInstallations()
    }
  }, [tenants, loadInstallations])

  const handleUninstall = async (connectorId: string, tenantId: string) => {
    if (!confirm('Are you sure you want to uninstall this server?')) {
      return
    }

    try {
      setUninstalling(connectorId)
      await api.delete(
        `/registry/installations/${connectorId}?tenant_id=${tenantId}`
      )
      alert('Server uninstalled successfully')
      loadInstallations()
    } catch (error: any) {
      console.error('Uninstallation failed:', error)
      alert(`Uninstallation error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setUninstalling(null)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      running: 'bg-green-500/10 text-green-400',
      pending: 'bg-amber-500/10 text-amber-400',
      failed: 'bg-red-500/10 text-red-400',
      succeeded: 'bg-blue-500/10 text-blue-400',
      unknown: 'bg-zinc-700 text-zinc-300'
    }
    return colors[status.toLowerCase()] || 'bg-zinc-700 text-zinc-300'
  }

  const totalInstallations = Object.values(installations).reduce(
    (sum, items) => sum + items.length,
    0
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-100">MCP Server Installations</h1>
          <p className="text-zinc-400 mt-2">
            Manage installed MCP servers across all tenants
          </p>
        </div>
        <button
          onClick={() => navigate('/marketplace')}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Install Server
        </button>
      </div>

      {/* Filters */}
      <div className="bg-surface-elevated rounded-lg border border-zinc-800 p-6">
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-zinc-300">
            Filter by Tenant:
          </label>
          <select
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
            className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-zinc-100 focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="all">All Tenants ({totalInstallations} installations)</option>
            {tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name} ({installations[tenant.id]?.length || 0})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Installations List */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
          <p className="mt-2 text-zinc-400">Loading installations...</p>
        </div>
      ) : totalInstallations === 0 ? (
        <div className="bg-surface-elevated rounded-lg border border-zinc-800 p-12 text-center">
          <p className="text-zinc-400 mb-4">No installations found</p>
          <button
            onClick={() => navigate('/marketplace')}
            className="text-blue-400 hover:text-blue-300 font-medium"
          >
            Browse Marketplace \u2192
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(installations).map(([tenantId, tenantInstallations]) => {
            const tenant = tenants.find(t => t.id === tenantId)
            if (!tenant || tenantInstallations.length === 0) return null

            return (
              <div key={tenantId} className="bg-surface-elevated rounded-lg border border-zinc-800">
                <div className="p-6 border-b border-zinc-800">
                  <h2 className="text-xl font-semibold text-zinc-100">{tenant.name}</h2>
                  <p className="text-sm text-zinc-400">
                    {tenantInstallations.length} server(s) installed
                  </p>
                </div>

                <div className="divide-y divide-zinc-800">
                  {tenantInstallations.map((installation) => (
                    <div key={installation.connector_id} className="p-6 hover:bg-zinc-800/50">
                      <div className="flex items-start justify-between">
                        {/* Left side - Details */}
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="text-lg font-semibold text-zinc-100">{installation.name}</h3>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(installation.container_status)}`}>
                              {installation.container_status}
                            </span>
                          </div>

                          <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
                            <div>
                              <dt className="text-zinc-400">Version</dt>
                              <dd className="font-medium text-zinc-200">{installation.installed_version || 'N/A'}</dd>
                            </div>
                            <div>
                              <dt className="text-zinc-400">Container IP</dt>
                              <dd className="font-medium font-mono text-zinc-200">{installation.container_ip || 'N/A'}</dd>
                            </div>
                            <div>
                              <dt className="text-zinc-400">Installed</dt>
                              <dd className="font-medium text-zinc-200">
                                {installation.installed_at
                                  ? new Date(installation.installed_at).toLocaleDateString()
                                  : 'N/A'}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-zinc-400">Last Check</dt>
                              <dd className="font-medium text-zinc-200">
                                {installation.last_health_check
                                  ? new Date(installation.last_health_check).toLocaleTimeString()
                                  : 'N/A'}
                              </dd>
                            </div>
                          </dl>
                        </div>

                        {/* Right side - Actions */}
                        <div className="flex space-x-2 ml-4">
                          <button
                            onClick={() => navigate(`/installations/${installation.connector_id}/console?tenant_id=${tenantId}`)}
                            className="px-3 py-2 text-sm border border-zinc-700 rounded hover:bg-zinc-800 text-zinc-300"
                          >
                            Console
                          </button>
                          <button
                            onClick={() => handleUninstall(installation.connector_id, tenantId)}
                            disabled={uninstalling === installation.connector_id}
                            className="px-3 py-2 text-sm text-red-400 border border-red-500/30 rounded hover:bg-red-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {uninstalling === installation.connector_id ? 'Uninstalling...' : 'Uninstall'}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
