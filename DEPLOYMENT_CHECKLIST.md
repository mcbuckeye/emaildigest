# EmailDigest Deployment Checklist

## Pre-Deployment

- [ ] All code committed and CI green
- [ ] `.env.example` reflects the current env shape
- [ ] Alembic migrations present under `alembic/versions/`
- [ ] Dockerfiles and `docker-compose.yml` include: backend, worker, beat, migrate, frontend, db, redis

## Dokploy Deployment

### 1. Create Application

- [ ] Log into Dokploy, "Create Application"
- [ ] Connect to Git: `mcbuckeye/emaildigest`, branch `main`

### 2. Configure Environment

Required:
- [ ] `DATABASE_URL`
- [ ] `REDIS_URL`
- [ ] `SECRET_KEY` (strong random value — app refuses to boot with the default in production)
- [ ] `APP_ENV=production`
- [ ] `APP_BASE_URL=https://emaildigest.machomelab.com`
- [ ] `CORS_ORIGINS=https://emaildigest.machomelab.com`
- [ ] `SMTP2GO_API_KEY`
- [ ] `OPENAI_API_KEY`
- [ ] `SMTP2GO_FROM_EMAIL`, `SMTP2GO_FROM_NAME`

Optional rate limits (override if abuse appears):
- [ ] `RATE_LIMIT_SIGNUP`, `RATE_LIMIT_LOGIN`, `RATE_LIMIT_AI_CHAT`

### 3. Configure Domain

- [ ] Add `emaildigest.machomelab.com`
- [ ] Enable SSL/HTTPS (Cloudflare managed cert recommended)

### 4. Deploy

- [ ] Run migrations (the `migrate` service applies `alembic upgrade head`; must complete before backend)
- [ ] Start `backend`, `worker`, `beat`, `frontend`
- [ ] Check logs for errors
- [ ] `beat` service is required; without it, nothing gets delivered

## Cloudflare Configuration

- [ ] `emaildigest` CNAME → Dokploy host (proxied)
- [ ] (Optional) Workers for reverse proxy

## Verification

### Health Checks

```bash
curl https://emaildigest.machomelab.com/health
curl https://emaildigest.machomelab.com/health/ready
curl https://emaildigest.machomelab.com/health/db
```

### Smoke tests

1. Sign up → /login
2. AI assistant page → ask for "weekly AI news" → confirm proposed digest
3. Dashboard → Pause / Resume / Resend
4. Deliveries page → preview last delivery
5. Log out → Forgot password → reset via emailed link

### Security

- [ ] `SECRET_KEY` rotated from default
- [ ] HTTPS only (HSTS header sent in prod)
- [ ] CORS origins locked to production domain
- [ ] Rate limits sane for your traffic profile

## Observability

- [ ] Backend emits structured JSON logs (`structlog`)
- [ ] Monitor Celery worker + beat uptime
- [ ] (Optional) Connect Sentry by wiring `SENTRY_DSN` into `logging_conf.configure_logging`

## Rollback

1. Re-deploy previous image
2. If migration needed rollback: `alembic downgrade -1` (check destructive-migration safety first)

---

**Deployment Date:** __________
**Deployed By:** __________
**Notes:** __________
