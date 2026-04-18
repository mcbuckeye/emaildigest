import { useEffect, useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { api, type Source } from '../api'

interface FormState {
  name: string
  description: string
  frequency_cron: string
  recipient_email: string
  sources: Source[]
}

const defaultState: FormState = {
  name: '',
  description: '',
  frequency_cron: '0 9 * * 1',
  recipient_email: '',
  sources: [{ source_type: 'rss', url: '' }],
}

export default function DigestEditor() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const isEdit = !!id
  const [form, setForm] = useState<FormState>(defaultState)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isEdit && id) {
      api.getDigest(Number(id))
        .then((d) =>
          setForm({
            name: d.name,
            description: d.description ?? '',
            frequency_cron: d.frequency_cron,
            recipient_email: d.recipient_email,
            sources: d.sources.length ? d.sources : [{ source_type: 'rss', url: '' }],
          }),
        )
        .catch(() => setError('Could not load digest'))
    }
    // hydrate from AI proposal if provided via navigation state
    const proposed = (location.state as { proposal?: FormState } | null)?.proposal
    if (proposed && !isEdit) {
      setForm((prev) => ({ ...prev, ...proposed }))
    }
  }, [isEdit, id, location.state])

  const updateSource = (idx: number, patch: Partial<Source>) => {
    setForm((f) => ({
      ...f,
      sources: f.sources.map((s, i) => (i === idx ? { ...s, ...patch } : s)),
    }))
  }

  const addSource = () =>
    setForm((f) => ({ ...f, sources: [...f.sources, { source_type: 'rss', url: '' }] }))

  const removeSource = (idx: number) =>
    setForm((f) => ({ ...f, sources: f.sources.filter((_, i) => i !== idx) }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      if (isEdit && id) {
        await api.updateDigest(Number(id), {
          name: form.name,
          description: form.description || null,
          frequency_cron: form.frequency_cron,
          recipient_email: form.recipient_email,
        })
      } else {
        await api.createDigest({
          name: form.name,
          description: form.description || undefined,
          frequency_cron: form.frequency_cron,
          recipient_email: form.recipient_email,
          sources: form.sources.filter((s) => s.url.trim()),
        })
      }
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card">
      <h1 className="heading-2">{isEdit ? 'Edit Digest' : 'Create Digest'}</h1>

      <form onSubmit={submit}>
        <div className="input-group">
          <label htmlFor="name">Name</label>
          <input id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div className="input-group">
          <label htmlFor="desc">Description</label>
          <textarea
            id="desc"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </div>
        <div className="input-group">
          <label htmlFor="email">Recipient email</label>
          <input
            id="email"
            type="email"
            required
            value={form.recipient_email}
            onChange={(e) => setForm({ ...form, recipient_email: e.target.value })}
          />
        </div>
        <div className="input-group">
          <label htmlFor="cron">Schedule (cron)</label>
          <select
            id="cron"
            value={form.frequency_cron}
            onChange={(e) => setForm({ ...form, frequency_cron: e.target.value })}
          >
            <option value="0 9 * * *">Daily at 9:00</option>
            <option value="0 9 * * 1">Weekly — Monday 9:00</option>
            <option value="0 9 * * 0">Weekly — Sunday 9:00</option>
            <option value="0 9 1 * *">Monthly — 1st 9:00</option>
          </select>
        </div>

        {!isEdit && (
          <>
            <h3 className="heading-3" style={{ marginTop: 16 }}>Sources</h3>
            {form.sources.map((src, idx) => (
              <div key={idx} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <select
                  aria-label={`source type ${idx}`}
                  value={src.source_type}
                  onChange={(e) => updateSource(idx, { source_type: e.target.value as 'rss' | 'url' })}
                >
                  <option value="rss">RSS</option>
                  <option value="url">URL</option>
                </select>
                <input
                  aria-label={`source url ${idx}`}
                  style={{ flex: 1 }}
                  placeholder="https://example.com/feed.xml"
                  value={src.url}
                  onChange={(e) => updateSource(idx, { url: e.target.value })}
                />
                {form.sources.length > 1 && (
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeSource(idx)}>
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button type="button" className="btn btn-secondary btn-sm" onClick={addSource}>+ Add source</button>
          </>
        )}

        {error && <div role="alert" style={{ color: 'red', marginTop: 12 }}>{error}</div>}

        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : isEdit ? 'Save' : 'Create digest'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
