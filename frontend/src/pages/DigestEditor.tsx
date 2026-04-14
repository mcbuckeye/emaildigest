import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
// keep declared imports used to satisfy TypeScript linting even if not referenced directly
void useNavigate

interface DigestFormData {
  name: string
  description: string
  frequency_cron: string
  recipient_email: string
  source_type: 'rss' | 'url'
  source_url: string
}

const defaultForm: DigestFormData = {
  name: '',
  description: '',
  frequency_cron: '0 9 * * *',
  recipient_email: '',
  source_type: 'rss',
  source_url: '',
}

export default function DigestEditor() {
  const { id } = useParams<{ id: string }>()
  const isEdit = !!id
  const [formData, setFormData] = useState<DigestFormData>(defaultForm)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEdit) {
      fetchDigest()
    }
  }, [isEdit])

  const fetchDigest = async () => {
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`http://localhost:8000/api/digests/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (res.ok) {
        const data = await res.json()
        setFormData({
          name: data.name,
          description: data.description || '',
          frequency_cron: data.frequency_cron,
          recipient_email: data.recipient_email,
          source_type: 'rss',
          source_url: '',
        })
      }
    } catch (err) {
      console.error('Failed to fetch digest:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)

    const token = localStorage.getItem('token')
    const url = isEdit 
      ? `http://localhost:8000/api/digests/${id}`
      : 'http://localhost:8000/api/digests/'
    
    const method = isEdit ? 'PATCH' : 'POST'

    try {
      const res = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      if (res.ok) {
        window.location.href = '/'
      } else {
        const err = await res.json()
        alert(err.detail || 'Failed to save digest')
      }
    } catch (err) {
      console.error('Failed to save digest:', err)
      alert('An error occurred while saving')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card">
      <h1 className="heading-2">
        {isEdit ? 'Edit Digest' : 'Create New Digest'}
      </h1>

      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label>Digest Name *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., Weekly AI News"
            required
          />
        </div>

        <div className="input-group">
          <label>Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Brief description of what this digest is about"
          />
        </div>

        <div className="input-group">
          <label>Recipient Email *</label>
          <input
            type="email"
            value={formData.recipient_email}
            onChange={(e) => setFormData({ ...formData, recipient_email: e.target.value })}
            placeholder="where should the digest be sent?"
            required
          />
        </div>

        <div className="input-group">
          <label>Frequency</label>
          <select
            value={formData.frequency_cron}
            onChange={(e) => setFormData({ ...formData, frequency_cron: e.target.value })}
          >
            <option value="0 9 * * *">Daily at 9:00 AM</option>
            <option value="0 9 * * 1">Weekly on Mondays at 9:00 AM</option>
            <option value="0 9 * * 7">Weekly on Sundays at 9:00 AM</option>
            <option value="0 9 1 * *">Monthly on the 1st at 9:00 AM</option>
            <option value="0 9 * * *">Custom (Cron expression)</option>
          </select>
          <p className="text-muted" style={{ fontSize: '12px', marginTop: '4px' }}>
            Or enter a custom cron expression
          </p>
        </div>

        <div className="input-group">
          <label>Source Type</label>
          <select
            value={formData.source_type}
            onChange={(e) => setFormData({ ...formData, source_type: e.target.value as 'rss' | 'url' })}
          >
            <option value="rss">RSS Feed</option>
            <option value="url">Website URL</option>
          </select>
        </div>

        <div className="input-group">
          <label>Source URL *</label>
          <input
            type="url"
            value={formData.source_url}
            onChange={(e) => setFormData({ ...formData, source_url: e.target.value })}
            placeholder="https://example.com/feed.xml"
            required
          />
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Digest'}
          </button>
          <button 
            type="button" 
            className="btn btn-secondary" 
            onClick={() => window.history.back()}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
