import { useState, useEffect, useRef, useCallback } from 'react'

export interface LogEntry {
  timestamp: number
  level: string
  message: string
  logger: string
  tenant_slug?: string
  connector_id?: string
}

interface UseLogsOptions {
  level?: string
  tenantSlug?: string
  connectorId?: string
  paused?: boolean
  maxEntries?: number
}

export function useLogs(options: UseLogsOptions = {}) {
  const { level, tenantSlug, connectorId, paused = false, maxEntries = 500 } = options
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  const clear = useCallback(() => setEntries([]), [])

  useEffect(() => {
    if (paused) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
        setConnected(false)
      }
      return
    }

    const params = new URLSearchParams()
    if (level) params.set('level', level)
    if (tenantSlug) params.set('tenant_slug', tenantSlug)
    if (connectorId) params.set('connector_id', connectorId)

    const url = `/api/v1/admin/logs/stream${params.toString() ? '?' + params.toString() : ''}`
    const es = new EventSource(url)
    eventSourceRef.current = es

    es.addEventListener('connected', () => {
      setConnected(true)
    })

    es.addEventListener('log', (event) => {
      try {
        const entry: LogEntry = JSON.parse(event.data)
        setEntries(prev => {
          const next = [...prev, entry]
          return next.length > maxEntries ? next.slice(-maxEntries) : next
        })
      } catch {
        // ignore parse errors
      }
    })

    es.onerror = () => {
      setConnected(false)
    }

    return () => {
      es.close()
      eventSourceRef.current = null
      setConnected(false)
    }
  }, [level, tenantSlug, connectorId, paused, maxEntries])

  return { entries, connected, clear }
}
