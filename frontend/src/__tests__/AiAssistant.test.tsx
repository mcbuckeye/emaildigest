import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AiAssistant from '../pages/AiAssistant'

function sseBody(events: unknown[]) {
  const enc = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      for (const ev of events) {
        controller.enqueue(enc.encode(`data: ${JSON.stringify(ev)}\n\n`))
      }
      controller.close()
    },
  })
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

describe('AiAssistant (streaming)', () => {
  it('streams assistant tokens and renders a proposal', async () => {
    localStorage.setItem('token', 'tok')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      sseBody([
        { type: 'token', content: 'Found ' },
        { type: 'token', content: 'a feed!' },
        {
          type: 'final',
          reply: 'Found a feed!',
          tool_calls: [],
          proposed_digest: {
            name: 'AI News',
            frequency_cron: '0 9 * * 1',
            sources: [{ source_type: 'rss', url: 'https://example.com/feed.xml' }],
          },
        },
      ]),
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
