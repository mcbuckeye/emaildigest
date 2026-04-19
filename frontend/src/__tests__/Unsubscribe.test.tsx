import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Unsubscribe from '../pages/Unsubscribe'

describe('Unsubscribe page', () => {
  it('calls the unsubscribe API with the token from the URL', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Unsubscribed' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    render(
      <MemoryRouter initialEntries={['/unsubscribe?token=abc123']}>
        <Routes>
          <Route path="/unsubscribe" element={<Unsubscribe />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText(/Unsubscribed/)).toBeInTheDocument())
    const call = fetchMock.mock.calls[0]
    expect(String(call[0])).toBe('/api/unsubscribe/abc123')
  })
})
