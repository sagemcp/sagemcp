import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Braces, FileText, MessageSquare, Pencil, Plus, Trash2, Wrench } from 'lucide-react'
import { toast } from 'sonner'
import { overridesApi } from '@/utils/api'
import { cn } from '@/utils/cn'
import type {
  ConnectorOverride,
  ConnectorOverrideCreate,
  ConnectorOverrideTargetKind,
} from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'

interface ConnectorOverridesManagementProps {
  tenantSlug: string
  connectorId: string
  connectorName: string
}

type OverrideFormState = {
  target_kind: ConnectorOverrideTargetKind
  identifier: string
  payload_text: string
  metadata_json_text: string
  is_enabled: boolean
}

const DEFAULT_FORM_STATE: OverrideFormState = {
  target_kind: 'resource',
  identifier: '',
  payload_text: '',
  metadata_json_text: '',
  is_enabled: true,
}

const TARGET_KIND_LABELS: Record<ConnectorOverrideTargetKind, string> = {
  tool: 'Tool',
  resource: 'Resource',
  resource_template: 'Resource Template',
  prompt: 'Prompt',
}

const TARGET_KIND_HINTS: Record<ConnectorOverrideTargetKind, string> = {
  tool: 'Use the tool name as the identifier.',
  resource: 'Use the full resource URI as the identifier.',
  resource_template: 'Use the URI template as the identifier.',
  prompt: 'Use the prompt name as the identifier.',
}

const TARGET_KIND_IDENTIFIER_PLACEHOLDERS: Record<ConnectorOverrideTargetKind, string> = {
  tool: 'safe_tool',
  resource: 'docs://guide',
  resource_template: 'sagemcp://github/issues/{owner}/{repo}/{issue_number}',
  prompt: 'triage_issue',
}

const TARGET_KIND_PAYLOAD_PLACEHOLDERS: Record<ConnectorOverrideTargetKind, string> = {
  tool: '{"repo":"openai/codex"}',
  resource: '# Resource body',
  resource_template: 'Issue summary for {owner}/{repo} #{issue_number}\n\n{tool_result}',
  prompt: 'Triage issue {issue_number}',
}

function formatMetadata(metadata?: Record<string, any>) {
  if (!metadata || Object.keys(metadata).length === 0) {
    return ''
  }
  return JSON.stringify(metadata, null, 2)
}

function getOverrideIcon(targetKind: ConnectorOverrideTargetKind) {
  switch (targetKind) {
    case 'tool':
      return Wrench
    case 'resource':
      return FileText
    case 'resource_template':
      return Braces
    case 'prompt':
      return MessageSquare
  }
}

function getOverrideSummary(override: ConnectorOverride) {
  const metadata = override.metadata_json ?? {}
  switch (override.target_kind) {
    case 'tool':
      return metadata.description || metadata.targetToolName || 'Tool override'
    case 'resource':
      return metadata.mimeType || 'Static resource'
    case 'resource_template':
      return metadata.mimeType || 'Templated resource'
    case 'prompt':
      return metadata.description || 'Prompt override'
  }
}

function parseMetadata(text: string) {
  const trimmed = text.trim()
  if (!trimmed) {
    return undefined
  }
  return JSON.parse(trimmed) as Record<string, any>
}

export default function ConnectorOverridesManagement({
  tenantSlug,
  connectorId,
  connectorName,
}: ConnectorOverridesManagementProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingOverride, setEditingOverride] = useState<ConnectorOverride | null>(null)
  const [formState, setFormState] = useState<OverrideFormState>(DEFAULT_FORM_STATE)

  const queryKey = ['overrides', tenantSlug, connectorId]

  const { data: overrides = [], isLoading, error } = useQuery({
    queryKey,
    queryFn: async () => {
      const response = await overridesApi.list(tenantSlug, connectorId)
      return response.data
    },
  })

  const filteredOverrides = useMemo(() => {
    if (!searchQuery.trim()) {
      return overrides
    }
    const query = searchQuery.toLowerCase()
    return overrides.filter((override) => {
      const metadata = JSON.stringify(override.metadata_json ?? {}).toLowerCase()
      return (
        override.identifier.toLowerCase().includes(query) ||
        override.target_kind.toLowerCase().includes(query) ||
        override.payload_text.toLowerCase().includes(query) ||
        metadata.includes(query)
      )
    })
  }, [overrides, searchQuery])

  const upsertMutation = useMutation({
    mutationFn: async (payload: ConnectorOverrideCreate) => {
      if (editingOverride) {
        return overridesApi.update(tenantSlug, connectorId, editingOverride.id, payload)
      }
      return overridesApi.create(tenantSlug, connectorId, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey })
      toast.success(editingOverride ? 'Override updated' : 'Override created')
      closeDialog()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to save override')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (overrideId: string) => overridesApi.delete(tenantSlug, connectorId, overrideId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey })
      toast.success('Override deleted')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete override')
    },
  })

  useEffect(() => {
    if (!isDialogOpen) {
      setFormState(DEFAULT_FORM_STATE)
      setEditingOverride(null)
    }
  }, [isDialogOpen])

  function closeDialog() {
    setIsDialogOpen(false)
    setEditingOverride(null)
    setFormState(DEFAULT_FORM_STATE)
  }

  function openCreateDialog() {
    setEditingOverride(null)
    setFormState(DEFAULT_FORM_STATE)
    setIsDialogOpen(true)
  }

  function openEditDialog(override: ConnectorOverride) {
    setEditingOverride(override)
    setFormState({
      target_kind: override.target_kind,
      identifier: override.identifier,
      payload_text: override.payload_text,
      metadata_json_text: formatMetadata(override.metadata_json),
      is_enabled: override.is_enabled,
    })
    setIsDialogOpen(true)
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()

    if (!formState.identifier.trim()) {
      toast.error('Identifier is required')
      return
    }
    if (!formState.payload_text.trim()) {
      toast.error('Payload is required')
      return
    }

    let metadata_json: Record<string, any> | undefined
    try {
      metadata_json = parseMetadata(formState.metadata_json_text)
    } catch {
      toast.error('Metadata must be valid JSON')
      return
    }

    upsertMutation.mutate({
      target_kind: formState.target_kind,
      identifier: formState.identifier.trim(),
      payload_text: formState.payload_text,
      metadata_json,
      is_enabled: formState.is_enabled,
    })
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-error-500/30 bg-error-500/10 p-4">
        <p className="text-error-400">Failed to load overrides</p>
      </div>
    )
  }

  return (
    <>
      <Dialog open={isDialogOpen} onOpenChange={(open) => !upsertMutation.isPending && setIsDialogOpen(open)}>
        <DialogContent onClose={closeDialog} className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingOverride ? 'Edit Override' : 'Create Override'}</DialogTitle>
            <p className="mt-1 text-sm text-theme-secondary">{connectorName}</p>
          </DialogHeader>

          <form onSubmit={handleSubmit}>
            <div className="space-y-4 px-6 py-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm text-theme-secondary">
                  Target kind
                  <select
                    value={formState.target_kind}
                    onChange={(event) =>
                      setFormState((current) => ({
                        ...current,
                        target_kind: event.target.value as ConnectorOverrideTargetKind,
                      }))
                    }
                    disabled={!!editingOverride}
                    className="input-field mt-1"
                  >
                    {Object.entries(TARGET_KIND_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-sm text-theme-secondary">
                  Identifier
                  <input
                    type="text"
                    value={formState.identifier}
                    onChange={(event) =>
                      setFormState((current) => ({
                        ...current,
                        identifier: event.target.value,
                      }))
                    }
                    disabled={!!editingOverride}
                    className="input-field mt-1"
                    placeholder={TARGET_KIND_IDENTIFIER_PLACEHOLDERS[formState.target_kind]}
                  />
                </label>
              </div>

              <p className="text-xs text-theme-muted">{TARGET_KIND_HINTS[formState.target_kind]}</p>

              <label className="block text-sm text-theme-secondary">
                Payload
                <textarea
                  value={formState.payload_text}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      payload_text: event.target.value,
                    }))
                  }
                  className="input-field mt-1 min-h-[140px]"
                  placeholder={TARGET_KIND_PAYLOAD_PLACEHOLDERS[formState.target_kind]}
                />
              </label>

              <label className="block text-sm text-theme-secondary">
                Metadata JSON
                <textarea
                  value={formState.metadata_json_text}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      metadata_json_text: event.target.value,
                    }))
                  }
                  className="input-field mt-1 min-h-[140px] font-mono text-xs"
                  placeholder='{"description":"Shown in list results","mimeType":"text/markdown"}'
                />
              </label>

              <label className="flex items-center gap-2 text-sm text-theme-secondary">
                <input
                  type="checkbox"
                  checked={formState.is_enabled}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      is_enabled: event.target.checked,
                    }))
                  }
                  className="h-4 w-4 rounded border-theme-default bg-theme-surface"
                />
                Enabled
              </label>
            </div>

            <DialogFooter>
              <Button type="button" variant="ghost" onClick={closeDialog} disabled={upsertMutation.isPending}>
                Cancel
              </Button>
              <Button type="submit" disabled={upsertMutation.isPending}>
                {upsertMutation.isPending ? 'Saving...' : editingOverride ? 'Save Override' : 'Create Override'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <div className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-theme-primary">Local Overrides</h3>
            <p className="mt-0.5 text-sm text-theme-muted">
              Create connector-scoped prompts, resources, templates, and tool wrappers.
            </p>
          </div>
          <Button size="sm" onClick={openCreateDialog}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Add Override
          </Button>
        </div>

        <div className="rounded-lg border border-theme-default bg-surface-elevated p-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            className="input-field"
            placeholder="Search by identifier, type, payload, or metadata"
          />
        </div>

        <div className="rounded-lg border border-theme-default overflow-hidden">
          <div className="divide-y divide-zinc-800">
            {filteredOverrides.length === 0 ? (
              <div className="p-8 text-center text-theme-muted">
                {overrides.length === 0 ? 'No overrides configured yet.' : 'No overrides match your search.'}
              </div>
            ) : (
              filteredOverrides.map((override) => {
                const Icon = getOverrideIcon(override.target_kind)
                return (
                  <div key={override.id} className={cn('p-4', !override.is_enabled && 'opacity-60')}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4 text-accent" />
                            <span className="font-mono text-sm text-theme-primary">{override.identifier}</span>
                          </div>
                          <Badge variant="default">{TARGET_KIND_LABELS[override.target_kind]}</Badge>
                          <Badge variant={override.is_enabled ? 'healthy' : 'idle'}>
                            {override.is_enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                        </div>

                        <p className="mt-2 text-sm text-theme-secondary">{getOverrideSummary(override)}</p>

                        <div className="mt-3 rounded-md bg-theme-surface p-3">
                          <pre className="whitespace-pre-wrap break-words text-xs text-theme-muted">
                            {override.payload_text}
                          </pre>
                        </div>

                        {override.metadata_json && Object.keys(override.metadata_json).length > 0 && (
                          <details className="mt-3">
                            <summary className="cursor-pointer text-xs font-medium text-theme-secondary">
                              Metadata
                            </summary>
                            <pre className="mt-2 whitespace-pre-wrap break-words rounded-md bg-theme-surface p-3 text-xs text-theme-muted">
                              {formatMetadata(override.metadata_json)}
                            </pre>
                          </details>
                        )}
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Button variant="ghost" size="sm" onClick={() => openEditDialog(override)}>
                          <Pencil className="mr-1.5 h-3.5 w-3.5" />
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-error-400 hover:text-error-300 hover:bg-error-500/10"
                          onClick={() => deleteMutation.mutate(override.id)}
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </>
  )
}
