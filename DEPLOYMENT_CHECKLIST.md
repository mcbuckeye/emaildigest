# EmailDigest Deployment Checklist

## Pre-Deployment

- [ ] All code committed to GitHub
- [ ] `.env.example` contains all required variables
- [ ] `pyproject.toml` has all dependencies
- [ ] Dockerfiles are present and correct
- [ ] `docker-compose.yml` is properly configured

## Dokploy Deployment

### 1. Create Application

- [ ] Log into Dokploy dashboard
- [ ] Click "Create Application"
- [ ] Select "Connect to Git"
- [ ] Choose repository: `mcbuckeye/emaildigest`
- [ ] Select branch: `main`

### 2. Configure Environment

- [ ] Set `DATABASE_URL`
- [ ] Set `REDIS_URL`
- [ ] Set `SECRET_KEY` (generate a strong random value)
- [ ] Set `SMTP2GO_API_KEY`
- [ ] Set `LLM_API_KEY`
- [ ] Set `APP_DEBUG=false`
- [ ] Set `APP_HOST=0.0.0.0`
- [ ] Set `APP_PORT=8000`

### 3. Configure Domain

- [ ] Add custom domain: `emaildigest.machomelab.com`
- [ ] Enable SSL/HTTPS
- [ ] Configure SSL provider (Cloudflare managed cert recommended)

### 4. Deploy

- [ ] Click "Deploy"
- [ ] Wait for deployment to complete
- [ ] Check deployment logs for errors

## Cloudflare Configuration

### DNS Setup

- [ ] Log into Cloudflare
- [ ] Navigate to `machomelab.com` DNS settings
- [ ] Create CNAME record:
  - Name: `emaildigest`
  - Target: `<dokploy-deployment-url>`
  - Proxy: Enabled (orange cloud)

### Optional: Workers Setup

- [ ] Create Cloudflare Worker for reverse proxy
- [ ] Bind environment variables
- [ ] Set routing rules

## Verification

### Health Checks

```bash
# Backend API
curl https://emaildigest.machomelab.com/health

# Database connection
curl https://emaildigest.machomelab.com/health/db

# Frontend
curl https://emaildigest.machomelab.com
```

### Functional Tests

1. **Sign up test**
   - [ ] Navigate to `https://emaildigest.machomelab.com/signup`
   - [ ] Create a new account
   - [ ] Verify email received (if SMTP configured)

2. **Login test**
   - [ ] Navigate to `https://emaildigest.machomelab.com/login`
   - [ ] Login with credentials
   - [ ] Verify redirect to dashboard

3. **Create digest test**
   - [ ] Click "Create New Digest"
   - [ ] Fill in digest details
   - [ ] Submit and verify digest created

4. **View digests**
   - [ ] Verify digest appears in dashboard
   - [ ] Test edit/delete functionality

## Post-Deployment

### Monitoring

- [ ] Set up Dokploy monitoring/alerts
- [ ] Configure health check intervals
- [ ] Set up log aggregation (optional)

### Security

- [ ] Change default `SECRET_KEY` to production value
- [ ] Enable HTTPS only
- [ ] Configure CORS properly
- [ ] Set up rate limiting (if needed)

### Documentation

- [ ] Update team documentation
- [ ] Document any custom configurations
- [ ] Create runbook for common issues

## Rollback Plan

If deployment fails:

1. [ ] Revert to previous commit if needed
2. [ ] Check Dokploy rollback options
3. [ ] Review error logs
4. [ ] Contact support if necessary

## Troubleshooting Resources

- Dokploy documentation: https://dokploy.com/docs
- Cloudflare documentation: https://developers.cloudflare.com/
- FastAPI documentation: https://fastapi.tiangolo.com/
- Celery documentation: https://docs.celeryq.dev/

## Emergency Contacts

- Dokploy Support: https://dokploy.com/support
- Cloudflare Support: https://www.cloudflare.com/support/

---

**Deployment Date:** __________  
**Deployed By:** __________  
**Notes:** __________
