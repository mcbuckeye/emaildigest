import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Digest } from '../api'

export default function Dashboard() {
  const [digests, setDigests] = useState<Digest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      setDigests(await api.listDigests())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const onDelete = async (id: number) => {
    if (!confirm('Delete this digest?')) return
    await api.deleteDigest(id)
    setDigests((ds) => ds.filter((d) => d.id !== id))
  }

  const onPause = async (d: Digest) => {
    const fn = d.status === 'paused' ? api.resumeDigest : api.pauseDigest
    const res = await fn(d.id)
    setDigests((ds) => ds.map((x) => (x.id === d.id ? { ...x, status: res.status as Digest['status'] } : x)))
  }

  const onResend = async (id: number) => {
    await api.resendDigest(id)
    alert('Delivery queued')
  }

  if (loading) {
    return <div className="loader" aria-label="loading" />
  }

  return (
    <>
      <div className="dashboard-header">
        <h1 className="heading-2">Your Digests</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to="/digests/new" className="btn btn-secondary">+ Manual</Link>
          <Link to="/digests/assistant" className="btn btn-primary">+ AI Assistant</Link>
        </div>
      </div>

      {error && <div role="alert" style={{ color: 'red' }}>{error}</div>}

      {digests.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No digests yet</h3>
            <p>Create your first digest with the AI assistant.</p>
          </div>
        </div>
      ) : (
        <div className="dashboard-grid">
          {digests.map((d) => (
            <div key={d.id} className="card" data-testid={`digest-${d.id}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3 className="heading-3">{d.name}</h3>
                <span className={`status-badge status-${d.status}`}>{d.status}</span>
              </div>
              {d.description && <p className="text-muted">{d.description}</p>}
              {d.sources.some((s) => s.health === 'broken' || s.health === 'degraded') && (
                <p style={{ fontSize: 12, color: '#b45309', margin: '4px 0' }}>
                  ⚠ One or more sources are unhealthy — check the editor.
                </p>
              )}
              <p style={{ fontSize: 13, color: '#666' }}>
                <strong>Schedule:</strong> {d.frequency_cron} <br />
                <strong>To:</strong> {d.recipient_email}
                {d.next_run_at && <> <br /><strong>Next run:</strong> {new Date(d.next_run_at).toLocaleString()}</>}
              </p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                <Link to={`/digests/${d.id}/deliveries`} className="btn btn-secondary btn-sm">Deliveries</Link>
                <Link to={`/digests/edit/${d.id}`} className="btn btn-secondary btn-sm">Edit</Link>
                <button className="btn btn-secondary btn-sm" onClick={() => onPause(d)}>
                  {d.status === 'paused' ? 'Resume' : 'Pause'}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => onResend(d.id)}>Resend</button>
                <button className="btn btn-secondary btn-sm" onClick={() => onDelete(d.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
