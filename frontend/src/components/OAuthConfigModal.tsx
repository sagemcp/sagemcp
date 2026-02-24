import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { X, Settings } from 'lucide-react'
import { createPortal } from 'react-dom'
import { oauthApi } from '@/utils/api'
import { OAuthConfigCreate } from '@/types'
import { cn } from '@/utils/cn'
import { GitHubLogo, SlackLogo, GoogleDocsLogo, JiraLogo } from './icons/BrandLogos'

const oauthConfigSchema = z.object({
  provider: z.string().min(1, 'Provider is required'),
  client_id: z.string().min(1, 'Client ID is required'),
  client_secret: z.string().min(1, 'Client Secret is required'),
})

type OAuthConfigFormData = z.infer<typeof oauthConfigSchema>

const ProviderIcon = ({ provider }: { provider: string }) => {
  const icons = {
    github: GitHubLogo,
    slack: SlackLogo,
    google_docs: GoogleDocsLogo,
    jira: JiraLogo,
  }

  const Icon = icons[provider as keyof typeof icons] || Settings
  return <Icon className="h-5 w-5" />
}

interface OAuthConfigModalProps {
  isOpen: boolean
  onClose: () => void
  tenantSlug: string
  provider: string
  providerName: string
  onConfigSaved?: () => void
}

export default function OAuthConfigModal({
  isOpen,
  onClose,
  tenantSlug,
  provider,
  providerName,
  onConfigSaved
}: OAuthConfigModalProps) {
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
    reset
  } = useForm<OAuthConfigFormData>({
    resolver: zodResolver(oauthConfigSchema),
    defaultValues: {
      provider: provider
    }
  })

  // Set provider value when modal opens (similar to ConnectorModal)
  React.useEffect(() => {
    if (isOpen && provider) {
      setValue('provider', provider)
    }
  }, [isOpen, provider, setValue])

  const createMutation = useMutation({
    mutationFn: (data: OAuthConfigCreate) => {
      console.log('Creating OAuth config via API...')
      console.log('Data:', data)
      console.log('Tenant slug:', tenantSlug)
      return oauthApi.createConfig(tenantSlug, data)
    },
    onSuccess: async () => {
      console.log('OAuth config creation successful!')
      // Invalidate and wait for refetch to complete
      await queryClient.invalidateQueries({ queryKey: ['oauth-configs', tenantSlug] })
      await queryClient.invalidateQueries({ queryKey: ['oauth-providers'] })

      toast.success(`${providerName} OAuth configuration saved successfully`)
      onConfigSaved?.()

      // Small delay to ensure parent components have time to update
      setTimeout(() => {
        handleClose()
      }, 100)
    },
    onError: (error: any) => {
      console.error('OAuth config save error:', error)
      toast.error(error.response?.data?.detail || error.message || 'Failed to save OAuth configuration')
    }
  })

  const handleClose = () => {
    reset()
    onClose()
  }

  // Reset form when modal closes
  React.useEffect(() => {
    if (!isOpen) {
      reset()
    }
  }, [isOpen, reset])

  // Early return if modal is closed to prevent unnecessary renders
  if (!isOpen) return null

  console.log('=== OAuth Config Modal Render (OPEN) ===')
  console.log('tenantSlug:', tenantSlug)
  console.log('provider:', provider)
  console.log('providerName:', providerName)

  const onSubmit = (data: OAuthConfigFormData) => {
    console.log('=== OAuth Config Form Submit ===')
    console.log('Data:', data)
    console.log('Tenant slug:', tenantSlug)
    console.log('Form errors:', errors)
    console.log('Is submitting:', isSubmitting)

    console.log('API call will be made to:', `/api/v1/oauth/${tenantSlug}/config`)
    createMutation.mutate(data)
  }

  // Debug form state
  console.log('Form state debug:', {
    isSubmitting,
    errors,
    formValid: Object.keys(errors).length === 0,
    provider: provider,
    defaultValues: { provider: provider }
  })

  const redirectUri = `${window.location.origin}/api/v1/oauth/${tenantSlug}/callback/${provider}`

  const modalContent = (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />
        <div className="relative bg-theme-surface border border-theme-default rounded-lg shadow-2xl max-w-lg w-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-theme-default">
            <div className="flex items-center space-x-3">
              <div className={cn(
                'p-2 rounded-lg',
                provider === 'github' ? 'bg-gray-900 text-white' :
                provider === 'slack' ? 'bg-purple-600 text-white' :
                provider === 'google_docs' ? 'bg-blue-500 text-white' :
                provider === 'jira' ? 'bg-blue-600 text-white' :
                'bg-gray-600 text-white'
              )}>
                <ProviderIcon provider={provider} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-theme-primary">
                  Configure {providerName} OAuth
                </h3>
                <p className="text-sm text-theme-secondary">
                  Set up your {providerName} OAuth application credentials
                </p>
              </div>
            </div>
            <button onClick={handleClose} className="text-theme-muted hover:text-theme-secondary">
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            <form
              onSubmit={handleSubmit(onSubmit)}
              className="space-y-4"
              onInvalid={(e) => console.log('Form invalid:', e)}
            >
              {/* Instructions */}
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                <h4 className="text-sm font-medium text-blue-400 mb-2">
                  Setup Instructions
                </h4>
                <ol className="text-sm text-blue-400 space-y-1 list-decimal list-inside">
                  <li>Create a {providerName} OAuth application</li>
                  <li>Set the redirect URI to: <code className="bg-blue-500/10 px-1 rounded text-xs">{redirectUri}</code></li>
                  <li>Copy the Client ID and Client Secret below</li>
                </ol>
              </div>

              {/* Hidden provider field */}
              <input type="hidden" {...register('provider')} value={provider} />

              {/* Client ID */}
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Client ID *
                </label>
                <input
                  {...register('client_id')}
                  className="input-field"
                  placeholder="Enter your OAuth application Client ID"
                />
                {errors.client_id && (
                  <p className="mt-1 text-sm text-error-600">{errors.client_id.message}</p>
                )}
              </div>

              {/* Client Secret */}
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
                  Client Secret *
                </label>
                <input
                  {...register('client_secret')}
                  type="password"
                  className="input-field"
                  placeholder="Enter your OAuth application Client Secret"
                />
                {errors.client_secret && (
                  <p className="mt-1 text-sm text-error-600">{errors.client_secret.message}</p>
                )}
              </div>

              {/* Footer */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-theme-default">
                <button
                  type="button"
                  onClick={handleClose}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn-primary"
                >
                  {isSubmitting ? 'Saving...' : 'Save Configuration'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )

  // Render modal in a portal to avoid form nesting issues
  return createPortal(modalContent, document.body)
}
