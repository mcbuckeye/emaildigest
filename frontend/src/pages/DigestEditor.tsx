import { useEffect, useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { api, type Recipient, type Source } from '../api'
import CronBuilder from '../components/CronBuilder'

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

const HEALTH_COLOR: Record<NonNullable<Source['health']>, string> = {
  healthy: '#22c55e',
  degraded: '#f59e0b',
  broken: '#dc2626',
}

export default function DigestEditor() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const isEdit = !!id
  const [form, setForm] = useState<FormState>(defaultState)
  const [sources, setSources] = useState<Source[]>([])
  const [recipients, setRecipients] = useState<Recipient[]>([])
  const [newRecipient, setNewRecipient] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isEdit && id) {
      api.getDigest(Number(id))
        .then((d) => {
          setForm({
            name: d.name,
            description: d.description ?? '',
            frequency_cron: d.frequency_cron,
            recipient_email: d.recipient_email,
            sources: d.sources.length ? d.sources : [{ source_type: 'rss', url: '' }],
          })
          setSources(d.sources)
        })
        .catch(() => setError('Could not load digest'))
      api.listRecipients(Number(id)).then(setRecipients).catch(() => {})
    }
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

  const addRecipient = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !newRecipient.trim()) return
    try {
      const rec = await api.addRecipient(Number(id), newRecipient.trim())
      setRecipients((rs) => [...rs, rec])
      setNewRecipient('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  const removeRecipient = async (recId: number) => {
    if (!id) return
    await api.removeRecipient(Number(id), recId)
    setRecipients((rs) => rs.filter((r) => r.id !== recId))
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
          <label htmlFor="email">Primary recipient</label>
          <input
            id="email"
            type="email"
            required
            value={form.recipient_email}
            onChange={(e) => setForm({ ...form, recipient_email: e.target.value })}
          />
        </div>
        <CronBuilder
          value={form.frequency_cron}
          onChange={(cron) => setForm({ ...form, frequency_cron: cron })}
        />

        {!isEdit ? (
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
        ) : (
          <>
            <h3 className="heading-3" style={{ marginTop: 16 }}>Sources</h3>
            <ul>
              {sources.map((s) => (
                <li key={s.id}>
                  <span
                    title={s.last_error || ''}
                    style={{
                      display: 'inline-block',
                      width: 8,
                      height: 8,
                      borderRadius: 4,
                      background: HEALTH_COLOR[s.health ?? 'healthy'],
                      marginRight: 6,
                    }}
                  />
                  <code>{s.url}</code>
                  {s.health !== 'healthy' && (
                    <span style={{ color: HEALTH_COLOR[s.health ?? 'healthy'], fontSize: 12, marginLeft: 8 }}>
                      ({s.health}: {s.consecutive_failures} failures)
                    </span>
                  )}
                </li>
              ))}
            </ul>
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

      {isEdit && (
        <div style={{ marginTop: 24 }}>
          <h3 className="heading-3">Extra recipients</h3>
          <ul>
            {recipients.map((r) => (
              <li key={r.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span>{r.email}</span>
                {r.unsubscribed_at && <em style={{ color: '#dc2626' }}>unsubscribed</em>}
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => removeRecipient(r.id)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={addRecipient} style={{ display: 'flex', gap: 8 }}>
            <input
              aria-label="new recipient"
              type="email"
              placeholder="another@example.com"
              value={newRecipient}
              onChange={(e) => setNewRecipient(e.target.value)}
              style={{ flex: 1 }}
            />
            <button type="submit" className="btn btn-secondary btn-sm">Add</button>
          </form>
        </div>
      )}
    </div>
  )
}
