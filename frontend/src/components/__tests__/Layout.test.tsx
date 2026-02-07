import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import Layout from '../Layout'

describe('Layout', () => {
  it('renders the main navigation', () => {
    render(<Layout />)

    // Check for navigation items (multiple instances for mobile/desktop)
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Tenants').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Pool').length).toBeGreaterThan(0)
  })

  it('renders the logo/title', () => {
    render(<Layout />)

    // Logo appears in both mobile and desktop nav
    expect(screen.getAllByText('Sage MCP').length).toBeGreaterThan(0)
  })

  it('has proper semantic structure', () => {
    render(<Layout />)

    // Should have nav and main elements (multiple navs for mobile/desktop)
    expect(screen.getAllByRole('navigation').length).toBeGreaterThan(0)
    expect(screen.getByRole('main')).toBeInTheDocument()
  })
})
