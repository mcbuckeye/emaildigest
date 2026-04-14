# Cloudflare Setup for EmailDigest

## Overview

This guide shows how to configure Cloudflare to route traffic from `emaildigest.machomelab.com` to your Dokploy-hosted EmailDigest application.

## Prerequisites

1. Cloudflare account with access to `machomelab.com` DNS
2. Dokploy deployment URL (e.g., `https://dokploy.example.com/emaildigest`)

## Step 1: Configure Cloudflare DNS

1. Log in to Cloudflare Dashboard
2. Navigate to your domain: `machomelab.com`
3. Go to **DNS** → **Records**
4. Add a new CNAME record:

   | Type | Name | Target | Proxy status | TTL |
   |------|------|--------|--------------|-----|
   | CNAME | emaildigest | `<your-dokploy-deployment-url>` | Proxied (orange cloud) | Auto |

**Example** (adjust domain based on your Dokploy setup):
- Type: `CNAME`
- Name: `emaildigest`
- Target: `emaildigest.your-dokploy-domain.com`
- Proxy status: **Proxied**
- TTL: Auto

## Step 2: Configure Cloudflare Workers (Optional)

If you want to use a Cloudflare Worker as a reverse proxy:

1. Go to **Workers & Pages** → **Create Application** → **Workers**
2. Name it: `emaildigest-proxy`
3. Paste the contents of `cloudflare-workers/index.js`
4. Add bindings:
   - **Environment Variable**: `BACKEND_URL`
   - **Value**: `http://your-dokploy-backend-url:8000`
   - **Environment Variable**: `FRONTEND_URL`
   - **Value**: `http://your-dokploy-frontend-url:3000`
5. Deploy the worker
6. Add a route: `emaildigest.machomelab.com/*`
7. Select your worker: `emaildigest-proxy`

## Step 3: Configure SSL/HTTPS

1. Go to **SSL/TLS** in Cloudflare Dashboard
2. Set encryption mode to **Full** or **Full (Strict)**
3. If using **Full (Strict)**, ensure your Dokploy instance has a valid certificate

## Step 4: Configure EmailDigest in Dokploy

In your Dokploy dashboard:

1. Create a new app/project for EmailDigest
2. Connect to GitHub repository: `mcbuckeye/emaildigest`
3. Select branch: `main`
4. Configure environment variables:

   ```
   DATABASE_URL=postgresql+asyncpg://emaildigest:emaildigest@<dokploy-db-host>:5432/emaildigest
   REDIS_URL=redis://<dokploy-redis-host>:6379/0
   SECRET_KEY=<generate-a-strong-random-secret>
   SMTP2GO_API_KEY=<your-smtp2go-api-key>
   LLM_API_KEY=<your-llm-api-key>
   APP_DEBUG=false
   APP_HOST=0.0.0.0
   APP_PORT=8000
   ```

5. Set the custom domain to: `emaildigest.machomelab.com`
6. Deploy the application

## Step 5: Verify Deployment

After deployment, test each endpoint:

```bash
# Check backend health
curl -v https://emaildigest.machomelab.com/health

# Check database connection
curl -v https://emaildigest.machomelab.com/health/db

# Access the frontend
curl -v https://emaildigest.machomelab.com
```

## Troubleshooting

### Issue: CNAME record not resolving
- Check that the proxy status is set to **Proxied** (orange cloud)
- Verify the target URL is correct and accessible
- Wait up to 60 minutes for DNS propagation (usually much faster)

### Issue: SSL certificate errors
- Ensure SSL mode is set to **Full** or **Full (Strict)** in Cloudflare
- If using **Full (Strict)**, your origin server needs a valid certificate
- For development, you can use **Flexible** mode (not recommended for production)

### Issue: 502 Bad Gateway
- Verify that Dokploy services are running
- Check Dokploy logs for any errors
- Ensure the backend is listening on the correct port

### Issue: CORS errors in frontend
- Verify CORS settings in `src/main.py`
- Ensure frontend and backend URLs are correctly configured

## Quick DNS Configuration

If you need to set this up quickly via Cloudflare API:

```bash
# Install wrangler CLI
npm install -g wrangler@latest

# Login to Cloudflare
wrangler login

# Set DNS records (run from emaildigest directory)
wrangler dns records create emaildigest.machomelab.com emaildigest <dokploy-url> proxy
```

## Next Steps

1. ✅ Configure DNS in Cloudflare
2. ✅ Deploy to Dokploy
3. ✅ Test endpoints
4. ✅ Set up SMTP2GO credentials
5. ✅ Create first digest!
