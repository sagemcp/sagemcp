import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '@/utils/api'

interface MCPServerDetail {
  id: string
  name: string
  display_name: string
  description: string
  source_type: string
  source_url: string
  npm_package_name: string | null
  github_repo: string | null
  latest_version: string
  runtime_type: string
  tools_count: number
  resources_count: number
  prompts_count: number
  star_count: number
  download_count: number
  requires_oauth: boolean
  oauth_providers: string[]
  author: string
  license: string
  repository_url: string
  homepage_url: string
  is_verified: boolean
  first_discovered_at: string
  last_scanned_at: string
}

interface Tenant {
  id: string
  name: string
  slug: string
}

export default function ServerDetail() {
  const { serverId } = useParams<{ serverId: string }>()
  const navigate = useNavigate()
  const [server, setServer] = useState<MCPServerDetail | null>(null)
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)
  const [installing, setInstalling] = useState(false)
  const [selectedTenant, setSelectedTenant] = useState<string>('')
  const [showInstallModal, setShowInstallModal] = useState(false)

  const loadServer = useCallback(async () => {
    try {
      setLoading(true)
      const response = await api.get(`/registry/servers/${serverId}`)
      setServer(response.data)
    } catch (error) {
      console.error('Failed to load server:', error)
    } finally {
      setLoading(false)
    }
  }, [serverId])

  const loadTenants = useCallback(async () => {
    try {
      const response = await api.get('/admin/tenants')
      setTenants(response.data)
    } catch (error) {
      console.error('Failed to load tenants:', error)
    }
  }, [])

  useEffect(() => {
    loadServer()
    loadTenants()
  }, [loadServer, loadTenants])

  const handleInstall = async () => {
    if (!selectedTenant || !server) return

    try {
      setInstalling(true)
      const response = await api.post(
        `/registry/servers/${server.id}/install`,
        {
          tenant_id: selectedTenant,
          config_overrides: {}
        }
      )

      if (response.data.success) {
        alert(`Server installed successfully! Connector ID: ${response.data.connector_id}`)
        setShowInstallModal(false)
        // Navigate to installations page
        navigate('/installations')
      } else {
        alert(`Installation failed: ${response.data.message}`)
      }
    } catch (error: any) {
      console.error('Installation failed:', error)
      alert(`Installation error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setInstalling(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!server) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Server not found</p>
        <button
          onClick={() => navigate('/marketplace')}
          className="mt-4 text-blue-600 hover:text-blue-800"
        >
          ← Back to Marketplace
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => navigate('/marketplace')}
        className="text-blue-600 hover:text-blue-800 flex items-center"
      >
        ← Back to Marketplace
      </button>

      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold">{server.display_name || server.name}</h1>
            <p className="text-gray-600 mt-2">{server.description}</p>

            <div className="flex flex-wrap gap-2 mt-4">
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                {server.runtime_type}
              </span>
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                {server.source_type}
              </span>
              {server.requires_oauth && (
                <span className="px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
                  OAuth Required
                </span>
              )}
              {server.is_verified && (
                <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                  ✓ Verified
                </span>
              )}
            </div>
          </div>

          <button
            onClick={() => setShowInstallModal(true)}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            Install Server
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-600">Stars</div>
          <div className="text-2xl font-bold mt-2">⭐ {server.star_count}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-600">Tools</div>
          <div className="text-2xl font-bold mt-2">🔧 {server.tools_count}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-600">Resources</div>
          <div className="text-2xl font-bold mt-2">📦 {server.resources_count}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-600">Prompts</div>
          <div className="text-2xl font-bold mt-2">💬 {server.prompts_count}</div>
        </div>
      </div>

      {/* Details */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Server Details</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-600">Version</dt>
            <dd className="mt-1 text-sm text-gray-900">{server.latest_version || 'N/A'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Author</dt>
            <dd className="mt-1 text-sm text-gray-900">{server.author || 'Unknown'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">License</dt>
            <dd className="mt-1 text-sm text-gray-900">{server.license || 'N/A'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-600">Runtime</dt>
            <dd className="mt-1 text-sm text-gray-900">{server.runtime_type}</dd>
          </div>
          {server.npm_package_name && (
            <div>
              <dt className="text-sm font-medium text-gray-600">NPM Package</dt>
              <dd className="mt-1 text-sm text-gray-900">{server.npm_package_name}</dd>
            </div>
          )}
          {server.github_repo && (
            <div>
              <dt className="text-sm font-medium text-gray-600">GitHub Repo</dt>
              <dd className="mt-1 text-sm text-gray-900">{server.github_repo}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Links */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Links</h2>
        <div className="space-y-2">
          {server.homepage_url && (
            <a
              href={server.homepage_url}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-blue-600 hover:text-blue-800"
            >
              🏠 Homepage →
            </a>
          )}
          {server.repository_url && (
            <a
              href={server.repository_url}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-blue-600 hover:text-blue-800"
            >
              💻 Repository →
            </a>
          )}
          <a
            href={server.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block text-blue-600 hover:text-blue-800"
          >
            📦 Source →
          </a>
        </div>
      </div>

      {/* Install Modal */}
      {showInstallModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-4">Install {server.name}</h2>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Tenant
              </label>
              <select
                value={selectedTenant}
                onChange={(e) => setSelectedTenant(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Choose a tenant...</option>
                {tenants.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name} ({tenant.slug})
                  </option>
                ))}
              </select>
            </div>

            {server.requires_oauth && (
              <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                <p className="text-sm text-yellow-800">
                  ⚠️ This server requires OAuth authentication. You'll need to configure
                  OAuth credentials after installation.
                </p>
              </div>
            )}

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowInstallModal(false)}
                disabled={installing}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={handleInstall}
                disabled={!selectedTenant || installing}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {installing ? 'Installing...' : 'Install'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
