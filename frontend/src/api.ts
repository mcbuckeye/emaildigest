export interface User {
  id: number
  email: string
}

export interface Source {
  id?: number
  source_type: 'rss' | 'url'
  url: string
}

export interface Digest {
  id: number
  name: string
  description: string | null
  frequency_cron: string
  status: 'active' | 'paused' | 'inactive'
  recipient_email: string
  next_run_at: string | null
  last_run_at: string | null
  sources: Source[]
  created_at: string
  updated_at: string
}

export interface Delivery {
  id: number
  digest_id: number
  scheduled_at: string
  sent_at: string | null
  status: 'pending' | 'running' | 'sent' | 'failed'
  subject: string | null
  error_message: string | null
  item_count: number
}

export interface ChatResponse {
  reply: string
  tool_calls: Array<{ tool: string; args: unknown; result: unknown }>
  proposed_digest: {
    name: string
    frequency_cron: string
    sources: Source[]
  } | null
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  const h: HeadersInit = { 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers || {}) },
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* non-JSON */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return (await res.json()) as T
  return (await res.text()) as unknown as T
}

export const api = {
  signup: (email: string, password: string) =>
    request<{ id: number; email: string; token: string }>('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>('/api/auth/me'),
  requestPasswordReset: (email: string) =>
    request<{ detail: string }>('/api/auth/password-reset', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  confirmPasswordReset: (token: string, newPassword: string) =>
    request<{ detail: string }>('/api/auth/password-reset/confirm', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
    }),

  listDigests: () => request<Digest[]>('/api/digests'),
  getDigest: (id: number) => request<Digest>(`/api/digests/${id}`),
  createDigest: (body: {
    name: string
    description?: string
    frequency_cron: string
    recipient_email: string
    sources: Source[]
  }) =>
    request<Digest>('/api/digests', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateDigest: (id: number, body: Partial<Omit<Digest, 'id' | 'sources' | 'created_at' | 'updated_at'>>) =>
    request<Digest>(`/api/digests/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  deleteDigest: (id: number) => request<void>(`/api/digests/${id}`, { method: 'DELETE' }),
  pauseDigest: (id: number) =>
    request<{ id: number; status: string }>(`/api/digests/${id}/pause`, { method: 'POST' }),
  resumeDigest: (id: number) =>
    request<{ id: number; status: string }>(`/api/digests/${id}/resume`, { method: 'POST' }),
  resendDigest: (id: number) =>
    request<{ status: string; digest_id: number }>(`/api/digests/${id}/resend`, { method: 'POST' }),

  listDeliveries: (digestId: number) =>
    request<Delivery[]>(`/api/digests/${digestId}/deliveries`),
  previewDelivery: (deliveryId: number) =>
    request<string>(`/api/deliveries/${deliveryId}/preview`),

  chat: (message: string) =>
    request<ChatResponse>('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
}
