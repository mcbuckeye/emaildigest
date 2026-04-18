import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Delivery } from '../api'

export default function Deliveries() {
  const { id } = useParams<{ id: string }>()
  const digestId = Number(id)
  const [deliveries, setDeliveries] = useState<Delivery[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listDeliveries(digestId)
      .then(setDeliveries)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [digestId])

  if (loading) return <div className="loader" aria-label="loading" />
  if (error) return <div role="alert" style={{ color: 'red' }}>{error}</div>

  return (
    <>
      <div className="dashboard-header">
        <h1 className="heading-2">Deliveries</h1>
        <Link to="/" className="btn btn-secondary">Back</Link>
      </div>
      {deliveries.length === 0 ? (
        <div className="card"><p>No deliveries yet.</p></div>
      ) : (
        <div className="card">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>When</th>
                <th style={{ textAlign: 'left' }}>Status</th>
                <th style={{ textAlign: 'left' }}>Items</th>
                <th style={{ textAlign: 'left' }}>Opens</th>
                <th style={{ textAlign: 'left' }}>Clicks</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {deliveries.map((d) => (
                <tr key={d.id} data-testid={`delivery-${d.id}`}>
                  <td>{new Date(d.sent_at || d.scheduled_at).toLocaleString()}</td>
                  <td><span className={`status-badge status-${d.status}`}>{d.status}</span></td>
                  <td>{d.item_count}</td>
                  <td>{d.open_count}</td>
                  <td>{d.click_count}</td>
                  <td>
                    <Link to={`/deliveries/${d.id}/preview`} className="btn btn-secondary btn-sm">Preview</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

export function DeliveryPreview() {
  const { id } = useParams<{ id: string }>()
  const [html, setHtml] = useState<string>('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.previewDelivery(Number(id))
      .then(setHtml)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'))
  }, [id])

  if (error) return <div role="alert" style={{ color: 'red' }}>{error}</div>
  return (
    <iframe
      title="delivery-preview"
      srcDoc={html}
      style={{ width: '100%', height: 'calc(100vh - 100px)', border: '1px solid #e0e0e0', borderRadius: 8 }}
    />
  )
}
