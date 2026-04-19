import { test, expect } from '@playwright/test'

/**
 * Full user journey:
 *   signup → AI chat suggests a digest → create it → see it on dashboard
 *
 * The API calls are intercepted so this runs without a live backend.
 * Run the frontend dev server separately before invoking.
 */
test('signup, AI chat, create digest, see it on dashboard', async ({ page }) => {
  const uniqueEmail = `e2e+${Date.now()}@example.com`
  let digestCreated = false

  await page.route('**/api/auth/signup', async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ id: 1, email: uniqueEmail, token: 'token-e2e' }),
    })
  })

  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 1, email: uniqueEmail }),
    })
  })

  await page.route('**/api/digests', async (route, req) => {
    if (req.method() === 'POST') {
      digestCreated = true
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 99,
          name: 'AI News',
          description: null,
          frequency_cron: '0 9 * * 1',
          status: 'active',
          recipient_email: uniqueEmail,
          next_run_at: null,
          last_run_at: null,
          sources: [{ id: 1, source_type: 'rss', url: 'https://example.com/feed.xml', health: 'healthy' }],
          created_at: '2026-01-01T00:00:00',
          updated_at: '2026-01-01T00:00:00',
        }),
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: digestCreated
        ? JSON.stringify([
            {
              id: 99,
              name: 'AI News',
              description: null,
              frequency_cron: '0 9 * * 1',
              status: 'active',
              recipient_email: uniqueEmail,
              next_run_at: null,
              last_run_at: null,
              sources: [{ id: 1, source_type: 'rss', url: 'https://example.com/feed.xml', health: 'healthy' }],
              created_at: '2026-01-01T00:00:00',
              updated_at: '2026-01-01T00:00:00',
            },
          ])
        : '[]',
    })
  })

  await page.route('**/api/ai/chat/stream', async (route) => {
    const body = [
      { type: 'token', content: 'Proposing a feed…' },
      {
        type: 'final',
        reply: 'Proposing a feed…',
        tool_calls: [],
        proposed_digest: {
          name: 'AI News',
          frequency_cron: '0 9 * * 1',
          sources: [{ source_type: 'rss', url: 'https://example.com/feed.xml' }],
        },
      },
    ]
      .map((ev) => `data: ${JSON.stringify(ev)}\n\n`)
      .join('')
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body,
    })
  })

  await page.goto('/signup')
  await page.getByLabel('Email').fill(uniqueEmail)
  await page.getByLabel('Password').fill('pw-12345678')
  await page.getByRole('button', { name: /create account/i }).click()

  await expect(page.getByRole('heading', { name: /your digests/i })).toBeVisible()

  await page.goto('/digests/assistant')
  await page.getByLabel('message').fill('weekly AI news')
  await page.getByRole('button', { name: /send/i }).click()

  await expect(page.getByText(/Proposed digest/i)).toBeVisible()
  await page.getByRole('button', { name: /use this proposal/i }).click()

  await expect(page.getByRole('heading', { name: /create digest/i })).toBeVisible()
  await page.getByLabel('Primary recipient').fill(uniqueEmail)
  await page.getByRole('button', { name: /create digest/i }).click()

  await expect(page.getByText('AI News')).toBeVisible()
})
