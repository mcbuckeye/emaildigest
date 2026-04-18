import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from '../pages/Dashboard'

describe('Dashboard', () => {
  it('shows empty state when there are no digests', async () => {
    localStorage.setItem('token', 'tok')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText(/No digests yet/i)).toBeInTheDocument())
  })

  it('renders digests returned from the API', async () => {
    localStorage.setItem('token', 'tok')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: 1,
            name: 'AI News',
            description: 'Weekly',
            frequency_cron: '0 9 * * 1',
            status: 'active',
            recipient_email: 'me@x.com',
            next_run_at: null,
            last_run_at: null,
            sources: [],
            created_at: '2026-01-01T00:00:00',
            updated_at: '2026-01-01T00:00:00',
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('AI News')).toBeInTheDocument())
    expect(screen.getByText('active')).toBeInTheDocument()
  })
})
