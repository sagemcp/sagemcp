import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TenantDetail from '../TenantDetail'
import * as api from '../../utils/api'

vi.mock('../../utils/api', () => ({
  tenantsApi: {
    get: vi.fn(),
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  connectorsApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    toggle: vi.fn(),
  },
}))

vi.mock('../../hooks/use-sessions', () => ({
  useSessions: vi.fn(() => ({ data: [], isLoading: false })),
  useTerminateSession: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

const mockTenantsApi = vi.mocked(api.tenantsApi)
const mockConnectorsApi = vi.mocked(api.connectorsApi)

describe('TenantDetail config presets', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, cacheTime: 0 },
        mutations: { retry: false },
      },
    })
    vi.clearAllMocks()

    mockTenantsApi.get.mockResolvedValue({
      data: {
        id: 'tenant-id-1',
        slug: 'test-tenant',
        name: 'Test Tenant',
        description: 'Tenant used for tests',
        contact_email: 'tenant@example.com',
        is_active: true,
        created_at: '2026-02-15T00:00:00Z',
        updated_at: '2026-02-15T00:00:00Z',
      },
    } as any)

    mockConnectorsApi.list.mockResolvedValue({
      data: [
        {
          id: 'connector-id-1',
          tenant_id: 'tenant-id-1',
          name: 'GitHub',
          connector_type: 'github',
          runtime_type: 'native',
          is_enabled: true,
          configuration: {},
          created_at: '2026-02-15T00:00:00Z',
          updated_at: '2026-02-15T00:00:00Z',
        },
      ],
    } as any)
  })

  const renderPage = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/tenants/test-tenant']}>
          <Routes>
            <Route path="/tenants/:slug" element={<TenantDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )

  const getConfigCodeText = () => {
    const codeNode = document.querySelector('pre code')
    expect(codeNode).not.toBeNull()
    return codeNode?.textContent || ''
  }

  it('defaults to mcpServers + direct url config', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Client Config')).toBeInTheDocument()
    })

    const code = getConfigCodeText()
    expect(code).toContain('"mcpServers"')
    expect(code).toContain('"url"')
    expect(code).not.toContain('mcp-remote')
  })

  it('switches to mcp-remote config when connection mode changes', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByLabelText('Connection mode')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText('Connection mode'), {
      target: { value: 'mcp_remote' },
    })

    await waitFor(() => {
      const code = getConfigCodeText()
      expect(code).toContain('"command"')
      expect(code).toContain('"npx"')
      expect(code).toContain('mcp-remote')
    })
  })

  it('switches to vscode-style config preset', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByLabelText('Client preset')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText('Client preset'), {
      target: { value: 'vscode_json' },
    })

    await waitFor(() => {
      const code = getConfigCodeText()
      expect(code).toContain('"mcp"')
      expect(code).toContain('"servers"')
    })
  })
})
