import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../contexts/AuthContext'

export default function Settings() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [pwMsg, setPwMsg] = useState('')
  const [emailMsg, setEmailMsg] = useState('')
  const [resendMsg, setResendMsg] = useState('')
  const [error, setError] = useState('')

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setPwMsg('')
    try {
      await api.changePassword(currentPassword, newPassword)
      setPwMsg('Password updated.')
      setCurrentPassword('')
      setNewPassword('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  const changeEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setEmailMsg('')
    try {
      await api.changeEmail(newEmail, currentPassword)
      setEmailMsg('Email changed; please check your inbox to verify.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  const resend = async () => {
    try {
      await api.resendVerification()
      setResendMsg('Verification email sent.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  const deleteAccount = async () => {
    if (!confirm('Delete your account and all digests? This cannot be undone.')) return
    await api.deleteAccount()
    logout()
    navigate('/signup')
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <h1 className="heading-2">Account settings</h1>
      <p className="text-muted">Signed in as {user?.email}</p>

      <div className="card">
        <h3 className="heading-3">Email verification</h3>
        <button className="btn btn-secondary btn-sm" onClick={resend}>Resend verification email</button>
        {resendMsg && <p role="status">{resendMsg}</p>}
      </div>

      <div className="card">
        <h3 className="heading-3">Change password</h3>
        <form onSubmit={changePassword}>
          <div className="input-group">
            <label htmlFor="cpw">Current password</label>
            <input
              id="cpw"
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div className="input-group">
            <label htmlFor="npw">New password</label>
            <input
              id="npw"
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" type="submit">Update password</button>
          {pwMsg && <p role="status" style={{ color: 'green' }}>{pwMsg}</p>}
        </form>
      </div>

      <div className="card">
        <h3 className="heading-3">Change email</h3>
        <form onSubmit={changeEmail}>
          <div className="input-group">
            <label htmlFor="nem">New email</label>
            <input
              id="nem"
              type="email"
              required
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
            />
          </div>
          <div className="input-group">
            <label htmlFor="cpw2">Current password</label>
            <input
              id="cpw2"
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" type="submit">Change email</button>
          {emailMsg && <p role="status" style={{ color: 'green' }}>{emailMsg}</p>}
        </form>
      </div>

      <div className="card" style={{ borderLeft: '4px solid #dc2626' }}>
        <h3 className="heading-3">Delete account</h3>
        <p className="text-muted">Permanently removes your account, digests, and history.</p>
        <button className="btn btn-secondary" onClick={deleteAccount} style={{ color: '#dc2626' }}>
          Delete account
        </button>
      </div>

      {error && <div role="alert" style={{ color: 'red' }}>{error}</div>}
    </div>
  )
}
