import { useState, useRef, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import Editor from 'react-simple-code-editor'
import Prism from 'prismjs'
import 'prismjs/components/prism-json'
import Ajv, { ErrorObject } from 'ajv'
import { parse as parseJsonc, ParseError, printParseErrorCode } from 'jsonc-parser'
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
import { CodeBlock } from '@/components/sage/code-block'

interface TestMessage {
  id: string
  timestamp: string
  type: 'request' | 'response' | 'error' | 'info'
  content: any
  tenant: string
}

interface ToolDefinition {
  name: string
  description?: string
  inputSchema?: Record<string, unknown>
  input_schema?: Record<string, unknown>
}

interface ValidationErrorDetail {
  message: string
  path?: string
  propertyName?: string
  offset?: number
}

function formatAjvErrors(errors: ErrorObject[]): ValidationErrorDetail[] {
  return errors.map((error) => {
    if (error.keyword === 'required') {
      const missingProperty = (error.params as { missingProperty?: string }).missingProperty
      return {
        message: `arguments.${missingProperty ?? 'unknown'} is required`,
        path: missingProperty ? `/arguments/${missingProperty}` : '/arguments',
        propertyName: missingProperty,
      }
    }

    const path = error.instancePath ? `arguments${error.instancePath}` : 'arguments'
    const propertyName = error.instancePath.split('/').filter(Boolean).pop()
    return {
      message: `${path}: ${error.message ?? 'invalid value'}`,
      path: error.instancePath ? `/arguments${error.instancePath}` : '/arguments',
      propertyName: propertyName || undefined,
    }
  })
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
      default: return 'border-l-zinc-500 bg-theme-elevated'
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
          <Icon className="h-4 w-4 text-theme-secondary" />
          <span className="text-sm font-medium capitalize text-theme-primary">{message.type}</span>
          <span className="text-xs text-theme-muted">{message.tenant}</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-theme-muted">{message.timestamp}</span>
          <button
            onClick={() => onCopy(JSON.stringify(message.content, null, 2))}
            className="text-theme-muted hover:text-theme-secondary"
          >
            <Copy className="h-3 w-3" />
          </button>
        </div>
      </div>
      <CodeBlock
        code={JSON.stringify(message.content, null, 2)}
        language="json"
        className="text-xs"
      />
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
  const [debouncedRequestBody, setDebouncedRequestBody] = useState(requestBody)
  const [messages, setMessages] = useState<TestMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const editorContainerRef = useRef<HTMLDivElement | null>(null)
  const validatorCacheRef = useRef<Map<string, ReturnType<Ajv['compile']>>>(new Map())
  const [activeErrorKey, setActiveErrorKey] = useState<string | null>(null)

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

  const { data: availableTools = [] } = useQuery({
    queryKey: ['mcp-tools', selectedTenant, selectedConnector],
    queryFn: async () => {
      const response = await mcpApi.sendMessage(selectedTenant, selectedConnector, {
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'tools/list',
        params: {},
      })

      const data = response.data
      const tools = data?.result?.tools ?? data?.tools ?? []
      return Array.isArray(tools) ? (tools as ToolDefinition[]) : []
    },
    enabled: !!selectedTenant && !!selectedConnector,
    staleTime: 30_000,
  })

  const toolsByName = useMemo(
    () => new Map(availableTools.map((tool) => [tool.name, tool])),
    [availableTools]
  )

  const ajv = useMemo(() => new Ajv({ allErrors: true, strict: false }), [])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedRequestBody(requestBody), 400)
    return () => window.clearTimeout(timer)
  }, [requestBody])

  const requestPreview = useMemo(() => {
    const syntaxErrors: ParseError[] = []
    const data = parseJsonc(requestBody, syntaxErrors, {
      allowTrailingComma: true,
      disallowComments: false,
    }) as Record<string, any> | undefined
    return data && typeof data === 'object' ? data : null
  }, [requestBody])

  const parsedRequest = useMemo(() => {
    const syntaxErrors: ParseError[] = []
    const tolerantData = parseJsonc(debouncedRequestBody, syntaxErrors, {
      allowTrailingComma: true,
      disallowComments: false,
    }) as Record<string, any> | undefined

    let strictError: string | null = null
    let strictErrorOffset: number | null = null
    try {
      JSON.parse(debouncedRequestBody)
    } catch (error: any) {
      strictError = `Invalid JSON: ${error.message}`
      const positionMatch = String(error?.message ?? '').match(/position\s+(\d+)/i)
      strictErrorOffset = positionMatch ? Number.parseInt(positionMatch[1], 10) : null
    }

    return {
      data: tolerantData && typeof tolerantData === 'object' ? tolerantData : null,
      strictError,
      strictErrorOffset,
      syntaxErrors,
    }
  }, [debouncedRequestBody])

  const requestValidationErrors = useMemo(() => {
    const errors: ValidationErrorDetail[] = []
    if (parsedRequest.strictError) {
      errors.push({ message: parsedRequest.strictError, path: '/', offset: parsedRequest.strictErrorOffset ?? undefined })
    }

    for (const syntaxError of parsedRequest.syntaxErrors) {
      errors.push({
        message: `JSON syntax error: ${printParseErrorCode(syntaxError.error)} at offset ${syntaxError.offset}`,
        path: '/',
        offset: syntaxError.offset,
      })
    }

    const request = parsedRequest.data
    if (!request || request.method !== 'tools/call') {
      return errors
    }

    const toolName = request?.params?.name
    if (!toolName || typeof toolName !== 'string') {
      errors.push({ message: 'params.name is required for tools/call', path: '/params/name' })
      return errors
    }

    const tool = toolsByName.get(toolName)
    if (availableTools.length > 0 && !tool) {
      errors.push({
        message: `Unknown tool "${toolName}". Select a tool from available options.`,
        path: '/params/name',
      })
      return errors
    }

    const args = request?.params?.arguments ?? {}
    if (request?.params?.arguments !== undefined && typeof request?.params?.arguments !== 'object') {
      errors.push({ message: 'params.arguments must be an object', path: '/params/arguments' })
      return errors
    }

    const schema = tool?.inputSchema ?? tool?.input_schema
    if (!schema) {
      return errors
    }

    try {
      const cacheKey = `${toolName}:${JSON.stringify(schema)}`
      let validate = validatorCacheRef.current.get(cacheKey)
      if (!validate) {
        validate = ajv.compile(schema)
        validatorCacheRef.current.set(cacheKey, validate)
      }
      const isValid = validate(args)
      if (!isValid && validate.errors) {
        errors.push(...formatAjvErrors(validate.errors))
      }
    } catch (error: any) {
      errors.push({ message: `Failed to validate tool schema: ${error.message}`, path: '/params/arguments' })
    }

    return errors
  }, [ajv, parsedRequest, toolsByName, availableTools.length])

  const hasRequestValidationErrors = requestValidationErrors.length > 0
  const selectedToolName =
    requestPreview?.method === 'tools/call' && typeof requestPreview?.params?.name === 'string'
      ? requestPreview.params.name
      : ''

  const propertyErrorMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const error of requestValidationErrors) {
      if (error.propertyName) {
        map.set(error.propertyName, error.message)
        continue
      }

      // Map non-AJV errors to concrete request keys so squiggles appear.
      if (error.path === '/params/name') {
        map.set('name', error.message)
      } else if (error.path === '/params/arguments') {
        map.set('arguments', error.message)
      }
    }
    return map
  }, [requestValidationErrors])

  const syntaxErrorDetail = useMemo(() => {
    const syntaxErrors = requestValidationErrors.filter((error) => error.path === '/')
    if (syntaxErrors.length === 0) return null

    const withOffset = syntaxErrors.find((error) => Number.isInteger(error.offset))
    return {
      message: syntaxErrors.map((error) => error.message).join(' | '),
      offset: withOffset?.offset ?? null,
    }
  }, [requestValidationErrors])

  const highlightRequestJson = (value: string) => Prism.highlight(value, Prism.languages.json, 'json')

  const handleEditorMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    const textarea = event.currentTarget.querySelector('textarea')
    if (!(textarea instanceof HTMLTextAreaElement)) {
      if (activeErrorKey) setActiveErrorKey(null)
      return
    }

    // react-simple-code-editor renders a textarea overlay above highlighted tokens.
    // Temporarily disable hit-testing on textarea to resolve underlying token element.
    const previousPointerEvents = textarea.style.pointerEvents
    textarea.style.pointerEvents = 'none'
    const elements = document.elementsFromPoint(event.clientX, event.clientY)
    textarea.style.pointerEvents = previousPointerEvents || ''

    const errorToken = elements.find((el) =>
      el instanceof HTMLElement && el.classList.contains('json-error-token')
    ) as HTMLElement | undefined

    if (!errorToken) {
      if (activeErrorKey) setActiveErrorKey(null)
      return
    }

    const errorKey = errorToken.dataset.errorKey
    if (!errorKey) {
      if (activeErrorKey) setActiveErrorKey(null)
      return
    }

    if (activeErrorKey !== errorKey) {
      setActiveErrorKey(errorKey)
    }
  }

  const handleEditorMouseLeave = () => {
    if (activeErrorKey) setActiveErrorKey(null)
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const container = editorContainerRef.current
    if (!container) return

    const clearTokenErrorAttrs = (token: HTMLElement) => {
      token.classList.remove('json-error-token', 'json-error-token-active')
      delete token.dataset.errorKey
      delete token.dataset.errorMessage
    }

    const previouslyTaggedTokens = container.querySelectorAll('.json-error-token')
    previouslyTaggedTokens.forEach((tokenNode) => clearTokenErrorAttrs(tokenNode as HTMLElement))

    const consumedErrorKeys = new Set<string>()
    const propertyTokens = container.querySelectorAll('.token.property')
    propertyTokens.forEach((tokenNode) => {
      const token = tokenNode as HTMLElement

      const rawText = token.textContent ?? ''
      if (!rawText.startsWith('"') || !rawText.endsWith('"')) return
      const propertyName = rawText.slice(1, -1)
      if (consumedErrorKeys.has(propertyName)) return
      const errorMessage = propertyErrorMap.get(propertyName)
      if (!errorMessage) return

      token.classList.add('json-error-token')
      if (activeErrorKey === propertyName) {
        token.classList.add('json-error-token-active')
      }
      token.dataset.errorKey = propertyName
      token.dataset.errorMessage = errorMessage
      consumedErrorKeys.add(propertyName)
    })

    const findTokenAtOffset = (targetOffset: number): HTMLElement | null => {
      const root = container.querySelector('pre') ?? container
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
      let currentOffset = 0

      while (walker.nextNode()) {
        const textNode = walker.currentNode as Text
        const nextOffset = currentOffset + textNode.data.length
        if (targetOffset < nextOffset) {
          let element: HTMLElement | null = textNode.parentElement
          while (element && !element.classList.contains('token')) {
            element = element.parentElement
          }
          return element
        }
        currentOffset = nextOffset
      }

      return null
    }

    // Attach syntax-level errors to the token closest to the parser offset.
    const firstToken = container.querySelector(
      '.token.property, .token.string, .token.number, .token.boolean, .token.null, .token.punctuation'
    ) as HTMLElement | null

    const syntaxToken =
      syntaxErrorDetail && Number.isInteger(syntaxErrorDetail.offset)
        ? findTokenAtOffset(syntaxErrorDetail.offset as number) ?? firstToken
        : firstToken

    if (syntaxToken && syntaxErrorDetail) {
      syntaxToken.classList.add('json-error-token')
      if (activeErrorKey === '__syntax__') {
        syntaxToken.classList.add('json-error-token-active')
      }
      syntaxToken.dataset.errorKey = '__syntax__'
      syntaxToken.dataset.errorMessage = syntaxErrorDetail.message
    }
  }, [debouncedRequestBody, propertyErrorMap, syntaxErrorDetail, activeErrorKey])

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

    if (hasRequestValidationErrors) {
      toast.error('Fix request validation errors before sending')
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

    if (hasRequestValidationErrors) {
      toast.error('Fix request validation errors before sending')
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

  const setToolNameInRequest = (toolName: string) => {
    try {
      const syntaxErrors: ParseError[] = []
      const request = parseJsonc(requestBody, syntaxErrors, {
        allowTrailingComma: true,
        disallowComments: false,
      }) as Record<string, any> | undefined
      if (!request || typeof request !== 'object') {
        return
      }
      if (request.method !== 'tools/call') {
        return
      }
      request.params = request.params || {}
      request.params.name = toolName
      request.params.arguments = request.params.arguments || {}
      setRequestBody(JSON.stringify(request, null, 2))
    } catch {
      // ignore invalid JSON in editor
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
        <h1 className="text-2xl font-bold text-theme-primary">MCP Protocol Testing</h1>
        <p className="text-theme-secondary">Test and debug MCP connections with your tenants</p>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="lg:col-span-1">
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-theme-primary">Configuration</h3>
            </div>
            <div className="card-content space-y-4">
              {/* Tenant Selection */}
              <div>
                <label className="block text-sm font-medium text-theme-secondary mb-1">
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
                  <label className="block text-sm font-medium text-theme-secondary mb-1">
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
                <div className="text-sm text-theme-muted italic">
                  No connectors found for this tenant
                </div>
              )}

              {/* Connection Status */}
              {selectedTenant && selectedConnector && mcpInfo && (
                <div className="p-3 bg-theme-elevated rounded-lg">
                  <h4 className="text-sm font-medium text-theme-primary mb-2">MCP Server Info</h4>
                  <div className="space-y-1 text-xs text-theme-secondary">
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
                  <span className="text-sm font-medium text-theme-secondary">WebSocket</span>
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
                <label className="block text-sm font-medium text-theme-secondary mb-1">
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
                <h3 className="text-lg font-semibold text-theme-primary">Request</h3>
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
              <div
                ref={editorContainerRef}
                className="border border-theme-default rounded-lg bg-theme-surface overflow-hidden relative"
                onMouseMove={handleEditorMouseMove}
                onMouseLeave={handleEditorMouseLeave}
              >
                <Editor
                  value={requestBody}
                  onValueChange={(value) => setRequestBody(value)}
                  highlight={highlightRequestJson}
                  padding={12}
                  textareaId="mcp-request-editor"
                  className="mcp-json-editor text-sm font-mono text-theme-primary min-h-64"
                  style={{
                    fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace',
                    whiteSpace: 'pre',
                    overflow: 'auto',
                  }}
                />
              </div>

              {requestPreview?.method === 'tools/call' && (
                <div className="mt-3">
                  <div>
                    <label className="block text-sm font-medium text-theme-secondary mb-1">
                      Tool name (from tools/list)
                    </label>
                    <select
                      value={selectedToolName}
                      onChange={(e) => setToolNameInRequest(e.target.value)}
                      className="input-field"
                    >
                      <option value="">Select a tool...</option>
                      {availableTools.map((tool) => (
                        <option key={tool.name} value={tool.name}>
                          {tool.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              <div className="flex justify-end space-x-2 mt-4">
                <button
                  onClick={sendHttpRequest}
                  disabled={!selectedTenant || !selectedConnector || isLoading || hasRequestValidationErrors}
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
                  disabled={!isConnected || hasRequestValidationErrors}
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
            <h3 className="text-lg font-semibold text-theme-primary">
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
              <Settings className="h-12 w-12 text-theme-muted mx-auto mb-4" />
              <h3 className="text-lg font-medium text-theme-primary mb-2">No messages yet</h3>
              <p className="text-theme-secondary">Send your first MCP request to see messages here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
