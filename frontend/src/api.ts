export interface User {
  id: number
  email: string
}

export interface Source {
  id?: number
  source_type: 'rss' | 'url'
  url: string
  health?: 'healthy' | 'degraded' | 'broken'
  consecutive_failures?: number
  last_error?: string | null
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

export interface Recipient {
  id: number
  email: string
  unsubscribed_at: string | null
  unsubscribe_token: string
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
  open_count: number
  click_count: number
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

export type StreamEvent =
  | { type: 'token'; content: string }
  | { type: 'tool'; name: string; args: unknown; result: unknown }
  | {
      type: 'final'
      reply: string
      tool_calls: Array<{ tool: string; args: unknown; result: unknown }>
      proposed_digest: ChatResponse['proposed_digest']
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

export async function* chatStream(message: string): AsyncGenerator<StreamEvent> {
  const res = await fetch('/api/ai/chat/stream', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ message }),
  })
  if (!res.ok || !res.body) {
    throw new Error('stream failed')
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) return
    buffer += decoder.decode(value, { stream: true })
    for (;;) {
      const ix = buffer.indexOf('\n\n')
      if (ix === -1) break
      const frame = buffer.slice(0, ix)
      buffer = buffer.slice(ix + 2)
      for (const line of frame.split('\n')) {
        if (!line.startsWith('data:')) continue
        const data = line.slice(5).trim()
        if (!data) continue
        try {
          yield JSON.parse(data) as StreamEvent
        } catch {
          /* skip */
        }
      }
    }
  }
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
  verifyEmail: (token: string) =>
    request<{ detail: string }>('/api/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ token }),
    }),
  resendVerification: () =>
    request<{ detail: string }>('/api/auth/resend-verification', { method: 'POST' }),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ detail: string }>('/api/user/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  changeEmail: (newEmail: string, currentPassword: string) =>
    request<{ detail: string }>('/api/user/change-email', {
      method: 'POST',
      body: JSON.stringify({ new_email: newEmail, current_password: currentPassword }),
    }),
  deleteAccount: () =>
    request<void>('/api/user?confirm=DELETE', { method: 'DELETE' }),

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

  listRecipients: (digestId: number) =>
    request<Recipient[]>(`/api/digests/${digestId}/recipients`),
  addRecipient: (digestId: number, email: string) =>
    request<Recipient>(`/api/digests/${digestId}/recipients`, {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  removeRecipient: (digestId: number, recipientId: number) =>
    request<void>(`/api/digests/${digestId}/recipients/${recipientId}`, { method: 'DELETE' }),
  unsubscribe: (token: string) =>
    request<{ detail: string }>(`/api/unsubscribe/${token}`, { method: 'POST' }),

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
