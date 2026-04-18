import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type ChatResponse } from '../api'

interface ChatLine {
  role: 'user' | 'assistant'
  content: string
}

export default function AiAssistant() {
  const [lines, setLines] = useState<ChatLine[]>([
    {
      role: 'assistant',
      content:
        "Hi! Tell me what kind of digest you'd like. For example: \"weekly AI news from TechCrunch plus new arXiv papers on LLMs.\"",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [proposal, setProposal] = useState<ChatResponse['proposed_digest']>(null)
  const navigate = useNavigate()

  const send = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    const message = input
    setLines((ls) => [...ls, { role: 'user', content: message }])
    setInput('')
    setLoading(true)
    try {
      const res = await api.chat(message)
      setLines((ls) => [...ls, { role: 'assistant', content: res.reply }])
      if (res.proposed_digest) setProposal(res.proposed_digest)
    } catch (err) {
      setLines((ls) => [...ls, { role: 'assistant', content: (err as Error).message }])
    } finally {
      setLoading(false)
    }
  }

  const confirmProposal = () => {
    if (!proposal) return
    navigate('/digests/new', {
      state: {
        proposal: {
          name: proposal.name,
          description: '',
          frequency_cron: proposal.frequency_cron,
          recipient_email: '',
          sources: proposal.sources,
        },
      },
    })
  }

  return (
    <div className="card" style={{ maxWidth: 720 }}>
      <h1 className="heading-2">AI Digest Assistant</h1>
      <div
        aria-label="conversation"
        style={{
          background: '#f8f9fa',
          padding: 16,
          borderRadius: 8,
          minHeight: 200,
          marginBottom: 12,
        }}
      >
        {lines.map((l, i) => (
          <div key={i} style={{ marginBottom: 8, textAlign: l.role === 'user' ? 'right' : 'left' }}>
            <span
              style={{
                display: 'inline-block',
                background: l.role === 'user' ? '#667eea' : 'white',
                color: l.role === 'user' ? 'white' : '#222',
                padding: '8px 12px',
                borderRadius: 12,
                maxWidth: '80%',
              }}
            >
              {l.content}
            </span>
          </div>
        ))}
      </div>

      <form onSubmit={send} style={{ display: 'flex', gap: 8 }}>
        <input
          aria-label="message"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe the digest..."
          style={{ flex: 1 }}
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Thinking...' : 'Send'}
        </button>
      </form>

      {proposal && (
        <div className="card" style={{ marginTop: 16, background: '#eef' }}>
          <h3 className="heading-3">Proposed digest</h3>
          <p><strong>Name:</strong> {proposal.name}</p>
          <p><strong>Schedule:</strong> {proposal.frequency_cron}</p>
          <p><strong>Sources:</strong></p>
          <ul>
            {proposal.sources.map((s, i) => <li key={i}>{s.source_type}: {s.url}</li>)}
          </ul>
          <button className="btn btn-primary" onClick={confirmProposal}>Use this proposal</button>
        </div>
      )}
    </div>
  )
}
