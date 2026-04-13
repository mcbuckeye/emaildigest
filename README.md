# EmailDigest

AI-powered email newsletter automation platform.

## Quick Start

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis (Celery broker)
- Backend API (FastAPI)
- Frontend (React)
- Worker (Celery tasks)

## Tech Stack

- **Frontend**: React + TypeScript
- **Backend**: Python/FastAPI
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Email**: smtp2go
- **AI**: OpenRouter-compatible API

## Architecture

```
Frontend (React) ←→ Backend (FastAPI) ←→ Celery Workers
                             ↓
                      PostgreSQL + Redis
```

## Development

```bash
# Backend
pip install -r requirements.txt
fastapi dev main.py

# Worker
celery -A celery_app worker --loglevel=info

# Frontend
npm install
npm run dev
```

## Environment Variables

See `.env.example` for required configuration.

## Deployment

Deploy to Dokploy. The app is containerized and ready for production.

## License

MIT
