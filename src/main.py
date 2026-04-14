"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import config
from src.models.base import Base
from src.database import db_session
from src.routers import auth, digests


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: create database tables
    async with db_session() as session:
        await session.run_sync(Base.metadata.create_all)
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

    return app


app = create_app()
