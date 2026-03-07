import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '../../test/utils'
import MCPTesting from '../MCPTesting'
import * as api from '../../utils/api'

vi.mock('../../utils/api', () => ({
  tenantsApi: {
    list: vi.fn(),
  },
  connectorsApi: {
    list: vi.fn(),
  },
  mcpApi: {
    getInfo: vi.fn(),
    sendMessage: vi.fn(),
  },
}))

const mockTenantsApi = vi.mocked(api.tenantsApi)
const mockConnectorsApi = vi.mocked(api.connectorsApi)
const mockMcpApi = vi.mocked(api.mcpApi)

describe('MCPTesting validation UX', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    mockTenantsApi.list.mockResolvedValue({
      data: [{ slug: 'test-tenant', name: 'Test Tenant' }],
    } as any)

    mockConnectorsApi.list.mockResolvedValue({
      data: [{ id: 'connector-1', name: 'Test Connector', connector_type: 'external' }],
    } as any)

    mockMcpApi.getInfo.mockResolvedValue({
      data: {
        connector_name: 'Test Connector',
        connector_type: 'external',
        server_name: 'Test MCP',
        server_version: '1.0.0',
        protocol_version: '2024-11-05',
      },
    } as any)

    mockMcpApi.sendMessage.mockImplementation(
      (_tenant: string, _connector: string, payload: { method?: string } | undefined) => {
      if (payload?.method === 'tools/list') {
        return Promise.resolve({
          data: {
            result: {
              tools: [
                {
                  name: 'known_tool',
                  inputSchema: {
                    type: 'object',
                    properties: { value: { type: 'string' } },
                    required: ['value'],
                  },
                },
              ],
            },
          },
        } as any)
      }
      return Promise.resolve({ data: { ok: true } } as any)
      }
    )
  })

  async function setupAndSelectConnector() {
    render(<MCPTesting />)

    await waitFor(() => {
      expect(screen.getByText('MCP Protocol Testing')).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Test Tenant/ })).toBeInTheDocument()
    })

    const tenantSelect = screen.getAllByRole('combobox')[0]
    fireEvent.change(tenantSelect, {
      target: { value: 'test-tenant' },
    })

    await waitFor(() => {
      expect(screen.getByText('Select Connector')).toBeInTheDocument()
    })

    const connectorSelect = screen.getAllByRole('combobox')[1]
    fireEvent.change(connectorSelect, {
      target: { value: 'connector-1' },
    })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Send HTTP' })).toBeInTheDocument()
    })
  }

  it('shows syntax-level squiggle and disables send for malformed JSON', async () => {
    await setupAndSelectConnector()

    fireEvent.click(screen.getByRole('button', { name: 'Call Tool' }))

    const editor = document.getElementById('mcp-request-editor') as HTMLTextAreaElement
    expect(editor).not.toBeNull()

    fireEvent.change(editor, {
      target: {
        value: `{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "known_tool",
    "arguments": {},
  }
}`,
      },
    })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Send HTTP' })).toBeDisabled()
      expect(document.querySelector('.json-error-token')).not.toBeNull()
      expect(document.querySelector('.token.property')?.classList.contains('json-error-token')).toBe(false)
    })
  })

  it('marks only one duplicate key token for unknown tool name error', async () => {
    await setupAndSelectConnector()

    const editor = document.getElementById('mcp-request-editor') as HTMLTextAreaElement
    expect(editor).not.toBeNull()

    fireEvent.change(editor, {
      target: {
        value: `{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
            "name": "known_tool",
            "name": "",
            "arguments": {}
          }
        }`,
      },
    })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Send HTTP' })).toBeDisabled()
      const highlightedNameTokens = document.querySelectorAll('.json-error-token[data-error-key="name"]')
      expect(highlightedNameTokens.length).toBe(1)
    })
  })

})
