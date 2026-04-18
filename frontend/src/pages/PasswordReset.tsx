import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api'

export function PasswordResetRequest() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.requestPasswordReset(email)
      setSent(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset')
    }
  }

  if (sent) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Check your email</h1>
          <p>If an account exists for {email}, a reset link has been sent.</p>
          <p><Link to="/login">Back to sign in</Link></p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>Reset your password</h1>
        <form onSubmit={submit}>
          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>
          {error && <div role="alert" style={{ color: 'red' }}>{error}</div>}
          <button className="btn btn-primary" style={{ width: '100%' }}>Send reset link</button>
        </form>
        <p style={{ marginTop: '16px' }}><Link to="/login">Back to sign in</Link></p>
      </div>
    </div>
  )
}

export function PasswordResetConfirm() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const token = params.get('token') || ''

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!token) {
      setError('Missing token')
      return
    }
    try {
      await api.confirmPasswordReset(token, password)
      navigate('/login')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset')
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>Set a new password</h1>
        <form onSubmit={submit}>
          <div className="input-group">
            <label htmlFor="pw">New password</label>
            <input
              id="pw"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <div role="alert" style={{ color: 'red' }}>{error}</div>}
          <button className="btn btn-primary" style={{ width: '100%' }}>Update password</button>
        </form>
      </div>
    </div>
  )
}
