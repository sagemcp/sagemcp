import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Key } from 'lucide-react'
import { tenantsApi, connectorsApi } from '@/utils/api'
import { ConnectorType, ConnectorCreate } from '@/types'
import { cn } from '@/utils/cn'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { ConnectorBadge } from '@/components/sage/connector-badge'

const connectorSchema = z.object({
  tenant_slug: z.string().min(1, 'Please select a tenant'),
  connector_type: z.nativeEnum(ConnectorType, {
    errorMap: () => ({ message: 'Please select a connector type' })
  }),
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().optional(),
})

type ConnectorFormData = z.infer<typeof connectorSchema>

const CONNECTOR_CONFIGS: Record<string, { name: string; description: string }> = {
  [ConnectorType.GITHUB]: { name: 'GitHub', description: 'Connect to GitHub repositories and issues' },
  [ConnectorType.SLACK]: { name: 'Slack', description: 'Connect to Slack channels and messages' },
  [ConnectorType.GOOGLE_DOCS]: { name: 'Google Docs', description: 'Create, read, and manage Google Docs' },
  [ConnectorType.GOOGLE_SHEETS]: { name: 'Google Sheets', description: 'Read, write, and manage Google Sheets spreadsheets' },
  [ConnectorType.GMAIL]: { name: 'Gmail', description: 'Send, read, and manage Gmail messages and threads' },
  [ConnectorType.GOOGLE_SLIDES]: { name: 'Google Slides', description: 'Create and manage Google Slides presentations' },
  [ConnectorType.JIRA]: { name: 'Jira', description: 'Access Jira projects, issues, and sprints' },
  [ConnectorType.NOTION]: { name: 'Notion', description: 'Connect to Notion pages and databases' },
  [ConnectorType.ZOOM]: { name: 'Zoom', description: 'Manage Zoom meetings and recordings' },
  [ConnectorType.OUTLOOK]: { name: 'Outlook', description: 'Read, send, and manage Outlook emails' },
  [ConnectorType.TEAMS]: { name: 'Microsoft Teams', description: 'Manage Teams channels, chats, and messages' },
  [ConnectorType.EXCEL]: { name: 'Excel', description: 'Read, write, and manage Excel workbooks in OneDrive' },
  [ConnectorType.POWERPOINT]: { name: 'PowerPoint', description: 'Manage PowerPoint presentations in OneDrive' },
  [ConnectorType.CONFLUENCE]: { name: 'Confluence', description: 'Access Confluence spaces, pages, and content' },
  [ConnectorType.GITLAB]: { name: 'GitLab', description: 'Connect to GitLab projects, merge requests, and pipelines' },
  [ConnectorType.BITBUCKET]: { name: 'Bitbucket', description: 'Connect to Bitbucket repositories and pull requests' },
  [ConnectorType.LINEAR]: { name: 'Linear', description: 'Access Linear issues, projects, teams, and cycles' },
  [ConnectorType.DISCORD]: { name: 'Discord', description: 'Manage Discord servers, channels, and messages' },
}

const IMPLEMENTED_TYPES = [
  ConnectorType.GITHUB, ConnectorType.SLACK, ConnectorType.GOOGLE_DOCS,
  ConnectorType.GOOGLE_SHEETS, ConnectorType.GMAIL, ConnectorType.GOOGLE_SLIDES,
  ConnectorType.JIRA, ConnectorType.NOTION, ConnectorType.ZOOM,
  ConnectorType.OUTLOOK, ConnectorType.TEAMS, ConnectorType.EXCEL,
  ConnectorType.POWERPOINT, ConnectorType.CONFLUENCE, ConnectorType.GITLAB,
  ConnectorType.BITBUCKET, ConnectorType.LINEAR, ConnectorType.DISCORD,
]

interface ConnectorModalProps {
  isOpen: boolean
  onClose: () => void
  preselectedTenant?: string
}

export default function ConnectorModal({
  isOpen,
  onClose,
  preselectedTenant
}: ConnectorModalProps) {
  const [step, setStep] = useState<'type' | 'details'>('type')
  const [selectedType, setSelectedType] = useState<ConnectorType | null>(null)
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
    reset
  } = useForm<ConnectorFormData>({
    resolver: zodResolver(connectorSchema),
    defaultValues: preselectedTenant ? { tenant_slug: preselectedTenant } : undefined
  })

  const { data: tenants = [] } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then(res => res.data),
    enabled: isOpen
  })

  const selectedTenantSlug = preselectedTenant || undefined
  const { data: existingConnectors = [] } = useQuery({
    queryKey: ['connectors', selectedTenantSlug],
    queryFn: () => selectedTenantSlug ? connectorsApi.list(selectedTenantSlug).then(res => res.data) : Promise.resolve([]),
    enabled: isOpen && !!selectedTenantSlug
  })

  const usedConnectorTypes = new Set(existingConnectors.map(c => c.connector_type))

  const createMutation = useMutation({
    mutationFn: ({ tenant_slug, ...data }: ConnectorFormData) =>
      connectorsApi.create(tenant_slug, data as ConnectorCreate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      queryClient.invalidateQueries({ queryKey: ['all-connectors'] })
      toast.success('Connector created successfully')
      handleClose()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create connector')
    }
  })

  const handleClose = () => {
    setStep('type')
    setSelectedType(null)
    reset()
    onClose()
  }

  const handleTypeSelect = (type: ConnectorType) => {
    setSelectedType(type)
    setValue('connector_type', type)
    setStep('details')
  }

  const requiresOAuth = (type: ConnectorType) => {
    return [
      ConnectorType.GITHUB, ConnectorType.SLACK, ConnectorType.GOOGLE_DOCS,
      ConnectorType.GOOGLE_SHEETS, ConnectorType.GMAIL, ConnectorType.GOOGLE_SLIDES,
      ConnectorType.JIRA, ConnectorType.NOTION, ConnectorType.ZOOM,
      ConnectorType.OUTLOOK, ConnectorType.TEAMS, ConnectorType.EXCEL,
      ConnectorType.POWERPOINT, ConnectorType.CONFLUENCE, ConnectorType.GITLAB,
      ConnectorType.BITBUCKET, ConnectorType.LINEAR, ConnectorType.DISCORD,
    ].includes(type)
  }

  const onSubmit = (data: ConnectorFormData) => {
    const payload = { ...data, configuration: null }
    createMutation.mutate(payload as any)
  }

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <SheetContent onClose={handleClose} className="sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>
            {step === 'type' ? 'Choose Connector Type' : 'Configure Connector'}
          </SheetTitle>
          <SheetDescription>
            {step === 'type'
              ? 'Select the type of connector you want to create'
              : `Setting up ${selectedType} connector`
            }
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 px-6 py-4 overflow-y-auto">
          {step === 'type' ? (
            <div className="grid grid-cols-1 gap-3">
              {IMPLEMENTED_TYPES.map((type) => {
                const config = CONNECTOR_CONFIGS[type]
                if (!config) return null
                const disabled = usedConnectorTypes.has(type)
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => !disabled && handleTypeSelect(type)}
                    disabled={disabled}
                    className={cn(
                      'p-4 border rounded-lg transition-all text-left w-full',
                      disabled
                        ? 'border-theme-default bg-theme-surface/50 opacity-50 cursor-not-allowed'
                        : selectedType === type
                        ? 'border-accent bg-accent/10'
                        : 'border-theme-default hover:border-theme-hover bg-surface-elevated'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <ConnectorBadge type={type} size="sm" />
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-theme-primary">{config.name}</h4>
                        <p className="text-xs text-theme-muted mt-0.5">
                          {disabled ? 'Already exists for this tenant' : config.description}
                        </p>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          ) : (
            <form id="connector-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {selectedType && requiresOAuth(selectedType) && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
                  <div className="flex items-start gap-3">
                    <Key className="h-5 w-5 text-amber-400 mt-0.5 shrink-0" />
                    <div>
                      <h4 className="text-sm font-medium text-amber-300">
                        OAuth Configuration Required
                      </h4>
                      <p className="text-sm text-amber-400/80 mt-1">
                        After creating this connector, go to the <strong>OAuth Settings</strong> tab to configure your {selectedType} credentials.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {!preselectedTenant && (
                <div>
                  <label className="block text-sm font-medium text-theme-secondary mb-1">Tenant *</label>
                  <select {...register('tenant_slug')} className="input-field">
                    <option value="">Select a tenant...</option>
                    {tenants.map(tenant => (
                      <option key={tenant.slug} value={tenant.slug}>
                        {tenant.name} ({tenant.slug})
                      </option>
                    ))}
                  </select>
                  {errors.tenant_slug && (
                    <p className="mt-1 text-sm text-error-400">{errors.tenant_slug.message}</p>
                  )}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">Connector Name *</label>
                <input
                  {...register('name')}
                  className="input-field"
                  placeholder={`My ${selectedType} Connector`}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-error-400">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">Description</label>
                <textarea
                  {...register('description')}
                  className="input-field"
                  rows={3}
                  placeholder="Brief description of this connector..."
                />
              </div>

              <input type="hidden" {...register('connector_type')} />
            </form>
          )}
        </div>

        {step === 'details' && (
          <SheetFooter>
            <Button type="button" variant="ghost" onClick={() => setStep('type')}>Back</Button>
            <div className="flex gap-2">
              <Button type="button" variant="ghost" onClick={handleClose}>Cancel</Button>
              <Button type="submit" form="connector-form" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create Connector'}
              </Button>
            </div>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  )
}
