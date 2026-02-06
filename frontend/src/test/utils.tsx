import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'sonner'

// Create a custom render function that includes providers
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => render(ui, { wrapper: AllTheProviders, ...options })

export * from '@testing-library/react'
export { customRender as render }

// Mock data helpers
export const mockTenant = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  slug: 'test-tenant',
  name: 'Test Tenant',
  description: 'A test tenant',
  contact_email: 'test@example.com',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockConnector = {
  id: '123e4567-e89b-12d3-a456-426614174001',
  name: 'Test GitHub Connector',
  description: 'GitHub integration for testing',
  connector_type: 'github',
  is_enabled: true,
  configuration: {},
  tenant_id: mockTenant.id,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockOAuthConfig = {
  id: '123e4567-e89b-12d3-a456-426614174002',
  tenant_id: mockTenant.id,
  provider: 'github',
  client_id: 'test-client-id',
  client_secret: 'test-client-secret',
  scopes: 'repo,user:email,read:org',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}