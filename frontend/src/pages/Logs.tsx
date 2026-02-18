import { useState, useRef, useEffect } from 'react'
import {
  Play,
  Pause,
  Trash2,
  Download,
  Filter,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LiveIndicator } from '@/components/sage/live-indicator'
import { LogLine } from '@/components/sage/log-line'
import { useLogs } from '@/hooks/use-logs'

const LEVELS = ['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR']

export default function Logs() {
  const [paused, setPaused] = useState(false)
  const [level, setLevel] = useState('ALL')
  const [autoScroll, setAutoScroll] = useState(true)
  const containerRef = useRef<HTMLDivElement>(null)

  const { entries, connected, clear } = useLogs({
    level: level === 'ALL' ? undefined : level,
    paused,
  })

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [entries, autoScroll])

  const handleScroll = () => {
    if (!containerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
    setAutoScroll(isAtBottom)
  }

  const handleExport = () => {
    const text = entries
      .map(e => `${new Date(e.timestamp * 1000).toISOString()} [${e.level}] ${e.message}`)
      .join('\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `sagemcp-logs-${Date.now()}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-theme-primary">Logs</h1>
          <p className="text-sm text-theme-muted mt-1">Real-time structured log stream</p>
        </div>
        <div className="flex items-center gap-2">
          {connected && !paused && <LiveIndicator />}
          {paused && <Badge variant="warning">Paused</Badge>}
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 mb-3 p-2 rounded-lg border border-theme-default bg-surface-elevated">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setPaused(!paused)}
        >
          {paused ? <Play className="h-4 w-4 mr-1" /> : <Pause className="h-4 w-4 mr-1" />}
          {paused ? 'Resume' : 'Pause'}
        </Button>

        <Button variant="ghost" size="sm" onClick={clear}>
          <Trash2 className="h-4 w-4 mr-1" />
          Clear
        </Button>

        <Button variant="ghost" size="sm" onClick={handleExport}>
          <Download className="h-4 w-4 mr-1" />
          Export
        </Button>

        <div className="h-4 w-px bg-zinc-700 mx-1" />

        <Filter className="h-3.5 w-3.5 text-theme-muted" />
        <div className="flex items-center gap-1">
          {LEVELS.map(l => (
            <button
              key={l}
              onClick={() => setLevel(l)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                level === l
                  ? 'bg-accent/20 text-accent'
                  : 'text-theme-muted hover:text-theme-secondary hover:bg-theme-elevated'
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        <div className="ml-auto text-xs text-theme-muted">
          {entries.length} entries
        </div>
      </div>

      {/* Log output */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto rounded-lg border border-theme-default bg-[#0a0a0b]"
      >
        {entries.length === 0 ? (
          <div className="flex items-center justify-center h-full text-theme-muted text-sm">
            {paused ? 'Stream paused — click Resume to continue' : 'Waiting for log entries...'}
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/50">
            {entries.map((entry, i) => (
              <LogLine key={`${entry.timestamp}-${i}`} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
