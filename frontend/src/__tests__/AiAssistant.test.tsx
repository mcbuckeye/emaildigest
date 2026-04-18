import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AiAssistant from '../pages/AiAssistant'

describe('AiAssistant', () => {
  it('sends a message and shows the assistant reply + proposal', async () => {
    localStorage.setItem('token', 'tok')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          reply: 'Found a feed!',
          tool_calls: [],
          proposed_digest: {
            name: 'AI News',
            frequency_cron: '0 9 * * 1',
            sources: [{ source_type: 'rss', url: 'https://example.com/feed.xml' }],
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    render(
      <MemoryRouter>
        <AiAssistant />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText('message'), 'weekly AI news')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() => expect(screen.getByText('Found a feed!')).toBeInTheDocument())
    expect(screen.getByText(/Proposed digest/i)).toBeInTheDocument()
    expect(screen.getByText(/rss:/)).toBeInTheDocument()
  })
})
