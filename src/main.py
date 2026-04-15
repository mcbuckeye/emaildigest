"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import config
from src.models.base import Base
from src.database import db_session, create_db_engine
from src.routers import auth, digests


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: create database tables
    session_factory = create_db_engine()
    async with session_factory.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: close database connections


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=config().app_name,
        description="AI-powered email newsletter automation platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router)
    app.include_router(digests.router)

    # Health check endpoints for Dokploy
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {"status": "healthy", "service": "emaildigest-backend"}

    @app.get("/health/db")
    async def health_check_db():
        """Database connectivity health check."""
        try:
            async with db_session() as session:
                # Simple query to verify DB connection
                async with session.begin():
                    pass
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "database": "error", "error": str(e)}
            )

    return app


app = create_app()
