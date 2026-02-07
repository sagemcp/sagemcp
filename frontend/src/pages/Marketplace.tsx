import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '@/utils/api'

interface MCPServer {
  id: string
  name: string
  display_name: string
  description: string
  source_type: string
  runtime_type: string
  tools_count: number
  star_count: number
  requires_oauth: boolean
  author: string
  license: string
  homepage_url: string
  repository_url: string
}

interface RegistryStats {
  total_servers: number
  by_runtime: Record<string, number>
  by_source: Record<string, number>
  requires_oauth_count: number
  verified_count: number
}

export default function Marketplace() {
  const [servers, setServers] = useState<MCPServer[]>([])
  const [stats, setStats] = useState<RegistryStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [runtimeFilter, setRuntimeFilter] = useState<string>('all')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [oauthFilter, setOauthFilter] = useState<string>('all')
  const navigate = useNavigate()

  const loadStats = useCallback(async () => {
    try {
      const response = await api.get('/registry/stats')
      setStats(response.data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }, [])

  const loadServers = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()

      if (searchQuery) params.append('search', searchQuery)
      if (runtimeFilter !== 'all') params.append('runtime_type', runtimeFilter)
      if (sourceFilter !== 'all') params.append('source_type', sourceFilter)
      if (oauthFilter === 'yes') params.append('requires_oauth', 'true')
      if (oauthFilter === 'no') params.append('requires_oauth', 'false')
      params.append('limit', '50')

      const response = await api.get(`/registry/servers?${params}`)
      setServers(response.data)
    } catch (error) {
      console.error('Failed to load servers:', error)
    } finally {
      setLoading(false)
    }
  }, [searchQuery, runtimeFilter, sourceFilter, oauthFilter])

  useEffect(() => {
    loadStats()
    loadServers()
  }, [loadStats, loadServers])

  const getRuntimeIcon = (runtime: string) => {
    const icons: Record<string, string> = {
      nodejs: '\u2B22',
      python: '\uD83D\uDC0D',
      go: '\uD83D\uDD37',
      rust: '\uD83E\uDD80',
      binary: '\u2699\uFE0F'
    }
    return icons[runtime.toLowerCase()] || '\uD83D\uDCE6'
  }

  const getRuntimeColor = (runtime: string) => {
    const colors: Record<string, string> = {
      nodejs: 'bg-green-500/10 text-green-400',
      python: 'bg-blue-500/10 text-blue-400',
      go: 'bg-cyan-500/10 text-cyan-400',
      rust: 'bg-orange-500/10 text-orange-400',
      binary: 'bg-zinc-700 text-zinc-300'
    }
    return colors[runtime.toLowerCase()] || 'bg-zinc-700 text-zinc-300'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">MCP Server Marketplace</h1>
        <p className="text-zinc-400 mt-2">
          Discover and install MCP servers from NPM and GitHub
        </p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-surface-elevated rounded-lg border border-zinc-800 p-6">
            <div className="text-sm font-medium text-zinc-400">Total Servers</div>
            <div className="text-3xl font-bold mt-2 text-zinc-100">{stats.total_servers}</div>
          </div>
          <div className="bg-surface-elevated rounded-lg border border-zinc-800 p-6">
            <div className="text-sm font-medium text-zinc-400">Node.js</div>
            <div className="text-3xl font-bold mt-2 text-zinc-100">{stats.by_runtime.nodejs || 0}</div>
          </div>
          <div className="bg-surface-elevated rounded-lg border border-zinc-800 p-6">
            <div className="text-sm font-medium text-zinc-400">Python</div>
            <div className="text-3xl font-bold mt-2 text-zinc-100">{stats.by_runtime.python || 0}</div>
          </div>
          <div className="bg-surface-elevated rounded-lg border border-zinc-800 p-6">
            <div className="text-sm font-medium text-zinc-400">OAuth Required</div>
            <div className="text-3xl font-bold mt-2 text-zinc-100">{stats.requires_oauth_count}</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-surface-elevated rounded-lg border border-zinc-800 p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Search
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search servers..."
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          {/* Runtime Filter */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Runtime
            </label>
            <select
              value={runtimeFilter}
              onChange={(e) => setRuntimeFilter(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-zinc-100 focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="all">All Runtimes</option>
              <option value="nodejs">Node.js</option>
              <option value="python">Python</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="binary">Binary</option>
            </select>
          </div>

          {/* Source Filter */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Source
            </label>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-zinc-100 focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="all">All Sources</option>
              <option value="npm">NPM</option>
              <option value="github">GitHub</option>
            </select>
          </div>

          {/* OAuth Filter */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              OAuth
            </label>
            <select
              value={oauthFilter}
              onChange={(e) => setOauthFilter(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-zinc-100 focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="all">All</option>
              <option value="yes">Required</option>
              <option value="no">Not Required</option>
            </select>
          </div>
        </div>
      </div>

      {/* Server List */}
      <div className="bg-surface-elevated rounded-lg border border-zinc-800">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4 text-zinc-100">
            Available Servers ({servers.length})
          </h2>

          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
              <p className="mt-2 text-zinc-400">Loading servers...</p>
            </div>
          ) : servers.length === 0 ? (
            <div className="text-center py-12 text-zinc-500">
              No servers found matching your filters
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {servers.map((server) => (
                <div
                  key={server.id}
                  className="border border-zinc-800 rounded-lg p-4 hover:border-zinc-600 transition-colors cursor-pointer bg-zinc-900"
                  onClick={() => navigate(`/marketplace/${server.id}`)}
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-2xl">{getRuntimeIcon(server.runtime_type)}</span>
                      <div>
                        <h3 className="font-semibold text-lg text-zinc-100">{server.display_name || server.name}</h3>
                        <p className="text-xs text-zinc-500">by {server.author || 'Unknown'}</p>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-sm text-zinc-400 mb-3 line-clamp-2">
                    {server.description || 'No description available'}
                  </p>

                  {/* Badges */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getRuntimeColor(server.runtime_type)}`}>
                      {server.runtime_type}
                    </span>
                    <span className="px-2 py-1 rounded text-xs font-medium bg-purple-500/10 text-purple-400">
                      {server.source_type}
                    </span>
                    {server.requires_oauth && (
                      <span className="px-2 py-1 rounded text-xs font-medium bg-amber-500/10 text-amber-400">
                        OAuth
                      </span>
                    )}
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between text-sm text-zinc-500 pt-3 border-t border-zinc-800">
                    <div className="flex items-center space-x-3">
                      <span>\u2B50 {server.star_count}</span>
                      <span>\uD83D\uDD27 {server.tools_count} tools</span>
                    </div>
                    <button className="text-blue-400 hover:text-blue-300 font-medium">
                      Details \u2192
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
