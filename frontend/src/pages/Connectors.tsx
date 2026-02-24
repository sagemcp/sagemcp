import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Search,
  Filter,
  Plus,
  Settings,
  ToggleLeft,
  ToggleRight,
  MoreVertical,
  Edit,
  Trash2
} from 'lucide-react'
import { tenantsApi, connectorsApi } from '@/utils/api'
import { ConnectorType } from '@/types'
import { cn } from '@/utils/cn'
import ConnectorModal from '@/components/ConnectorModal'
import {
  GitHubLogo, SlackLogo, GoogleDocsLogo, JiraLogo, NotionLogo, ZoomLogo,
  GitLabLogo, BitbucketLogo, GoogleSheetsLogo, GmailLogo, GoogleSlidesLogo,
  ConfluenceLogo, LinearLogo, TeamsLogo, DiscordLogo, OutlookLogo,
  ExcelLogo, PowerPointLogo, CopilotLogo, ClaudeCodeLogo, CodexLogo,
  CursorLogo, WindsurfLogo,
} from '@/components/icons/BrandLogos'

const ConnectorIcon = ({ type }: { type: ConnectorType }) => {
  const icons: Record<string, React.ComponentType<{ className?: string }>> = {
    [ConnectorType.GITHUB]: GitHubLogo,
    [ConnectorType.GITLAB]: GitLabLogo,
    [ConnectorType.BITBUCKET]: BitbucketLogo,
    [ConnectorType.SLACK]: SlackLogo,
    [ConnectorType.GOOGLE_DOCS]: GoogleDocsLogo,
    [ConnectorType.GOOGLE_SHEETS]: GoogleSheetsLogo,
    [ConnectorType.GMAIL]: GmailLogo,
    [ConnectorType.GOOGLE_SLIDES]: GoogleSlidesLogo,
    [ConnectorType.JIRA]: JiraLogo,
    [ConnectorType.NOTION]: NotionLogo,
    [ConnectorType.ZOOM]: ZoomLogo,
    [ConnectorType.CONFLUENCE]: ConfluenceLogo,
    [ConnectorType.LINEAR]: LinearLogo,
    [ConnectorType.TEAMS]: TeamsLogo,
    [ConnectorType.DISCORD]: DiscordLogo,
    [ConnectorType.OUTLOOK]: OutlookLogo,
    [ConnectorType.EXCEL]: ExcelLogo,
    [ConnectorType.POWERPOINT]: PowerPointLogo,
    [ConnectorType.COPILOT]: CopilotLogo,
    [ConnectorType.CLAUDE_CODE]: ClaudeCodeLogo,
    [ConnectorType.CODEX]: CodexLogo,
    [ConnectorType.CURSOR]: CursorLogo,
    [ConnectorType.WINDSURF]: WindsurfLogo,
  }

  const Icon = icons[type] || Settings
  return <Icon className="h-5 w-5" />
}

const ConnectorCard = ({ 
  connector, 
  tenant 
}: { 
  connector: any
  tenant: string 
}) => {
  const [showMenu, setShowMenu] = useState(false)
  const queryClient = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: () => connectorsApi.delete(connector.tenantSlug, connector.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['all-connectors'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      toast.success('Connector deleted successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete connector')
    }
  })

  const toggleMutation = useMutation({
    mutationFn: () => connectorsApi.toggle(connector.tenantSlug, connector.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['all-connectors'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      toast.success(connector.is_enabled ? 'Connector disabled' : 'Connector enabled')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to toggle connector')
    }
  })

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete connector "${connector.name}"?`)) {
      deleteMutation.mutate()
    }
    setShowMenu(false)
  }
  return (
    <div className="card">
      <div className="card-content">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-primary-50 rounded-lg">
              <ConnectorIcon type={connector.connector_type} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900">{connector.name}</h3>
              <p className="text-sm text-gray-600 capitalize">{connector.connector_type}</p>
              {connector.description && (
                <p className="text-sm text-gray-500 mt-1">{connector.description}</p>
              )}
              
              <div className="flex items-center space-x-4 mt-3">
                <span className="text-xs text-gray-500">Tenant: {tenant}</span>
                <span className="text-xs text-gray-500">
                  Created {new Date(connector.created_at || '').toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className={cn(
              'status-badge',
              connector.is_enabled ? 'status-active' : 'status-inactive'
            )}>
              {connector.is_enabled ? 'Enabled' : 'Disabled'}
            </span>
            <div className="flex items-center space-x-2">
              <button 
                onClick={() => toggleMutation.mutate()}
                disabled={toggleMutation.isPending}
                className="p-1 hover:bg-gray-100 rounded disabled:opacity-50"
              >
                {connector.is_enabled ? (
                  <ToggleRight className="h-5 w-5 text-success-600" />
                ) : (
                  <ToggleLeft className="h-5 w-5 text-gray-400" />
                )}
              </button>
              
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="p-1 hover:bg-gray-100 rounded"
                >
                  <MoreVertical className="h-4 w-4 text-gray-400" />
                </button>
                
                {showMenu && (
                  <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
                    <button 
                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <Edit className="h-4 w-4 mr-2" />
                      Edit
                    </button>
                    <button 
                      onClick={handleDelete}
                      disabled={deleteMutation.isPending}
                      className="flex items-center w-full px-4 py-2 text-sm text-error-600 hover:bg-error-50 disabled:opacity-50"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <Settings className="h-3 w-3" />
            <span>Configuration available</span>
          </div>
          <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            Configure
          </button>
        </div>
      </div>
    </div>
  )
}

const ConnectorTypeFilter = ({
  selected,
  onChange
}: {
  selected: ConnectorType | 'all'
  onChange: (type: ConnectorType | 'all') => void
}) => {
  // Only show implemented connector types
  const types = [
    { value: 'all', label: 'All Types', icon: Filter },
    { value: ConnectorType.GITHUB, label: 'GitHub', icon: GitHubLogo },
    { value: ConnectorType.SLACK, label: 'Slack', icon: SlackLogo },
    { value: ConnectorType.GOOGLE_DOCS, label: 'Google Docs', icon: GoogleDocsLogo },
    { value: ConnectorType.GOOGLE_SHEETS, label: 'Google Sheets', icon: GoogleSheetsLogo },
    { value: ConnectorType.GMAIL, label: 'Gmail', icon: GmailLogo },
    { value: ConnectorType.GOOGLE_SLIDES, label: 'Google Slides', icon: GoogleSlidesLogo },
    { value: ConnectorType.JIRA, label: 'Jira', icon: JiraLogo },
    { value: ConnectorType.NOTION, label: 'Notion', icon: NotionLogo },
    { value: ConnectorType.ZOOM, label: 'Zoom', icon: ZoomLogo },
    { value: ConnectorType.OUTLOOK, label: 'Outlook', icon: OutlookLogo },
    { value: ConnectorType.TEAMS, label: 'Teams', icon: TeamsLogo },
    { value: ConnectorType.EXCEL, label: 'Excel', icon: ExcelLogo },
    { value: ConnectorType.POWERPOINT, label: 'PowerPoint', icon: PowerPointLogo },
    { value: ConnectorType.CONFLUENCE, label: 'Confluence', icon: ConfluenceLogo },
    { value: ConnectorType.GITLAB, label: 'GitLab', icon: GitLabLogo },
    { value: ConnectorType.BITBUCKET, label: 'Bitbucket', icon: BitbucketLogo },
    { value: ConnectorType.LINEAR, label: 'Linear', icon: LinearLogo },
    { value: ConnectorType.DISCORD, label: 'Discord', icon: DiscordLogo },
  ]

  return (
    <div className="flex flex-wrap gap-2">
      {types.map(type => {
        const Icon = type.icon
        return (
          <button
            key={type.value}
            onClick={() => onChange(type.value as ConnectorType | 'all')}
            className={cn(
              'flex items-center space-x-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
              selected === type.value
                ? 'bg-primary-50 border-primary-200 text-primary-700'
                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
            )}
          >
            <Icon className="h-4 w-4" />
            <span>{type.label}</span>
          </button>
        )
      })}
    </div>
  )
}

export default function Connectors() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<ConnectorType | 'all'>('all')
  const [selectedTenant, setSelectedTenant] = useState<string>('all')
  const [showConnectorModal, setShowConnectorModal] = useState(false)

  const { data: tenants = [] } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then(res => res.data)
  })

  // Get all connectors from all tenants
  const tenantConnectorQueries = useQuery({
    queryKey: ['all-connectors', tenants.map(t => t.slug)],
    queryFn: async () => {
      const allConnectors = await Promise.all(
        tenants.map(async (tenant) => {
          try {
            const response = await connectorsApi.list(tenant.slug)
            return response.data.map(connector => ({
              ...connector,
              tenantSlug: tenant.slug,
              tenantName: tenant.name
            }))
          } catch (error) {
            return []
          }
        })
      )
      return allConnectors.flat()
    },
    enabled: tenants.length > 0
  })

  const allConnectors = tenantConnectorQueries.data || []

  const filteredConnectors = allConnectors.filter(connector => {
    const matchesSearch = 
      connector.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      connector.connector_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      connector.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      connector.tenantName.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesType = selectedType === 'all' || connector.connector_type === selectedType
    const matchesTenant = selectedTenant === 'all' || connector.tenantSlug === selectedTenant
    
    return matchesSearch && matchesType && matchesTenant
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Connectors</h1>
          <p className="text-gray-600">Manage integrations across all tenants</p>
        </div>
        <button 
          onClick={() => {
            console.log('Add Connector button clicked!')
            setShowConnectorModal(true)
          }}
          className="btn-primary"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Connector
        </button>
      </div>

      {/* Filters */}
      <div className="space-y-4">
        {/* Search */}
        <div className="flex items-center space-x-4">
          <div className="flex-1 max-w-md relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search connectors..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-10"
            />
          </div>
          
          {/* Tenant filter */}
          <select
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
            className="input-field w-auto"
          >
            <option value="all">All Tenants</option>
            {tenants.map(tenant => (
              <option key={tenant.slug} value={tenant.slug}>
                {tenant.name}
              </option>
            ))}
          </select>
        </div>

        {/* Type filters */}
        <ConnectorTypeFilter
          selected={selectedType}
          onChange={setSelectedType}
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="card-content">
            <p className="text-sm font-medium text-gray-600">Total Connectors</p>
            <p className="text-2xl font-bold text-gray-900">{allConnectors.length}</p>
          </div>
        </div>
        <div className="card">
          <div className="card-content">
            <p className="text-sm font-medium text-gray-600">Active</p>
            <p className="text-2xl font-bold text-success-600">
              {allConnectors.filter(c => c.is_enabled).length}
            </p>
          </div>
        </div>
        <div className="card">
          <div className="card-content">
            <p className="text-sm font-medium text-gray-600">Inactive</p>
            <p className="text-2xl font-bold text-gray-500">
              {allConnectors.filter(c => !c.is_enabled).length}
            </p>
          </div>
        </div>
        <div className="card">
          <div className="card-content">
            <p className="text-sm font-medium text-gray-600">Types</p>
            <p className="text-2xl font-bold text-gray-900">
              {new Set(allConnectors.map(c => c.connector_type)).size}
            </p>
          </div>
        </div>
      </div>

      {/* Connectors grid */}
      {tenantConnectorQueries.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="card-content">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2 mb-4"></div>
                <div className="h-3 bg-gray-200 rounded w-full"></div>
              </div>
            </div>
          ))}
        </div>
      ) : filteredConnectors.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredConnectors.map((connector) => (
            <ConnectorCard
              key={`${connector.tenantSlug}-${connector.id}`}
              connector={connector}
              tenant={connector.tenantName}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchQuery || selectedType !== 'all' || selectedTenant !== 'all' 
              ? 'No connectors found' 
              : 'No connectors configured'
            }
          </h3>
          <p className="text-gray-600 mb-4">
            {searchQuery || selectedType !== 'all' || selectedTenant !== 'all'
              ? 'Try adjusting your search criteria'
              : 'Add your first connector to get started'
            }
          </p>
          {!searchQuery && selectedType === 'all' && selectedTenant === 'all' && (
            <button 
              onClick={() => {
                console.log('Add Connector button clicked (empty state)!')
                setShowConnectorModal(true)
              }}
              className="btn-primary"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Connector
            </button>
          )}
        </div>
      )}

      <ConnectorModal
        isOpen={showConnectorModal}
        onClose={() => setShowConnectorModal(false)}
      />
    </div>
  )
}