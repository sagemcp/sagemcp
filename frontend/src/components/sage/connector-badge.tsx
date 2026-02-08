import {
  Plug,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { Badge } from '@/components/ui/badge'
import type { ConnectorType } from '@/types'
import {
  GitHubLogo, SlackLogo, GoogleDocsLogo, JiraLogo, NotionLogo, ZoomLogo,
  GitLabLogo, BitbucketLogo, GoogleSheetsLogo, GmailLogo, GoogleSlidesLogo,
  ConfluenceLogo, LinearLogo, TeamsLogo, DiscordLogo, OutlookLogo,
  ExcelLogo, PowerPointLogo, CopilotLogo, ClaudeCodeLogo, CodexLogo,
  CursorLogo, WindsurfLogo,
} from '@/components/icons/BrandLogos'

const connectorMeta: Record<string, { icon: React.ElementType; label: string }> = {
  github: { icon: GitHubLogo, label: 'GitHub' },
  gitlab: { icon: GitLabLogo, label: 'GitLab' },
  bitbucket: { icon: BitbucketLogo, label: 'Bitbucket' },
  google_docs: { icon: GoogleDocsLogo, label: 'Google Docs' },
  google_sheets: { icon: GoogleSheetsLogo, label: 'Google Sheets' },
  gmail: { icon: GmailLogo, label: 'Gmail' },
  google_slides: { icon: GoogleSlidesLogo, label: 'Google Slides' },
  notion: { icon: NotionLogo, label: 'Notion' },
  confluence: { icon: ConfluenceLogo, label: 'Confluence' },
  jira: { icon: JiraLogo, label: 'Jira' },
  linear: { icon: LinearLogo, label: 'Linear' },
  slack: { icon: SlackLogo, label: 'Slack' },
  teams: { icon: TeamsLogo, label: 'Teams' },
  discord: { icon: DiscordLogo, label: 'Discord' },
  zoom: { icon: ZoomLogo, label: 'Zoom' },
  outlook: { icon: OutlookLogo, label: 'Outlook' },
  excel: { icon: ExcelLogo, label: 'Excel' },
  powerpoint: { icon: PowerPointLogo, label: 'PowerPoint' },
  copilot: { icon: CopilotLogo, label: 'GitHub Copilot' },
  claude_code: { icon: ClaudeCodeLogo, label: 'Claude Code' },
  codex: { icon: CodexLogo, label: 'OpenAI Codex' },
  cursor: { icon: CursorLogo, label: 'Cursor' },
  windsurf: { icon: WindsurfLogo, label: 'Windsurf' },
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
