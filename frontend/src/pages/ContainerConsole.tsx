import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import api from '@/utils/api'

interface InstallationStatus {
  connector_id: string
  name: string
  status: string
  container_status: string
  container_ip: string | null
  installed_version: string | null
  installed_at: string | null
  last_health_check: string | null
}

export default function ContainerConsole() {
  const { connectorId } = useParams<{ connectorId: string }>()
  const [searchParams] = useSearchParams()
  const tenantId = searchParams.get('tenant_id')
  const navigate = useNavigate()

  const [installation, setInstallation] = useState<InstallationStatus | null>(null)
  const [logs, setLogs] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const intervalRef = useRef<number | null>(null)

  const loadInstallation = useCallback(async () => {
    try {
      const response = await api.get(
        `/registry/installations/${connectorId}/status?tenant_id=${tenantId}`
      )
      setInstallation(response.data)
    } catch (error) {
      console.error('Failed to load installation:', error)
    }
  }, [connectorId, tenantId])

  const loadLogs = useCallback(async () => {
    try {
      setLoading(true)
      const response = await api.get(
        `/registry/installations/${connectorId}/logs?tenant_id=${tenantId}&tail=100`
      )
      setLogs(response.data.logs || 'No logs available')
    } catch (error) {
      console.error('Failed to load logs:', error)
      setLogs('Error loading logs. The logs endpoint may not be available yet.')
    } finally {
      setLoading(false)
    }
  }, [connectorId, tenantId])

  useEffect(() => {
    if (tenantId && connectorId) {
      loadInstallation()
      loadLogs()
    }
  }, [connectorId, tenantId, loadInstallation, loadLogs])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = window.setInterval(() => {
        loadLogs()
        loadInstallation()
      }, 3000) // Refresh every 3 seconds
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [autoRefresh, loadLogs, loadInstallation])

  useEffect(() => {
    // Auto-scroll to bottom when logs update
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const handleRestart = async () => {
    if (!confirm('Are you sure you want to restart this container?')) {
      return
    }

    try {
      await api.post(
        `/registry/installations/${connectorId}/restart?tenant_id=${tenantId}`
      )
      alert('Container restart initiated')
      setTimeout(() => {
        loadInstallation()
        loadLogs()
      }, 2000)
    } catch (error: any) {
      console.error('Restart failed:', error)
      alert(`Restart error: ${error.response?.data?.detail || error.message}`)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      running: 'bg-green-500/10 text-green-400',
      pending: 'bg-amber-500/10 text-amber-400',
      failed: 'bg-red-500/10 text-red-400',
      succeeded: 'bg-blue-500/10 text-blue-400',
      unknown: 'bg-theme-elevated text-theme-secondary'
    }
    return colors[status?.toLowerCase()] || 'bg-theme-elevated text-theme-secondary'
  }

  if (!tenantId) {
    return (
      <div className="text-center py-12">
        <p className="text-red-400">Error: Tenant ID is required</p>
        <button
          onClick={() => navigate('/installations')}
          className="mt-4 text-blue-400 hover:text-blue-300"
        >
          \u2190 Back to Installations
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => navigate('/installations')}
        className="text-blue-400 hover:text-blue-300 flex items-center"
      >
        \u2190 Back to Installations
      </button>

      {/* Header */}
      {installation && (
        <div className="bg-surface-elevated rounded-lg border border-theme-default p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-2">
                <h1 className="text-2xl font-bold text-theme-primary">{installation.name}</h1>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(installation.container_status)}`}>
                  {installation.container_status}
                </span>
              </div>

              <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
                <div>
                  <dt className="text-theme-secondary">Version</dt>
                  <dd className="font-medium text-theme-primary">{installation.installed_version || 'N/A'}</dd>
                </div>
                <div>
                  <dt className="text-theme-secondary">Container IP</dt>
                  <dd className="font-medium font-mono text-theme-primary">{installation.container_ip || 'N/A'}</dd>
                </div>
                <div>
                  <dt className="text-theme-secondary">Connector ID</dt>
                  <dd className="font-medium font-mono text-xs text-theme-primary">{installation.connector_id}</dd>
                </div>
                <div>
                  <dt className="text-theme-secondary">Last Check</dt>
                  <dd className="font-medium text-theme-primary">
                    {installation.last_health_check
                      ? new Date(installation.last_health_check).toLocaleTimeString()
                      : 'N/A'}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="flex space-x-2 ml-4">
              <button
                onClick={handleRestart}
                className="px-4 py-2 text-sm border border-orange-500/30 text-orange-400 rounded hover:bg-orange-500/10"
              >
                Restart
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Console */}
      <div className="bg-surface-elevated rounded-lg border border-theme-default">
        <div className="p-4 border-b border-theme-default flex items-center justify-between">
          <h2 className="text-lg font-semibold text-theme-primary">Container Logs</h2>

          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-accent bg-theme-elevated border-theme-hover"
              />
              <span className="text-sm font-medium text-theme-secondary">
                Auto-refresh
              </span>
            </label>

            <button
              onClick={loadLogs}
              disabled={loading}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-theme-elevated disabled:text-theme-muted"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        <div className="p-4 bg-zinc-950 text-green-400 font-mono text-sm overflow-auto" style={{ minHeight: '500px', maxHeight: '600px' }}>
          <pre className="whitespace-pre-wrap break-words">
            {logs || 'Loading logs...'}
            <div ref={logsEndRef} />
          </pre>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
        <p className="text-sm text-blue-400">
          \uD83D\uDCA1 <strong>Note:</strong> The container logs endpoint is part of Phase 2 implementation.
          If you see an error loading logs, the backend endpoint may need to be added.
        </p>
      </div>
    </div>
  )
}
