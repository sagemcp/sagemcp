import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  Play,
  Send,
  Copy,
  Download,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Trash2,
  Settings
} from 'lucide-react'
import { tenantsApi, connectorsApi, mcpApi } from '@/utils/api'
import { cn } from '@/utils/cn'
import { toast } from 'sonner'

interface TestMessage {
  id: string
  timestamp: string
  type: 'request' | 'response' | 'error' | 'info'
  content: any
  tenant: string
}

const MessageCard = ({
  message,
  onCopy
}: {
  message: TestMessage
  onCopy: (content: string) => void
}) => {
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'request': return 'border-l-accent bg-accent/10'
      case 'response': return 'border-l-green-500 bg-green-500/10'
      case 'error': return 'border-l-red-500 bg-red-500/10'
      default: return 'border-l-zinc-500 bg-zinc-800'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'request': return Send
      case 'response': return CheckCircle
      case 'error': return AlertCircle
      default: return Settings
    }
  }

  const Icon = getTypeIcon(message.type)

  return (
    <div className={cn('border-l-4 rounded-r-lg p-4', getTypeColor(message.type))}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <Icon className="h-4 w-4 text-zinc-300" />
          <span className="text-sm font-medium capitalize text-zinc-200">{message.type}</span>
          <span className="text-xs text-zinc-500">{message.tenant}</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-zinc-500">{message.timestamp}</span>
          <button
            onClick={() => onCopy(JSON.stringify(message.content, null, 2))}
            className="text-zinc-500 hover:text-zinc-300"
          >
            <Copy className="h-3 w-3" />
          </button>
        </div>
      </div>
      <pre className="text-xs text-zinc-300 bg-zinc-900 p-2 rounded border border-zinc-700 overflow-x-auto">
        {JSON.stringify(message.content, null, 2)}
      </pre>
    </div>
  )
}

const RequestTemplates = {
  'List Tools': {
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/list',
    params: {}
  },
  'List Resources': {
    jsonrpc: '2.0',
    id: 2,
    method: 'resources/list',
    params: {}
  },
  'Call Tool': {
    jsonrpc: '2.0',
    id: 3,
    method: 'tools/call',
    params: {
      name: 'example.tool',
      arguments: {}
    }
  },
  'Read Resource': {
    jsonrpc: '2.0',
    id: 4,
    method: 'resources/read',
    params: {
      uri: 'example://resource'
    }
  }
}

export default function MCPTesting() {
  const [searchParams] = useSearchParams()
  const [selectedTenant, setSelectedTenant] = useState(searchParams.get('tenant') || '')
  const [selectedConnector, setSelectedConnector] = useState('')
  const [requestBody, setRequestBody] = useState(JSON.stringify(RequestTemplates['List Tools'], null, 2))
  const [messages, setMessages] = useState<TestMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { data: tenants = [] } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then(res => res.data)
  })

  const { data: connectors = [] } = useQuery({
    queryKey: ['connectors', selectedTenant],
    queryFn: () => connectorsApi.list(selectedTenant).then(res => res.data),
    enabled: !!selectedTenant
  })

  const { data: mcpInfo } = useQuery({
    queryKey: ['mcp-info', selectedTenant, selectedConnector],
    queryFn: () => mcpApi.getInfo(selectedTenant, selectedConnector).then(res => res.data),
    enabled: !!selectedTenant && !!selectedConnector
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const connectWebSocket = () => {
    if (!selectedTenant) {
      toast.error('Please select a tenant first')
      return
    }

    if (!selectedConnector) {
      toast.error('Please select a connector first')
      return
    }

    if (wsRef.current) {
      wsRef.current.close()
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/${selectedTenant}/connectors/${selectedConnector}/mcp`

    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onopen = () => {
      setIsConnected(true)
      addMessage('info', { status: 'WebSocket connected' }, 'system')
      toast.success('WebSocket connected')
    }

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        addMessage('response', data, selectedTenant)
      } catch (error) {
        addMessage('error', { error: 'Failed to parse response', raw: event.data }, selectedTenant)
      }
    }

    wsRef.current.onerror = () => {
      addMessage('error', { error: 'WebSocket connection error' }, 'system')
      toast.error('WebSocket connection error')
    }

    wsRef.current.onclose = () => {
      setIsConnected(false)
      addMessage('info', { status: 'WebSocket disconnected' }, 'system')
    }
  }

  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }

  const addMessage = (type: TestMessage['type'], content: any, tenant: string) => {
    const message: TestMessage = {
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString(),
      type,
      content,
      tenant
    }
    setMessages(prev => [...prev, message])
  }

  const sendHttpRequest = async () => {
    if (!selectedTenant) {
      toast.error('Please select a tenant first')
      return
    }

    if (!selectedConnector) {
      toast.error('Please select a connector first')
      return
    }

    try {
      setIsLoading(true)
      const requestData = JSON.parse(requestBody)

      addMessage('request', requestData, selectedTenant)

      const response = await mcpApi.sendMessage(selectedTenant, selectedConnector, requestData)
      addMessage('response', response.data, selectedTenant)

      toast.success('Request sent successfully')
    } catch (error: any) {
      const errorData = error.response?.data || { error: error.message }
      addMessage('error', errorData, selectedTenant)
      toast.error('Request failed')
    } finally {
      setIsLoading(false)
    }
  }

  const sendWebSocketMessage = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error('WebSocket not connected')
      return
    }

    try {
      const requestData = JSON.parse(requestBody)
      wsRef.current.send(JSON.stringify(requestData))
      addMessage('request', requestData, selectedTenant)
    } catch (error) {
      toast.error('Invalid JSON format')
    }
  }

  const loadTemplate = (templateName: string) => {
    const template = RequestTemplates[templateName as keyof typeof RequestTemplates]
    if (template) {
      setRequestBody(JSON.stringify(template, null, 2))
    }
  }

  const copyToClipboard = (content: string) => {
    navigator.clipboard.writeText(content)
    toast.success('Copied to clipboard')
  }

  const clearMessages = () => {
    setMessages([])
  }

  const exportMessages = () => {
    const data = JSON.stringify(messages, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mcp-test-${selectedTenant}-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">MCP Protocol Testing</h1>
        <p className="text-zinc-400">Test and debug MCP connections with your tenants</p>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="lg:col-span-1">
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-zinc-100">Configuration</h3>
            </div>
            <div className="card-content space-y-4">
              {/* Tenant Selection */}
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">
                  Select Tenant
                </label>
                <select
                  value={selectedTenant}
                  onChange={(e) => {
                    setSelectedTenant(e.target.value)
                    setSelectedConnector('') // Reset connector when tenant changes
                  }}
                  className="input-field"
                >
                  <option value="">Choose a tenant...</option>
                  {tenants.map(tenant => (
                    <option key={tenant.slug} value={tenant.slug}>
                      {tenant.name} ({tenant.slug})
                    </option>
                  ))}
                </select>
              </div>

              {/* Connector Selection */}
              {selectedTenant && (
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">
                    Select Connector
                  </label>
                  <select
                    value={selectedConnector}
                    onChange={(e) => setSelectedConnector(e.target.value)}
                    className="input-field"
                  >
                    <option value="">Choose a connector...</option>
                    {connectors.map(connector => (
                      <option key={connector.id} value={connector.id}>
                        {connector.name} ({connector.connector_type})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Reset connector when tenant changes */}
              {selectedTenant && connectors.length === 0 && (
                <div className="text-sm text-zinc-500 italic">
                  No connectors found for this tenant
                </div>
              )}

              {/* Connection Status */}
              {selectedTenant && selectedConnector && mcpInfo && (
                <div className="p-3 bg-zinc-800 rounded-lg">
                  <h4 className="text-sm font-medium text-zinc-100 mb-2">MCP Server Info</h4>
                  <div className="space-y-1 text-xs text-zinc-400">
                    <div>Connector: {mcpInfo.connector_name}</div>
                    <div>Type: {mcpInfo.connector_type}</div>
                    <div>Server: {mcpInfo.server_name} v{mcpInfo.server_version}</div>
                    <div>Protocol: {mcpInfo.protocol_version}</div>
                  </div>
                </div>
              )}

              {/* WebSocket Controls */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-zinc-300">WebSocket</span>
                  <span className={cn(
                    'status-badge',
                    isConnected ? 'status-active' : 'status-inactive'
                  )}>
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="flex space-x-2">
                  {!isConnected ? (
                    <button
                      onClick={connectWebSocket}
                      disabled={!selectedTenant || !selectedConnector}
                      className="btn-primary flex-1"
                    >
                      Connect
                    </button>
                  ) : (
                    <button
                      onClick={disconnectWebSocket}
                      className="btn-secondary flex-1"
                    >
                      Disconnect
                    </button>
                  )}
                </div>
              </div>

              {/* Request Templates */}
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">
                  Quick Templates
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {Object.keys(RequestTemplates).map(template => (
                    <button
                      key={template}
                      onClick={() => loadTemplate(template)}
                      className="btn-ghost text-xs"
                    >
                      {template}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Request Panel */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-zinc-100">Request</h3>
                <div className="flex space-x-2">
                  <button
                    onClick={() => copyToClipboard(requestBody)}
                    className="btn-ghost btn-sm"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
            <div className="card-content">
              <textarea
                value={requestBody}
                onChange={(e) => setRequestBody(e.target.value)}
                className="w-full h-64 font-mono text-sm bg-theme-surface border border-theme-hover rounded-lg p-3 text-theme-primary placeholder:text-theme-muted focus:border-accent focus:ring-1 focus:ring-accent"
                placeholder="Enter your MCP request JSON..."
              />

              <div className="flex justify-end space-x-2 mt-4">
                <button
                  onClick={sendHttpRequest}
                  disabled={!selectedTenant || !selectedConnector || isLoading}
                  className="btn-secondary"
                >
                  {isLoading ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4 mr-2" />
                  )}
                  Send HTTP
                </button>
                <button
                  onClick={sendWebSocketMessage}
                  disabled={!isConnected}
                  className="btn-primary"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Send WebSocket
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Messages Panel */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-zinc-100">
              Messages ({messages.length})
            </h3>
            <div className="flex space-x-2">
              <button
                onClick={exportMessages}
                disabled={messages.length === 0}
                className="btn-ghost btn-sm"
              >
                <Download className="h-4 w-4" />
              </button>
              <button
                onClick={clearMessages}
                disabled={messages.length === 0}
                className="btn-ghost btn-sm text-red-400"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
        <div className="card-content">
          {messages.length > 0 ? (
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {messages.map((message) => (
                <MessageCard
                  key={message.id}
                  message={message}
                  onCopy={copyToClipboard}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          ) : (
            <div className="text-center py-8">
              <Settings className="h-12 w-12 text-zinc-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-zinc-100 mb-2">No messages yet</h3>
              <p className="text-zinc-400">Send your first MCP request to see messages here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
