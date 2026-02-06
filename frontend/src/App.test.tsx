import { describe, it, expect } from 'vitest'
import { render, screen } from './test/utils'
import App from './App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    expect(screen.getAllByText('Sage MCP').length).toBeGreaterThan(0)
  })

  it('has navigation links', () => {
    render(<App />)

    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Tenants').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Pool').length).toBeGreaterThan(0)
  })

  it('renders the main content area', () => {
    render(<App />)
    
    // Should have a main element
    const main = screen.getByRole('main')
    expect(main).toBeInTheDocument()
  })
})