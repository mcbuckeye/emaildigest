# EmailDigest — PRD

## Product Overview

**EmailDigest** is an AI-powered email newsletter automation platform. Users sign up at `emaildigest.machomelab.com`, create periodic research digests using AI assistance, and receive curated content delivered to their inbox on a schedule.

**Core value proposition**: Anyone can create custom email digests from any source with zero manual curation. AI finds, summarizes, and formats content automatically.

---

## User Flows

### Onboarding Flow
1. User lands on `emaildigest.machomelab.com`
2. Creates account with email/password or OAuth (using existing auth system)
3. Landed on welcome dashboard showing "Create your first digest" CTA

### Digest Creation Flow (AI-Assisted)
1. User clicks "Create New Digest"
2. Sees a chat interface: *"What kind of digest would you like to receive?"*
3. User types freely: *"Weekly AI news from techcrunch, arXiv papers about LLMs, and product hunt trends"*
4. AI parses the request and calls tools:
   - **Web search** to discover relevant sources/feeds
   - **Summary AI** to understand what topics/sources fit the description
   - **Email sender** to validate the request makes sense
5. AI returns a structured digest configuration with:
   - Identified RSS feeds or URLs to scrape
   - Suggested keywords/filters
   - Preview of first digest content
6. User confirms/edits, sets delivery frequency (daily/weekly/etc.) and recipient email
7. Digest is saved and will start delivering

### Dashboard Flow
- List all active digests
- Each digest shows: name, frequency, status, last delivery time, next delivery time, subscriber count (if applicable)
- Actions: edit, delete, pause, resend last digest
- Click into digest to see recent deliveries and content previews
- Analytics view: open rates, click rates (MVP: basic counts)

---

## Features

### MVP (Core)

**Authentication**
- Email/password signup and login
- Password reset
- Session management
- Separate subdomain with isolated auth

**Digest Management**
- Create digest via AI chat interface
- Edit existing digest
- Delete digest
- Pause/Resume digest delivery

**AI Configuration Assistant**
- Natural language input for digest description
- Tool-assisted source discovery (web search, summary AI)
- Source validation (test scrape, verify RSS parsing)
- Preview generation

**Delivery Engine**
- Schedule: daily, weekly (specific day), monthly, custom cron
- Email sending via smtp2go
- Content generation: fetch sources → parse/extract → summarize with AI → format as HTML email → send
- Rate limiting and retry logic for failed sends

**Dashboard**
- Digest list with status indicators
- Recent deliveries and preview
- Basic analytics (delivered, failed, next run)

**Sources**
- RSS/Atom feed ingestion (primary)
- Basic web scraping (secondary)
- Source validation and error handling

**Notifications**
- Digest failure emails (to user)
- Digest delivery confirmation (optional, toggleable)

### Out of Scope for MVP

- Multiple recipients per digest (start with single email address)
- User-submitted source lists
- Third-party integrations (Slack, Notion, etc.)
- Template customization
- Advanced analytics
- Paid tiers/subscriptions
- Mobile app

---

## Technical Architecture

### Stack
- **Frontend**: React + TypeScript (your existing UI library or shadcn/ui if starting fresh)
- **Backend**: Python/FastAPI
- **Database**: PostgreSQL (your existing instance or separate schema)
- **Email**: smtp2go (existing account)
- **AI**: Same model stack as main application (assume OpenRouter or similar)
- **Task Queue**: Celery with Redis

### Data Model

**Users**
- `id, email, password_hash, created_at, updated_at`

**Digests**
- `id, owner_id, name, description, frequency_cron, status (active/inactive/paused), recipient_email, created_at, updated_at`

**DigestSources**
- `id, digest_id, source_type (rss/url), url, last_checked_at, last_scraped_at`

**DigestDeliveries**
- `id, digest_id, scheduled_at, sent_at, status (pending/sent/failed), error_message, delivery_count`

**DigestItems**
- `id, delivery_id, source_url, title, summary, url, published_at, created_at`

### API Endpoints

**Auth**
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/password-reset`

**Digests**
- `GET /digests` — list user's digests
- `POST /digests` — create new digest (via AI chat)
- `GET /digests/:id` — get digest details
- `PATCH /digests/:id` — update digest
- `DELETE /digests/:id` — delete digest
- `POST /digests/:id/resend` — resend last delivery

**AI**
- `POST /ai/chat` — main AI interface for digest creation

**Deliveries**
- `GET /digests/:id/deliveries` — list deliveries for a digest
- `GET /deliveries/:id/preview` — get HTML preview of delivery

### Task Pipeline

```
Cron Scheduler (every minute)
  └─> Check for digests due
       └─> Celery task: generate_digest(digest_id)
            ├─> Fetch all sources (RSS/URLs)
            ├─> Parse and extract content
            ├─> AI summary generation for each item
            ├─> Combine into email body
            ├─> Send via smtp2go
            └─> Update delivery record
```

### Deployment Pipeline

```
1. Push to GitHub → emaildigest-machomelab repo
2. GitHub Actions (or Dokploy auto-deploy):
   - Run tests
   - Build Docker image
   - Push to registry
3. Dokploy pulls latest image
4. Dokploy redeploys with zero-downtime
5. Database migrations run automatically (if needed)
```

---

## Implementation Notes

**AI Prompt Design**
The AI assistant needs careful prompt engineering to reliably:
1. Understand vague user requests like "I want a weekly digest about cool tech stuff"
2. Identify actionable sources (RSS feeds, pub sites, newsletters)
3. Validate that discovered sources actually exist and are valid
4. Generate digest content that matches user expectations

**Email Content**
- HTML template with header, body (digest items), footer
- Each item: title, summary, source link, publish date
- Preserve original links and formatting
- Include digest title, description, and next delivery time

**Error Handling**
- Failed source scraping → log, retry next run
- Failed email delivery → retry 3x, then mark as failed and notify user
- Invalid cron expressions → graceful error, fall back to default

**Security**
- Rate limit the AI chat endpoint (prevent abuse)
- Validate all URLs before scraping
- Sanitize HTML content from scraped sources
- API keys for AI tools stored in environment variables

---

## Next Steps

Before I start building:
1. Confirm this PRD matches your vision
2. Should I create the GitHub repo `emaildigest-machomelab`?
3. Do you want me to start with backend API first or frontend?
4. Any specific preferences on task queue (Celery vs Huey)?
5. Should we integrate with your existing Dokploy setup, or create a new app?
