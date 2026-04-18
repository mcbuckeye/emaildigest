import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../contexts/AuthContext'

interface AuthProps {
  mode: 'login' | 'signup'
}

export default function Auth({ mode }: AuthProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (mode === 'signup') {
        const res = await api.signup(email, password)
        await login(res.token)
      } else {
        const res = await api.login(email, password)
        await login(res.access_token)
      }
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
        <p>{mode === 'login' ? 'Sign in to your account' : 'Get started with EmailDigest'}</p>

        <form onSubmit={handleSubmit} aria-label={mode}>
          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
            />
          </div>
          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Min 8 characters"
              minLength={8}
            />
          </div>

          {error && <div role="alert" style={{ color: 'red', marginBottom: '16px' }}>{error}</div>}

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Loading...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <p style={{ marginTop: '16px', fontSize: '14px' }}>
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <Link to={mode === 'login' ? '/signup' : '/login'} style={{ color: '#667eea' }}>
            {mode === 'login' ? 'Sign up' : 'Log in'}
          </Link>
        </p>
        {mode === 'login' && (
          <p style={{ marginTop: '8px', fontSize: '14px' }}>
            <Link to="/forgot-password" style={{ color: '#667eea' }}>
              Forgot your password?
            </Link>
          </p>
        )}
      </div>
    </div>
  )
}
