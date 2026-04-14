# EmailDigest

AI-powered email newsletter automation platform.

## Quick Start

```bash
# Start all services
docker-compose up -d

# Backend runs on http://localhost:8000
# Frontend runs on http://localhost:3000
```

## What This Does

- Users sign up at `emaildigest.machomelab.com`
- Create digests via AI-assisted interface (describe what you want in plain English)
- Receive curated email digests on their schedule

## Tech Stack

- **Frontend**: React + TypeScript (Vite)
- **Backend**: Python/FastAPI
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Email**: smtp2go

## Development

```bash
# Backend
pip install -r requirements.txt  # Or install from pyproject.toml
uvicorn src.main:app --reload

# Worker
celery -A celery_worker worker --loglevel=info

# Frontend
cd frontend
npm install
npm run dev
```

## Environment Variables

See `.env.example` for required configuration.

## API Endpoints

### Auth
- `POST /api/auth/signup` - Register
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Digests
- `GET /api/digests` - List digests
- `POST /api/digests` - Create digest
- `GET /api/digests/{id}` - Get digest
- `PATCH /api/digests/{id}` - Update digest
- `DELETE /api/digests/{id}` - Delete digest

### Health
- `GET /health` - Basic health check
- `GET /health/db` - Database connectivity check

## Deployment to Dokploy

1. **Push to GitHub** (already done):
   ```bash
   cd emaildigest
   git add -A
   git commit -m "Production-ready deployment"
   git push
   ```

2. **In Dokploy dashboard**:
   - Create new app from GitHub repository: `mcbuckeye/emaildigest`
   - Select branch: `main`
   - Set environment variables:
     - `SECRET_KEY` - JWT secret key
     - `SMTP2GO_API_KEY` - Your smtp2go API key
     - `LLM_API_KEY` - AI model API key (for future features)
   - Deploy

3. **Or use the pre-configured files**:
   - Copy `.dokploy/docker-compose.prod.yml` and `.dokploy/production.env`
   - Adjust paths and credentials as needed
   - Deploy using Dokploy CLI:
     ```bash
     dokploy deploy --file .dokploy/docker-compose.prod.yml
     ```

4. **Custom domain**:
   - Point CNAME `emaildigest.machomelab.com` to your Dokploy instance
   - Configure SSL certificate in Dokploy

## Architecture

```
Frontend (React) ←→ Backend (FastAPI) ←→ Celery Workers
                             ↓
                      PostgreSQL + Redis
```

## License

MIT
