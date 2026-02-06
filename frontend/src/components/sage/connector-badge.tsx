import {
  Github,
  FileText,
  Bookmark,
  Trello,
  Video,
  Hash,
  Users,
  Disc,
  Plug,
  Calendar,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { Badge } from '@/components/ui/badge'
import type { ConnectorType } from '@/types'

const connectorMeta: Record<string, { icon: React.ElementType; label: string }> = {
  github: { icon: Github, label: 'GitHub' },
  gitlab: { icon: Bookmark, label: 'GitLab' },
  google_docs: { icon: FileText, label: 'Google Docs' },
  google_calendar: { icon: Calendar, label: 'Google Calendar' },
  notion: { icon: FileText, label: 'Notion' },
  confluence: { icon: FileText, label: 'Confluence' },
  jira: { icon: Trello, label: 'Jira' },
  linear: { icon: Trello, label: 'Linear' },
  slack: { icon: Hash, label: 'Slack' },
  teams: { icon: Users, label: 'Teams' },
  discord: { icon: Disc, label: 'Discord' },
  zoom: { icon: Video, label: 'Zoom' },
  custom: { icon: Plug, label: 'Custom' },
}

interface ConnectorBadgeProps {
  type: ConnectorType | string
  name?: string
  toolCount?: number
  enabled?: boolean
  size?: 'sm' | 'md'
  className?: string
}

export function ConnectorBadge({ type, name, toolCount, enabled = true, size = 'md', className }: ConnectorBadgeProps) {
  const meta = connectorMeta[type] || { icon: Plug, label: type }
  const Icon = meta.icon

  return (
    <div className={cn(
      'inline-flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900',
      size === 'sm' ? 'px-2 py-1' : 'px-2.5 py-1.5',
      !enabled && 'opacity-50',
      className
    )}>
      <Icon className={cn(
        'text-zinc-400',
        size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'
      )} />
      <span className={cn(
        'font-medium text-zinc-300',
        size === 'sm' ? 'text-[10px]' : 'text-xs'
      )}>{name || meta.label}</span>
      {toolCount !== undefined && (
        <Badge variant="default" className="text-[10px] px-1.5 py-0">{toolCount} tools</Badge>
      )}
      <span className={cn(
        'h-1.5 w-1.5 rounded-full',
        enabled ? 'bg-success-500' : 'bg-zinc-600'
      )} />
    </div>
  )
}
