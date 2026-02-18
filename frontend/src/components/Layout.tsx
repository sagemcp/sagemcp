import React from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  Server,
  ScrollText,
  Settings,
  ExternalLink,
  Menu,
  X,
  ChevronLeft,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { StatusDot } from '@/components/sage/status-dot'
import { CommandPalette } from '@/components/layout/command-palette'
import { useStats } from '@/hooks/use-stats'
import logo from '@/assets/logo.svg'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Tenants', href: '/tenants', icon: Building2 },
  { name: 'Pool', href: '/pool', icon: Server },
  { name: 'Logs', href: '/logs', icon: ScrollText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Layout() {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = React.useState(false)
  const [collapsed, setCollapsed] = React.useState(false)
  const { data: stats } = useStats()

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/'
    return location.pathname.startsWith(href)
  }

  const sidebarWidth = collapsed ? 'w-16' : 'w-60'
  const contentPadding = collapsed ? 'lg:pl-16' : 'lg:pl-60'

  return (
    <div className="min-h-screen bg-[var(--bg-root)]">
      {/* Mobile sidebar overlay */}
      <div className={cn(
        'fixed inset-0 z-50 lg:hidden',
        sidebarOpen ? 'block' : 'hidden'
      )}>
        <div className="fixed inset-0 bg-black/60" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 w-60 bg-theme-surface border-r border-theme-default flex flex-col">
          <div className="flex h-14 items-center justify-between px-4 border-b border-theme-default">
            <Link to="/" className="flex items-center gap-2">
              <img src={logo} alt="Sage MCP" className="h-7 w-7 rounded-md" />
              <span className="text-sm font-semibold text-theme-primary">Sage MCP</span>
            </Link>
            <button onClick={() => setSidebarOpen(false)} className="text-theme-muted hover:text-theme-secondary">
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="flex-1 py-3 space-y-0.5 px-2">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive(item.href)
                    ? 'bg-accent/10 text-accent border-l-2 border-accent ml-0 pl-[10px]'
                    : 'text-theme-secondary hover:bg-theme-elevated hover:text-theme-primary'
                )}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                {item.name}
              </Link>
            ))}
          </nav>
          <div className="p-3 border-t border-theme-default">
            <a
              href="https://github.com/sagemcp/sagemcp"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-xs text-theme-muted hover:text-theme-secondary hover:bg-theme-elevated transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Docs
            </a>
          </div>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className={cn(
        'hidden lg:fixed lg:inset-y-0 lg:flex lg:flex-col lg:border-r lg:border-theme-default lg:bg-theme-surface transition-all duration-200',
        sidebarWidth
      )}>
        <div className="flex h-14 items-center px-4 border-b border-theme-default justify-between">
          <Link to="/" className="flex items-center gap-2 overflow-hidden">
            <img src={logo} alt="Sage MCP" className="h-7 w-7 rounded-md shrink-0" />
            {!collapsed && <span className="text-sm font-semibold text-theme-primary truncate">Sage MCP</span>}
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="text-theme-muted hover:text-theme-secondary transition-colors shrink-0"
          >
            <ChevronLeft className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')} />
          </button>
        </div>
        <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-hidden">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              title={collapsed ? item.name : undefined}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive(item.href)
                  ? 'bg-accent/10 text-accent border-l-2 border-accent pl-[10px]'
                  : 'text-theme-secondary hover:bg-theme-elevated hover:text-theme-primary',
                collapsed && 'justify-center px-2'
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.name}</span>}
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-theme-default">
          <a
            href="https://github.com/sagemcp/sagemcp"
            target="_blank"
            rel="noopener noreferrer"
            title={collapsed ? 'Docs' : undefined}
            className={cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-xs text-theme-muted hover:text-theme-secondary hover:bg-theme-elevated transition-colors',
              collapsed && 'justify-center px-2'
            )}
          >
            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
            {!collapsed && 'Docs'}
          </a>
        </div>
      </div>

      {/* Main content */}
      <div className={cn('transition-all duration-200', contentPadding)}>
        {/* Top bar */}
        <div className="sticky top-0 z-40 bg-[var(--bg-root)]/80 backdrop-blur-sm border-b border-theme-default">
          <div className="flex h-14 items-center justify-between px-4 sm:px-6 lg:px-8">
            <button
              className="lg:hidden text-theme-secondary hover:text-theme-primary"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>

            {/* Stats strip */}
            <div className="hidden sm:flex items-center gap-6 text-xs text-theme-muted">
              {stats && (
                <>
                  <span>
                    <span className="text-theme-secondary font-medium">{stats.tenants}</span> tenants
                  </span>
                  <span>
                    <span className="text-theme-secondary font-medium">{stats.active_instances}</span> instances
                  </span>
                  <span>
                    <span className="text-theme-secondary font-medium">{stats.active_sessions}</span> sessions
                  </span>
                </>
              )}
            </div>

            {/* Health indicator */}
            <div className="flex items-center gap-2">
              <StatusDot variant="healthy" size="sm" />
              <span className="text-xs text-theme-secondary">Healthy</span>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>

      {/* Command Palette */}
      <CommandPalette />
    </div>
  )
}
