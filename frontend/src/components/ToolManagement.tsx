import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Power,
  PowerOff,
  Search,
  RefreshCw,
  CheckSquare,
  Square,
  AlertTriangle
} from 'lucide-react'
import { toolsApi } from '@/utils/api'
import { cn } from '@/utils/cn'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

interface ToolManagementProps {
  tenantSlug: string
  connectorId: string
  connectorName: string
}

export default function ToolManagement({ tenantSlug, connectorId, connectorName }: ToolManagementProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')

  const { data: toolsData, isLoading, error } = useQuery({
    queryKey: ['tools', tenantSlug, connectorId],
    queryFn: async () => {
      const response = await toolsApi.list(tenantSlug, connectorId)
      return response.data
    }
  })

  const toggleToolMutation = useMutation({
    mutationFn: async ({ toolName, isEnabled }: { toolName: string; isEnabled: boolean }) => {
      await toolsApi.toggle(tenantSlug, connectorId, toolName, isEnabled)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools', tenantSlug, connectorId] })
      toast.success('Tool updated successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update tool')
    }
  })

  const enableAllMutation = useMutation({
    mutationFn: async () => {
      await toolsApi.enableAll(tenantSlug, connectorId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools', tenantSlug, connectorId] })
      toast.success('All tools enabled')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to enable all tools')
    }
  })

  const disableAllMutation = useMutation({
    mutationFn: async () => {
      await toolsApi.disableAll(tenantSlug, connectorId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools', tenantSlug, connectorId] })
      toast.success('All tools disabled')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to disable all tools')
    }
  })

  const syncToolsMutation = useMutation({
    mutationFn: async () => {
      const response = await toolsApi.sync(tenantSlug, connectorId)
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tools', tenantSlug, connectorId] })
      if (data.added.length > 0 || data.removed.length > 0) {
        toast.success(data.summary)
      } else {
        toast.success('Tools are already in sync')
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to sync tools')
    }
  })

  const filteredTools = useMemo(() => {
    if (!toolsData?.tools) return []
    if (!searchQuery) return toolsData.tools
    const query = searchQuery.toLowerCase()
    return toolsData.tools.filter(tool =>
      tool.tool_name.toLowerCase().includes(query) ||
      tool.description?.toLowerCase().includes(query)
    )
  }, [toolsData?.tools, searchQuery])

  const isDangerousTool = (toolName: string) => {
    const dangerous = ['delete', 'create', 'remove']
    return dangerous.some(keyword => toolName.toLowerCase().includes(keyword))
  }

  const handleToggleTool = (toolName: string, currentState: boolean) => {
    toggleToolMutation.mutate({ toolName, isEnabled: !currentState })
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg border border-error-500/30 bg-error-500/10">
        <p className="text-error-400">Failed to load tools</p>
      </div>
    )
  }

  if (!toolsData) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-zinc-100">
            Tools for {connectorName}
          </h3>
          <p className="text-sm text-zinc-500 mt-0.5">
            {toolsData.summary.enabled} of {toolsData.summary.total} tools enabled
          </p>
        </div>
      </div>

      {/* Bulk Actions */}
      <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg border border-zinc-800 bg-surface-elevated">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => enableAllMutation.mutate()}
          disabled={enableAllMutation.isPending}
          className="text-green-400 hover:text-green-300 hover:bg-green-500/10"
        >
          <Power className="h-4 w-4 mr-1.5" />
          Enable All
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => disableAllMutation.mutate()}
          disabled={disableAllMutation.isPending}
          className="text-error-400 hover:text-error-300 hover:bg-error-500/10"
        >
          <PowerOff className="h-4 w-4 mr-1.5" />
          Disable All
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => syncToolsMutation.mutate()}
          disabled={syncToolsMutation.isPending}
          className="text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
        >
          <RefreshCw className={cn("h-4 w-4 mr-1.5", syncToolsMutation.isPending && "animate-spin")} />
          Sync Tools
        </Button>

        <div className="ml-auto flex items-center gap-2 flex-1 max-w-xs">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input
              type="text"
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-9 py-1.5 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Tools List */}
      <div className="border border-zinc-800 rounded-lg overflow-hidden">
        <div className="divide-y divide-zinc-800 max-h-[500px] overflow-y-auto">
          {filteredTools.length === 0 ? (
            <div className="p-8 text-center text-zinc-500">
              {searchQuery ? 'No tools match your search' : 'No tools available'}
            </div>
          ) : (
            filteredTools.map((tool) => (
              <div
                key={tool.tool_name}
                className={cn(
                  "p-4 hover:bg-zinc-800/50 transition-colors",
                  !tool.is_enabled && "opacity-50"
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className={cn(
                        "text-sm font-medium font-mono truncate",
                        tool.is_enabled ? "text-zinc-100" : "text-zinc-500"
                      )}>
                        {tool.tool_name}
                      </h4>
                      {isDangerousTool(tool.tool_name) && (
                        <Badge variant="warning" className="text-xs">
                          <AlertTriangle className="h-3 w-3 mr-1" />
                          Dangerous
                        </Badge>
                      )}
                    </div>
                    {tool.description && (
                      <p className="text-xs text-zinc-500 mt-1 line-clamp-2">
                        {tool.description}
                      </p>
                    )}
                  </div>

                  <button
                    onClick={() => handleToggleTool(tool.tool_name, tool.is_enabled)}
                    disabled={toggleToolMutation.isPending}
                    className={cn(
                      "flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors border",
                      tool.is_enabled
                        ? "bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20"
                        : "bg-zinc-800 border-zinc-700 text-zinc-500 hover:bg-zinc-700",
                      "disabled:opacity-50 disabled:cursor-not-allowed"
                    )}
                    title={tool.is_enabled ? 'Disable tool' : 'Enable tool'}
                  >
                    {tool.is_enabled ? (
                      <>
                        <CheckSquare className="h-4 w-4" />
                        Enabled
                      </>
                    ) : (
                      <>
                        <Square className="h-4 w-4" />
                        Disabled
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
