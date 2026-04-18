"""FastAPI application entry point."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from src.config import INSECURE_DEFAULT_SECRET, config
from src.database import db_session, reset_engine
from src.logging_conf import configure_logging
from src.metrics import REQUESTS, prometheus_output
from src.rate_limit import limiter
from src.routers import ai, auth, digests, tracking, user

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    _init_sentry()
    settings = config()
    if settings.is_production and settings.secret_key == INSECURE_DEFAULT_SECRET:
        raise RuntimeError("SECRET_KEY must be set in production")
    yield
    await reset_engine()


def _init_sentry() -> None:
    settings = config()
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk  # type: ignore

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=settings.sentry_traces_sample_rate,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("sentry init failed: %s", exc)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                for key, value in (
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ):
                    headers.append((key, value))
                if config().is_production:
                    headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestIdMiddleware:
    """Attach a request-id header (generate if missing) and observe latency."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = value.decode()
                break
        if not request_id:
            request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        method = scope.get("method", "GET")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
                status_code = message.get("status", 0)
                REQUESTS.labels(method=method, status=str(status_code)).inc()
            await send(message)

        await self.app(scope, receive, send_wrapper)


def create_app() -> FastAPI:
    settings = config()
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered email newsletter automation platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(digests.router)
    app.include_router(digests.public_router)
    app.include_router(user.router)
    app.include_router(ai.router)
    app.include_router(tracking.router)

    @app.get("/health")
    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "service": "emaildigest-backend"}

    @app.get("/health/ready")
    @app.get("/api/health/ready")
    async def readiness_check():
        try:
            async with db_session() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception as exc:
            return JSONResponse(status_code=503, content={"status": "unready", "error": str(exc)})

    @app.get("/health/db")
    @app.get("/api/health/db")
    async def health_db():
        try:
            async with db_session() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as exc:
            return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(exc)})

    @app.get("/metrics")
    async def metrics():
        return Response(content=prometheus_output(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
