import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Key,
  ExternalLink,
  Trash2,
  Clock,
  CheckCircle,
  XCircle,
  Settings,
  Wrench
} from 'lucide-react'
import { oauthApi } from '@/utils/api'
import { OAuthProvider, OAuthCredential, OAuthConfig } from '@/types'
import { cn } from '@/utils/cn'
import OAuthConfigModal from './OAuthConfigModal'
import { GitHubLogo, SlackLogo, GoogleDocsLogo, JiraLogo, NotionLogo, ZoomLogo } from './icons/BrandLogos'

const ProviderIcon = ({ provider }: { provider: string }) => {
  const icons = {
    github: GitHubLogo,
    slack: SlackLogo,
    google_docs: GoogleDocsLogo,
    jira: JiraLogo,
    notion: NotionLogo,
    zoom: ZoomLogo,
  }

  const Icon = icons[provider as keyof typeof icons] || Settings
  return <Icon className="h-5 w-5" />
}

interface OAuthManagerProps {
  tenantSlug: string
  onCredentialChange?: () => void
  filterProvider?: string // If provided, only show this specific provider
}

export default function OAuthManager({ tenantSlug, onCredentialChange, filterProvider }: OAuthManagerProps) {
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null)
  const [configModal, setConfigModal] = useState<{ isOpen: boolean; provider: string; providerName: string }>({
    isOpen: false,
    provider: '',
    providerName: ''
  })
  const queryClient = useQueryClient()

  const { data: providers = [], isLoading: providersLoading } = useQuery({
    queryKey: ['oauth-providers'],
    queryFn: () => oauthApi.listProviders().then(res => res.data)
  })

  const { data: credentials = [], isLoading: credentialsLoading } = useQuery({
    queryKey: ['oauth-credentials', tenantSlug],
    queryFn: () => oauthApi.listCredentials(tenantSlug).then(res => res.data)
  })

  const { data: configs = [], isLoading: configsLoading } = useQuery({
    queryKey: ['oauth-configs', tenantSlug],
    queryFn: () => oauthApi.listConfigs(tenantSlug).then(res => res.data)
  })

  const revokeMutation = useMutation({
    mutationFn: (provider: string) => oauthApi.revokeCredential(tenantSlug, provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-credentials', tenantSlug] })
      toast.success('OAuth credential revoked successfully')
      onCredentialChange?.()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to revoke OAuth credential')
    }
  })

  const deleteConfigMutation = useMutation({
    mutationFn: (provider: string) => oauthApi.deleteConfig(tenantSlug, provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-configs', tenantSlug] })
      queryClient.invalidateQueries({ queryKey: ['oauth-providers'] })
      toast.success('OAuth configuration deleted successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete OAuth configuration')
    }
  })

  const handleConnect = (provider: OAuthProvider) => {
    const isConfigured = isProviderConfigured(provider, provider.id)
    if (!isConfigured) {
      toast.error(`${provider.name} OAuth is not configured. Please configure OAuth credentials first.`)
      return
    }

    console.log('Starting OAuth connection for:', provider.name)
    setConnectingProvider(provider.id)

    // Listen for OAuth completion
    const handleMessage = (event: MessageEvent) => {
      console.log('Received message:', event.data, 'from origin:', event.origin)

      if (event.origin !== window.location.origin) {
        console.log('Message from different origin, ignoring')
        return
      }

      if (event.data?.type === 'oauth-complete') {
        console.log('OAuth completion message received for provider:', event.data.provider)
        setConnectingProvider(null)

        // Force refresh of all OAuth-related queries
        console.log('Invalidating OAuth queries...')
        queryClient.invalidateQueries({ queryKey: ['oauth-credentials', tenantSlug] })
        queryClient.invalidateQueries({ queryKey: ['oauth-providers'] })

        // Force immediate refetch to ensure UI updates
        queryClient.refetchQueries({ queryKey: ['oauth-credentials', tenantSlug] })
        queryClient.refetchQueries({ queryKey: ['oauth-providers'] })

        toast.success(`Successfully connected to ${provider.name}!`)
        onCredentialChange?.()
        window.removeEventListener('message', handleMessage)
      }
    }

    window.addEventListener('message', handleMessage)
    console.log('Added message listener for OAuth completion')

    // Open OAuth flow
    const popup = oauthApi.initiateOAuth(tenantSlug, provider.id)

    // Monitor popup closure
    const checkClosed = setInterval(() => {
      if (popup && popup.closed) {
        console.log('OAuth popup was closed')
        setConnectingProvider(null)
        window.removeEventListener('message', handleMessage)
        clearInterval(checkClosed)
      }
    }, 1000)

    // Clean up if window is closed manually or timeout
    setTimeout(() => {
      console.log('OAuth timeout reached, cleaning up')
      setConnectingProvider(null)
      window.removeEventListener('message', handleMessage)
      clearInterval(checkClosed)
    }, 300000) // 5 minutes timeout
  }

  const handleRevoke = (provider: string) => {
    if (confirm(`Are you sure you want to revoke access to ${provider}? This will disconnect all connectors using this credential.`)) {
      revokeMutation.mutate(provider)
    }
  }

  const handleReconfigure = (provider: OAuthProvider) => {
    if (confirm(`Are you sure you want to reconfigure ${provider.name}? This will delete the current OAuth configuration and you'll need to set it up again.`)) {
      deleteConfigMutation.mutate(provider.id)
    }
  }

  const getCredentialForProvider = (providerId: string): OAuthCredential | undefined => {
    return credentials.find(cred => cred.provider === providerId)
  }

  const getConfigForProvider = (providerId: string): OAuthConfig | undefined => {
    return configs.find((config: OAuthConfig) => config.provider === providerId && config.is_active)
  }

  const isProviderConfigured = (provider: OAuthProvider, providerId: string): boolean => {
    // Check if tenant has specific config or if global config is available
    const tenantConfig = getConfigForProvider(providerId)
    return tenantConfig ? true : provider.configured
  }

  const isExpired = (credential: OAuthCredential): boolean => {
    if (!credential.expires_at) return false
    return new Date(credential.expires_at) < new Date()
  }

  const handleConfigure = (provider: OAuthProvider) => {
    setConfigModal({
      isOpen: true,
      provider: provider.id,
      providerName: provider.name
    })
  }

  const handleConfigSaved = () => {
    // Refresh all OAuth-related queries and force refetch
    queryClient.invalidateQueries({ queryKey: ['oauth-configs', tenantSlug] })
    queryClient.invalidateQueries({ queryKey: ['oauth-credentials', tenantSlug] })
    queryClient.invalidateQueries({ queryKey: ['oauth-providers'] })

    // Force immediate refetch to ensure UI updates
    queryClient.refetchQueries({ queryKey: ['oauth-configs', tenantSlug] })
    queryClient.refetchQueries({ queryKey: ['oauth-credentials', tenantSlug] })
    queryClient.refetchQueries({ queryKey: ['oauth-providers'] })
  }

  if (providersLoading || credentialsLoading || configsLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="card animate-pulse">
            <div className="card-content">
              <div className="h-4 bg-zinc-700 rounded w-1/4 mb-2"></div>
              <div className="h-3 bg-zinc-700 rounded w-3/4"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 text-sm text-theme-secondary mb-4">
        <Key className="h-4 w-4" />
        <span>
          {filterProvider
            ? `Configure ${filterProvider.charAt(0).toUpperCase() + filterProvider.slice(1)} OAuth to enable this connector`
            : 'Connect external services to enable additional connectors'
          }
        </span>
      </div>

      {providers
        .filter(provider => !filterProvider || provider.id === filterProvider)
        .map((provider) => {
        const credential = getCredentialForProvider(provider.id)
        const isConfigured = isProviderConfigured(provider, provider.id)
        const isConnected = !!credential && credential.is_active
        const expired = credential ? isExpired(credential) : false
        const isConnecting = connectingProvider === provider.id

        return (
          <div key={provider.id} className="card">
            <div className="card-content">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={cn(
                    'p-2 rounded-lg',
                    provider.id === 'github' ? 'bg-gray-900 text-white' :
                    provider.id === 'slack' ? 'bg-purple-600 text-white' :
                    provider.id === 'google_docs' ? 'bg-blue-500 text-white' :
                    provider.id === 'jira' ? 'bg-blue-600 text-white' :
                    'bg-gray-600 text-white'
                  )}>
                    <ProviderIcon provider={provider.id} />
                  </div>
                  <div>
                    <h3 className="font-medium text-theme-primary">{provider.name}</h3>
                    <p className="text-sm text-theme-muted">
                      Scopes: {provider.scopes.join(', ')}
                    </p>
                    {credential && (
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-xs text-theme-muted">
                          Connected as: {credential.provider_username || credential.provider_user_id}
                        </span>
                        {expired && (
                          <span className="text-xs text-error-600 flex items-center">
                            <Clock className="h-3 w-3 mr-1" />
                            Expired
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {isConnected && !expired ? (
                    <span className="status-badge status-active flex items-center">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Connected
                    </span>
                  ) : expired ? (
                    <span className="status-badge status-error flex items-center">
                      <XCircle className="h-3 w-3 mr-1" />
                      Expired
                    </span>
                  ) : (
                    <span className="status-badge bg-theme-elevated text-theme-secondary">
                      Not Connected
                    </span>
                  )}

                  {!isConfigured ? (
                    <button
                      onClick={() => handleConfigure(provider)}
                      className="btn-primary text-xs flex items-center"
                    >
                      <Wrench className="h-3 w-3 mr-1" />
                      Configure
                    </button>
                  ) : isConnected && !expired ? (
                    <>
                      <button
                        onClick={() => handleRevoke(provider.id)}
                        disabled={revokeMutation.isPending}
                        className="btn-secondary text-xs flex items-center"
                      >
                        <Trash2 className="h-3 w-3 mr-1" />
                        Revoke
                      </button>
                      <button
                        onClick={() => handleReconfigure(provider)}
                        disabled={deleteConfigMutation.isPending}
                        className="btn-ghost text-xs flex items-center"
                      >
                        <Wrench className="h-3 w-3 mr-1" />
                        Reconfigure
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => handleConnect(provider)}
                        disabled={isConnecting}
                        className="btn-primary text-xs flex items-center"
                      >
                        {isConnecting ? (
                          <>
                            <div className="animate-spin h-3 w-3 mr-1 border border-white border-t-transparent rounded-full"></div>
                            Connecting...
                          </>
                        ) : (
                          <>
                            <ExternalLink className="h-3 w-3 mr-1" />
                            {expired ? 'Reconnect' : 'Connect'}
                          </>
                        )}
                      </button>
                      {isConfigured && (
                        <button
                          onClick={() => handleReconfigure(provider)}
                          disabled={deleteConfigMutation.isPending}
                          className="btn-ghost text-xs flex items-center"
                        >
                          <Wrench className="h-3 w-3 mr-1" />
                          Reconfigure
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )
      })}

      {providers.length === 0 && (
        <div className="text-center py-8 text-theme-muted">
          <Key className="h-12 w-12 mx-auto mb-2 text-theme-muted" />
          <p>No OAuth providers configured</p>
        </div>
      )}

      <OAuthConfigModal
        isOpen={configModal.isOpen}
        onClose={() => setConfigModal({ isOpen: false, provider: '', providerName: '' })}
        tenantSlug={tenantSlug}
        provider={configModal.provider}
        providerName={configModal.providerName}
        onConfigSaved={handleConfigSaved}
      />
    </div>
  )
}
