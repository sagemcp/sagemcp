import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '../../test/utils'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Tenants from '../Tenants'
import * as api from '../../utils/api'

// Mock the API
vi.mock('../../utils/api', () => ({
  tenantsApi: {
    list: vi.fn(),
    create: vi.fn(),
    get: vi.fn(),
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

const mockTenantsApi = vi.mocked(api.tenantsApi)
const mockConnectorsApi = vi.mocked(api.connectorsApi)

describe('Tenants', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    })
    vi.clearAllMocks()
    mockConnectorsApi.list.mockResolvedValue({ data: [] } as any)
  })

  const renderWithClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  it('renders tenants page with title', () => {
    mockTenantsApi.list.mockResolvedValue({ data: [] } as any)

    renderWithClient(<Tenants />)

    expect(screen.getByText('Tenants')).toBeInTheDocument()
    expect(screen.getByText('Create Tenant')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    mockTenantsApi.list.mockImplementation(() => new Promise(() => { /* Never resolves */ }))

    renderWithClient(<Tenants />)

    // Loading state shows skeleton cards with animation
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('displays tenants when loaded', async () => {
    const mockTenants = [
      {
        id: '1',
        slug: 'tenant-1',
        name: 'Tenant 1',
        description: 'First tenant',
        contact_email: 'tenant1@example.com',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        id: '2',
        slug: 'tenant-2',
        name: 'Tenant 2',
        description: 'Second tenant',
        contact_email: 'tenant2@example.com',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ]

    mockTenantsApi.list.mockResolvedValue({ data: mockTenants } as any)

    renderWithClient(<Tenants />)

    await waitFor(() => {
      expect(screen.getByText('Tenant 1')).toBeInTheDocument()
      expect(screen.getByText('Tenant 2')).toBeInTheDocument()
    })
  })

  it('shows empty state when no tenants', async () => {
    mockTenantsApi.list.mockResolvedValue({ data: [] } as any)

    renderWithClient(<Tenants />)

    await waitFor(() => {
      expect(screen.getByText('No tenants yet')).toBeInTheDocument()
    })
  })

  it('handles error state', async () => {
    mockTenantsApi.list.mockRejectedValue(new Error('Failed to fetch'))

    renderWithClient(<Tenants />)

    // Error state is handled by React Query, which may show empty state
    await waitFor(() => {
      // Query will show empty array on error by default
      expect(screen.getByText('No tenants yet')).toBeInTheDocument()
    })
  })

  it('opens create tenant sheet when button clicked', async () => {
    mockTenantsApi.list.mockResolvedValue({ data: [] } as any)

    renderWithClient(<Tenants />)

    const createButton = screen.getAllByText('Create Tenant')[0]
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText('Set up a new multi-tenant MCP environment')).toBeInTheDocument()
    })
  })
})
