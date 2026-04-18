# EmailDigest

AI-powered email newsletter automation. Users sign up, describe what they want in plain English,
and receive curated email digests on a schedule.

## Stack

- **Backend:** FastAPI (async), SQLAlchemy 2.0 + Alembic, Celery + Celery Beat, Redis
- **Database:** PostgreSQL 16
- **AI:** OpenAI (`gpt-4o-mini` by default) with function calling for `validate_rss` + `propose_digest`
- **Email:** smtp2go via `aiosmtplib`, MIME built with stdlib `EmailMessage`
- **Frontend:** React 18 + TypeScript (Vite), Vitest + Testing Library
- **Deploy:** Docker Compose / Dokploy; Cloudflare for DNS/SSL

## Quick start (local)

```bash
# Backend
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env  # edit SECRET_KEY, OPENAI_API_KEY, SMTP2GO_API_KEY
.venv/bin/alembic upgrade head
.venv/bin/uvicorn src.main:app --reload

# Worker + scheduler (new shells)
.venv/bin/celery -A celery_worker worker --loglevel=info
.venv/bin/celery -A celery_worker beat --loglevel=info

# Frontend
cd frontend && npm install && npm run dev
```

## Docker

```bash
docker-compose up --build -d
```

Runs Postgres, Redis, migrations, backend, worker, Celery Beat, and frontend.

## Running tests

Backend (needs a running Postgres; the test suite creates a throwaway DB per session):

```bash
TEST_DB_ADMIN_URL=postgresql+asyncpg://emaildigest:emaildigest@localhost:5432/postgres \
  .venv/bin/pytest --cov=src
```

Frontend:

```bash
cd frontend && npm test && npm run typecheck && npm run build
```

End-to-end (Playwright):

```bash
cd e2e && npm install
npx playwright install chromium
npm --prefix ../frontend run dev &    # or point E2E_BASE_URL at any running frontend
npm test
```

## API

Auth
- `POST /api/auth/signup` — register
- `POST /api/auth/login` — JSON or OAuth2 form body
- `GET /api/auth/me` — current user
- `POST /api/auth/password-reset` — request reset link
- `POST /api/auth/password-reset/confirm` — consume token + new password

Digests
- `GET /api/digests` — list
- `POST /api/digests` — create (accepts `sources: [{source_type, url}]`)
- `GET /api/digests/{id}` — read
- `PATCH /api/digests/{id}` — update
- `DELETE /api/digests/{id}`
- `POST /api/digests/{id}/pause` / `resume` / `resend`
- `GET /api/digests/{id}/deliveries` — delivery history
- `GET /api/deliveries/{id}/preview` — rendered HTML email

AI
- `POST /api/ai/chat` — conversational digest builder with `web_search`, `validate_rss`, `propose_digest` tools
- `POST /api/ai/chat/stream` — Server-Sent Events; streams tokens + tool calls + final proposal

User settings
- `POST /api/user/change-password`
- `POST /api/user/change-email` (triggers re-verification)
- `DELETE /api/user?confirm=DELETE`
- `POST /api/auth/verify-email` / `POST /api/auth/resend-verification`

Recipients & unsubscribe
- `GET/POST /api/digests/{id}/recipients`, `DELETE /api/digests/{id}/recipients/{rec_id}`
- `POST /api/unsubscribe/{token}` (public)

Tracking
- `GET /api/track/open/{token}.gif` — open pixel (1x1 gif)
- `GET /api/track/click/{token}/{item_id}` — click redirect

Observability
- `GET /metrics` — Prometheus plaintext counters
- Set `SENTRY_DSN` to enable exception reporting

Health
- `GET /health` — liveness
- `GET /health/ready` — readiness (DB reachable)

## Environment

See `.env.example`. Required in production:
- `SECRET_KEY` (JWT signing; app refuses to start with the default in `APP_ENV=production`)
- `OPENAI_API_KEY`
- `SMTP2GO_API_KEY`
- `DATABASE_URL`, `REDIS_URL`
- `CORS_ORIGINS` (comma-separated)
- `APP_BASE_URL` (used in reset-password links)

## Architecture

```
React SPA
   │
   ▼
FastAPI  ──►  PostgreSQL
   │
   ├─► Redis (Celery broker + result backend)
   │       │
   │       ├─► Celery Worker  (digest generation)
   │       └─► Celery Beat    (scan_due_digests every minute)
   │
   └─► OpenAI (chat + summarization)
```

## Security notes

- Rate limits on signup, login, password-reset, and AI chat (configurable via env).
- SSRF protection in source fetchers (blocks private/link-local/loopback IPs).
- HTML sanitization via `bleach` before embedding in emails.
- CORS origins locked to `CORS_ORIGINS` (no `*` in production).
- `strict-transport-security`, `x-content-type-options`, `x-frame-options`, `referrer-policy` headers.

## License

MIT
