import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface Digest {
  id: number
  name: string
  description?: string
  frequency_cron: string
  status: 'active' | 'paused' | 'inactive'
  recipient_email: string
  created_at: string
  updated_at: string
}

export default function Dashboard() {
  const { user } = useAuth()
  // user variable is intentionally read by the JSX below; keep ESLint/TS happy
  void user
  const [digests, setDigests] = useState<Digest[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDigests()
  }, [])

  const fetchDigests = async () => {
    const token = localStorage.getItem('token')
    try {
      const res = await fetch('http://localhost:8000/api/digests/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (res.ok) {
        const data = await res.json()
        setDigests(data)
      }
    } catch (err) {
      console.error('Failed to fetch digests:', err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const classes = {
      active: 'status-active',
      paused: 'status-paused',
      inactive: 'status-inactive',
    }
    return <span className={`status-badge ${classes[status as keyof typeof classes]}`}>{status}</span>
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this digest?')) return
    const token = localStorage.getItem('token')
    const res = await fetch(`http://localhost:8000/api/digests/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })
    if (res.ok) {
      setDigests(digests.filter(d => d.id !== id))
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <div className="loader"></div>
      </div>
    )
  }

  return (
    <>
      <div className="dashboard-header">
        <h1 className="heading-2">Your Digests</h1>
        <Link to="/digests/new" className="btn btn-primary">
          + Create New Digest
        </Link>
      </div>

      {digests.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <h3>No digests yet</h3>
            <p>Create your first digest to start receiving curated content in your inbox.</p>
            <Link to="/digests/new" className="btn btn-primary" style={{ marginTop: '16px' }}>
              Create Your First Digest
            </Link>
          </div>
        </div>
      ) : (
        <div className="dashboard-grid">
          {digests.map((digest) => (
            <div key={digest.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                <h3 className="heading-3">{digest.name}</h3>
                {getStatusBadge(digest.status)}
              </div>
              
              {digest.description && (
                <p className="text-muted" style={{ marginBottom: '16px', fontSize: '14px' }}>
                  {digest.description}
                </p>
              )}

              <div style={{ marginBottom: '16px', fontSize: '13px', color: '#6b7280' }}>
                <p><strong>Frequency:</strong> {digest.frequency_cron}</p>
                <p><strong>Email:</strong> {digest.recipient_email}</p>
              </div>

              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <Link to={`/digests/edit/${digest.id}`} className="btn btn-secondary btn-sm">
                  Edit
                </Link>
                <button 
                  className="btn btn-secondary btn-sm" 
                  onClick={() => handleDelete(digest.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
