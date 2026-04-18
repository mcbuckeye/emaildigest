import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Auth from '../pages/Auth'
import { AuthProvider } from '../contexts/AuthContext'

beforeEach(() => {
  vi.restoreAllMocks()
})

function renderAuth(mode: 'login' | 'signup') {
  return render(
    <MemoryRouter initialEntries={[mode === 'login' ? '/login' : '/signup']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Auth mode="login" />} />
          <Route path="/signup" element={<Auth mode="signup" />} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('Auth page', () => {
  it('signs up and redirects home', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url.endsWith('/api/auth/signup')) {
        return new Response(
          JSON.stringify({ id: 1, email: 'a@b.com', token: 'tok' }),
          { status: 201, headers: { 'Content-Type': 'application/json' } },
        )
      }
      if (url.endsWith('/api/auth/me')) {
        return new Response(
          JSON.stringify({ id: 1, email: 'a@b.com' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        )
      }
      return new Response('{}', { status: 404 })
    })

    renderAuth('signup')
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com')
    await userEvent.type(screen.getByLabelText('Password'), 'pw-123456')
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => expect(screen.getByText('Home')).toBeInTheDocument())
    expect(localStorage.getItem('token')).toBe('tok')
  })

  it('shows an error when login fails', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Invalid email or password' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    renderAuth('login')
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrongpass')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/invalid email or password/i),
    )
    expect(localStorage.getItem('token')).toBeNull()
  })
})
