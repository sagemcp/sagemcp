import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { X, Plus, Trash2, Server, Code, Terminal, Box } from 'lucide-react'
import { tenantsApi, connectorsApi } from '@/utils/api'
import { ConnectorType, ConnectorRuntimeType } from '@/types'
import { cn } from '@/utils/cn'

const externalMCPSchema = z.object({
  tenant_slug: z.string().min(1, 'Please select a tenant'),
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().optional(),
  runtime_type: z.nativeEnum(ConnectorRuntimeType),
  runtime_command: z.string().min(1, 'Runtime command is required'),
  package_path: z.string().optional(),
  env_vars: z.array(z.object({
    key: z.string(),
    value: z.string()
  })).optional(),
  config_vars: z.array(z.object({
    key: z.string(),
    value: z.string()
  })).optional()
})

type ExternalMCPFormData = z.infer<typeof externalMCPSchema>

const RuntimeTypeCard = ({
  type,
  selected,
  onSelect,
}: {
  type: ConnectorRuntimeType
  selected: boolean
  onSelect: (type: ConnectorRuntimeType) => void
}) => {
  const configs: Record<string, {
    icon: React.ComponentType<{ className?: string }>
    name: string
    description: string
    color: string
    example: string
  }> = {
    [ConnectorRuntimeType.EXTERNAL_PYTHON]: {
      icon: Code,
      name: 'Python',
      description: 'Python MCP SDK server',
      color: 'bg-blue-600 text-white',
      example: '["python", "server.py"]'
    },
    [ConnectorRuntimeType.EXTERNAL_NODEJS]: {
      icon: Terminal,
      name: 'Node.js',
      description: 'Node.js @modelcontextprotocol/sdk',
      color: 'bg-green-600 text-white',
      example: '["node", "build/server.js"]'
    },
    [ConnectorRuntimeType.EXTERNAL_GO]: {
      icon: Box,
      name: 'Go',
      description: 'Go MCP implementation',
      color: 'bg-cyan-600 text-white',
      example: '["./mcp-server"]'
    },
    [ConnectorRuntimeType.EXTERNAL_CUSTOM]: {
      icon: Server,
      name: 'Custom',
      description: 'Any binary with MCP over stdio',
      color: 'bg-purple-600 text-white',
      example: '["./custom-server", "--flag"]'
    },
  }

  const config = configs[type]
  if (!config) return null

  const Icon = config.icon

  return (
    <button
      type="button"
      onClick={() => onSelect(type)}
      className={cn(
        'p-4 border-2 rounded-lg transition-all text-left w-full',
        selected
          ? 'border-accent bg-accent/10'
          : 'border-zinc-800 hover:border-zinc-700'
      )}
    >
      <div className="flex items-start space-x-3">
        <div className={cn('p-2 rounded-lg', config.color)}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-zinc-100">{config.name}</h4>
          <p className="text-xs text-zinc-500 mt-1">{config.description}</p>
          <p className="text-xs text-zinc-500 mt-1 font-mono">{config.example}</p>
        </div>
      </div>
    </button>
  )
}

interface ExternalMCPModalProps {
  isOpen: boolean
  onClose: () => void
  preselectedTenant?: string
}

export default function ExternalMCPModal({
  isOpen,
  onClose,
  preselectedTenant
}: ExternalMCPModalProps) {
  const [envVars, setEnvVars] = useState<Array<{ key: string; value: string }>>([])
  const [configVars, setConfigVars] = useState<Array<{ key: string; value: string }>>([])
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
    watch,
    reset
  } = useForm<ExternalMCPFormData>({
    resolver: zodResolver(externalMCPSchema),
    defaultValues: {
      tenant_slug: preselectedTenant || '',
      runtime_type: ConnectorRuntimeType.EXTERNAL_PYTHON
    }
  })

  const selectedRuntime = watch('runtime_type')

  const { data: tenants = [] } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then(res => res.data),
    enabled: isOpen
  })

  const createMutation = useMutation({
    mutationFn: ({ tenant_slug, env_vars, config_vars, ...data }: ExternalMCPFormData) => {
      // Convert env_vars array to object
      const runtime_env: Record<string, string> = {}
      env_vars?.forEach(({ key, value }) => {
        if (key && value) runtime_env[key] = value
      })

      // Convert config_vars array to object
      const configuration: Record<string, string> = {}
      config_vars?.forEach(({ key, value }) => {
        if (key && value) configuration[key] = value
      })

      const packagePath = data.package_path?.trim()

      return connectorsApi.create(tenant_slug, {
        connector_type: ConnectorType.CUSTOM,
        ...data,
        package_path: packagePath || undefined,
        runtime_env,
        configuration
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      queryClient.invalidateQueries({ queryKey: ['all-connectors'] })
      toast.success('External MCP server created successfully')
      handleClose()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create external MCP server')
    }
  })

  const handleClose = () => {
    reset()
    setEnvVars([])
    setConfigVars([])
    onClose()
  }

  const onSubmit = (data: ExternalMCPFormData) => {
    const payload = {
      ...data,
      env_vars: envVars,
      config_vars: configVars
    }
    createMutation.mutate(payload)
  }

  const addEnvVar = () => {
    setEnvVars([...envVars, { key: '', value: '' }])
  }

  const removeEnvVar = (index: number) => {
    setEnvVars(envVars.filter((_, i) => i !== index))
  }

  const updateEnvVar = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...envVars]
    updated[index][field] = value
    setEnvVars(updated)
  }

  const addConfigVar = () => {
    setConfigVars([...configVars, { key: '', value: '' }])
  }

  const removeConfigVar = (index: number) => {
    setConfigVars(configVars.filter((_, i) => i !== index))
  }

  const updateConfigVar = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...configVars]
    updated[index][field] = value
    setConfigVars(updated)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />
        <div className="relative bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
            <div>
              <h3 className="text-lg font-semibold text-zinc-100">
                Add External MCP Server
              </h3>
              <p className="text-sm text-zinc-400">
                Deploy a custom MCP server from any runtime (Python, Node.js, Go, etc.)
              </p>
            </div>
            <button onClick={handleClose} className="text-zinc-500 hover:text-zinc-300">
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 max-h-[calc(90vh-120px)] overflow-y-auto">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Tenant Selection (if not preselected) */}
              {!preselectedTenant && (
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">
                    Tenant *
                  </label>
                  <select {...register('tenant_slug')} className="input-field">
                    <option value="">Select a tenant...</option>
                    {tenants.map(tenant => (
                      <option key={tenant.slug} value={tenant.slug}>
                        {tenant.name} ({tenant.slug})
                      </option>
                    ))}
                  </select>
                  {errors.tenant_slug && (
                    <p className="mt-1 text-sm text-error-600">{errors.tenant_slug.message}</p>
                  )}
                </div>
              )}

              {/* Runtime Type Selection */}
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Runtime Type *
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    ConnectorRuntimeType.EXTERNAL_PYTHON,
                    ConnectorRuntimeType.EXTERNAL_NODEJS,
                    ConnectorRuntimeType.EXTERNAL_GO,
                    ConnectorRuntimeType.EXTERNAL_CUSTOM
                  ].map((type) => (
                    <RuntimeTypeCard
                      key={type}
                      type={type}
                      selected={selectedRuntime === type}
                      onSelect={(type) => setValue('runtime_type', type)}
                    />
                  ))}
                </div>
              </div>

              {/* Server Name */}
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">
                  Server Name *
                </label>
                <input
                  {...register('name')}
                  className="input-field"
                  placeholder="My Custom MCP Server"
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-error-600">{errors.name.message}</p>
                )}
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">
                  Description
                </label>
                <textarea
                  {...register('description')}
                  className="input-field"
                  rows={2}
                  placeholder="Brief description of this MCP server..."
                />
              </div>

              {/* Runtime Command */}
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">
                  Runtime Command * (JSON Array)
                </label>
                <input
                  {...register('runtime_command')}
                  className="input-field font-mono text-sm"
                  placeholder='["python", "server.py"] or ["npx", "@modelcontextprotocol/server-github"]'
                />
                {errors.runtime_command && (
                  <p className="mt-1 text-sm text-error-600">{errors.runtime_command.message}</p>
                )}
                <p className="mt-1 text-xs text-zinc-500">
                  JSON array of command and arguments. Example: ["node", "build/server.js"]
                </p>
              </div>

              {/* Package Path */}
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">
                  Package Path (Working Directory)
                </label>
                <input
                  {...register('package_path')}
                  className="input-field font-mono text-sm"
                  placeholder="/path/to/mcp-server"
                />
                <p className="mt-1 text-xs text-zinc-500">
                  Optional: Working directory for the process
                </p>
              </div>

              {/* Environment Variables */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-zinc-300">
                    Environment Variables
                  </label>
                  <button
                    type="button"
                    onClick={addEnvVar}
                    className="text-sm text-accent hover:text-accent flex items-center"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Variable
                  </button>
                </div>
                {envVars.length > 0 && (
                  <div className="space-y-2">
                    {envVars.map((envVar, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <input
                          className="input-field flex-1 font-mono text-sm"
                          placeholder="KEY"
                          value={envVar.key}
                          onChange={(e) => updateEnvVar(index, 'key', e.target.value)}
                        />
                        <span className="text-zinc-500">=</span>
                        <input
                          className="input-field flex-1 font-mono text-sm"
                          placeholder="value"
                          value={envVar.value}
                          onChange={(e) => updateEnvVar(index, 'value', e.target.value)}
                        />
                        <button
                          type="button"
                          onClick={() => removeEnvVar(index)}
                          className="text-error-600 hover:text-error-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <p className="mt-1 text-xs text-zinc-500">
                  Use <code className="bg-zinc-800 px-1 rounded">{"{{OAUTH_TOKEN}}"}</code> to inject OAuth credentials
                </p>
              </div>

              {/* Configuration Variables */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-zinc-300">
                    Configuration Variables
                  </label>
                  <button
                    type="button"
                    onClick={addConfigVar}
                    className="text-sm text-accent hover:text-accent flex items-center"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Variable
                  </button>
                </div>
                {configVars.length > 0 && (
                  <div className="space-y-2">
                    {configVars.map((configVar, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <input
                          className="input-field flex-1 font-mono text-sm"
                          placeholder="api_base_url"
                          value={configVar.key}
                          onChange={(e) => updateConfigVar(index, 'key', e.target.value)}
                        />
                        <span className="text-zinc-500">=</span>
                        <input
                          className="input-field flex-1 font-mono text-sm"
                          placeholder="https://api.example.com"
                          value={configVar.value}
                          onChange={(e) => updateConfigVar(index, 'value', e.target.value)}
                        />
                        <button
                          type="button"
                          onClick={() => removeConfigVar(index)}
                          className="text-error-600 hover:text-error-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <p className="mt-1 text-xs text-zinc-500">
                  Config vars are exposed as <code className="bg-zinc-800 px-1 rounded">CONFIG_*</code> environment variables
                </p>
              </div>

              {/* Footer */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-zinc-800">
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
                  {isSubmitting ? 'Creating...' : 'Create External Server'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
