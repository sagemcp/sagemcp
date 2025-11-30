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
      running: 'bg-green-100 text-green-800',
      pending: 'bg-yellow-100 text-yellow-800',
      failed: 'bg-red-100 text-red-800',
      succeeded: 'bg-blue-100 text-blue-800',
      unknown: 'bg-gray-100 text-gray-800'
    }
    return colors[status?.toLowerCase()] || 'bg-gray-100 text-gray-800'
  }

  if (!tenantId) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error: Tenant ID is required</p>
        <button
          onClick={() => navigate('/installations')}
          className="mt-4 text-blue-600 hover:text-blue-800"
        >
          ← Back to Installations
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => navigate('/installations')}
        className="text-blue-600 hover:text-blue-800 flex items-center"
      >
        ← Back to Installations
      </button>

      {/* Header */}
      {installation && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-2">
                <h1 className="text-2xl font-bold">{installation.name}</h1>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(installation.container_status)}`}>
                  {installation.container_status}
                </span>
              </div>

              <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
                <div>
                  <dt className="text-gray-600">Version</dt>
                  <dd className="font-medium">{installation.installed_version || 'N/A'}</dd>
                </div>
                <div>
                  <dt className="text-gray-600">Container IP</dt>
                  <dd className="font-medium font-mono">{installation.container_ip || 'N/A'}</dd>
                </div>
                <div>
                  <dt className="text-gray-600">Connector ID</dt>
                  <dd className="font-medium font-mono text-xs">{installation.connector_id}</dd>
                </div>
                <div>
                  <dt className="text-gray-600">Last Check</dt>
                  <dd className="font-medium">
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
                className="px-4 py-2 text-sm border border-orange-300 text-orange-600 rounded hover:bg-orange-50"
              >
                Restart
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Console */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Container Logs</h2>

          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Auto-refresh
              </span>
            </label>

            <button
              onClick={loadLogs}
              disabled={loading}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        <div className="p-4 bg-gray-900 text-green-400 font-mono text-sm overflow-auto" style={{ minHeight: '500px', maxHeight: '600px' }}>
          <pre className="whitespace-pre-wrap break-words">
            {logs || 'Loading logs...'}
            <div ref={logsEndRef} />
          </pre>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          💡 <strong>Note:</strong> The container logs endpoint is part of Phase 2 implementation.
          If you see an error loading logs, the backend endpoint may need to be added.
        </p>
      </div>
    </div>
  )
}
