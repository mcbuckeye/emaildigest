import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'

export default function VerifyEmail() {
  const [params] = useSearchParams()
  const [state, setState] = useState<'idle' | 'ok' | 'error'>('idle')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      setState('error')
      setMsg('Missing token')
      return
    }
    api.verifyEmail(token)
      .then(() => setState('ok'))
      .catch((err) => {
        setState('error')
        setMsg(err instanceof Error ? err.message : 'Verification failed')
      })
  }, [params])

  return (
    <div className="auth-container">
      <div className="auth-card">
        {state === 'idle' && <p>Verifying…</p>}
        {state === 'ok' && (
          <>
            <h1>Email verified</h1>
            <p>Thanks — your email is confirmed.</p>
            <p><Link to="/">Go to dashboard</Link></p>
          </>
        )}
        {state === 'error' && (
          <>
            <h1>Verification failed</h1>
            <p role="alert" style={{ color: 'red' }}>{msg}</p>
            <p><Link to="/">Back</Link></p>
          </>
        )}
      </div>
    </div>
  )
}
