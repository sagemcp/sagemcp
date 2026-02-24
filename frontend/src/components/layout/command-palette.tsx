import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Command } from 'cmdk'
import {
  LayoutDashboard,
  Building2,
  Server,
  ScrollText,
  Settings,
  Search,
} from 'lucide-react'
import { tenantsApi } from '@/utils/api'

const PAGES = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Tenants', path: '/tenants', icon: Building2 },
  { name: 'Server Pool', path: '/pool', icon: Server },
  { name: 'Logs', path: '/logs', icon: ScrollText },
  { name: 'Settings', path: '/settings', icon: Settings },
]

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const { data: tenants = [] } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then(res => res.data),
    enabled: open,
  })

  // Toggle on Cmd+K / Ctrl+K
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(prev => !prev)
      }
      if (e.key === 'Escape') {
        setOpen(false)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  const runCommand = (path: string) => {
    setOpen(false)
    navigate(path)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />

      {/* Dialog */}
      <div className="fixed left-1/2 top-[20%] -translate-x-1/2 w-full max-w-lg">
        <Command
          className="rounded-lg border border-theme-default bg-theme-surface shadow-2xl overflow-hidden"
          label="Command palette"
        >
          <div className="flex items-center gap-2 px-4 border-b border-theme-default">
            <Search className="h-4 w-4 text-theme-muted shrink-0" />
            <Command.Input
              placeholder="Search pages, tenants..."
              className="w-full py-3 bg-transparent text-sm text-theme-primary placeholder:text-theme-muted focus:outline-none"
            />
            <kbd className="shrink-0 text-[10px] font-mono text-theme-muted bg-theme-elevated px-1.5 py-0.5 rounded">ESC</kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-theme-muted">
              No results found.
            </Command.Empty>

            <Command.Group heading="Pages" className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-theme-muted [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
              {PAGES.map(page => (
                <Command.Item
                  key={page.path}
                  value={page.name}
                  onSelect={() => runCommand(page.path)}
                  className="flex items-center gap-3 px-3 py-2 text-sm text-theme-secondary rounded-md cursor-pointer data-[selected=true]:bg-theme-elevated data-[selected=true]:text-theme-primary"
                >
                  <page.icon className="h-4 w-4 text-theme-muted" />
                  {page.name}
                </Command.Item>
              ))}
            </Command.Group>

            {tenants.length > 0 && (
              <Command.Group heading="Tenants" className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-theme-muted [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
                {tenants.map(tenant => (
                  <Command.Item
                    key={tenant.slug}
                    value={`${tenant.name} ${tenant.slug}`}
                    onSelect={() => runCommand(`/tenants/${tenant.slug}`)}
                    className="flex items-center gap-3 px-3 py-2 text-sm text-theme-secondary rounded-md cursor-pointer data-[selected=true]:bg-theme-elevated data-[selected=true]:text-theme-primary"
                  >
                    <Building2 className="h-4 w-4 text-theme-muted" />
                    <div>
                      <div>{tenant.name}</div>
                      <div className="text-xs text-theme-muted font-mono">{tenant.slug}</div>
                    </div>
                  </Command.Item>
                ))}
              </Command.Group>
            )}
          </Command.List>
        </Command>
      </div>
    </div>
  )
}
