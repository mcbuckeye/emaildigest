import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'

export default function Unsubscribe() {
  const [params] = useSearchParams()
  const [state, setState] = useState<'idle' | 'ok' | 'error'>('idle')

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      setState('error')
      return
    }
    api.unsubscribe(token)
      .then(() => setState('ok'))
      .catch(() => setState('error'))
  }, [params])

  return (
    <div className="auth-container">
      <div className="auth-card">
        {state === 'idle' && <p>Processing…</p>}
        {state === 'ok' && (
          <>
            <h1>Unsubscribed</h1>
            <p>You won't get further emails for this digest. You can re-subscribe from the dashboard.</p>
            <p><Link to="/">Back</Link></p>
          </>
        )}
        {state === 'error' && (
          <>
            <h1>We couldn't find that subscription</h1>
            <p role="alert">The unsubscribe link may have expired.</p>
          </>
        )}
      </div>
    </div>
  )
}
