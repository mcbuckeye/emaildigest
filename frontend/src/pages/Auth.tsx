import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface AuthProps {
  mode: 'login' | 'signup'
}

export default function Auth({ mode }: AuthProps) {
  const [formData, setFormData] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/signup'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: mode === 'login'
          ? { 'Content-Type': 'application/x-www-form-urlencoded' }
          : { 'Content-Type': 'application/json' },
        body: mode === 'login'
          ? new URLSearchParams({ username: formData.email, password: formData.password }).toString()
          : JSON.stringify({ email: formData.email, password: formData.password }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Authentication failed')
      }

      const data = await res.json()
      login(data.access_token || data.token)
      navigate('/')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
        <p>{mode === 'login' ? 'Sign in to your account' : 'Get started with EmailDigest'}</p>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              placeholder="you@example.com"
            />
          </div>

          <div className="input-group">
            <label>Password</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              placeholder="Min 8 characters"
            />
          </div>

          {error && (
            <div style={{ color: 'red', marginBottom: '16px', fontSize: '14px' }}>
              {error}
            </div>
          )}

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Loading...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <p style={{ marginTop: '24px', fontSize: '14px' }}>
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <Link
            to={mode === 'login' ? '/signup' : '/login'}
            style={{ color: '#667eea', textDecoration: 'none' }}
          >
            {mode === 'login' ? 'Sign up' : 'Log in'}
          </Link>
        </p>
      </div>
    </div>
  )
}
