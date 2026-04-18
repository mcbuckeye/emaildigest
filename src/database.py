"""Database connection and sessions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.config import config

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    return create_async_engine(
        config().database_url,
        echo=config().app_debug,
        future=True,
        pool_pre_ping=True,
    )


def get_engine() -> AsyncEngine:
    """Return the shared async engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory bound to the shared engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def db_session() -> AsyncIterator[AsyncSession]:
    """Async context manager yielding a database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session."""
    async with db_session() as session:
        yield session


async def reset_engine() -> None:
    """Dispose of the current engine and clear the cached factory (for tests)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def create_db_engine() -> AsyncEngine:
    """Backwards-compatible alias returning the shared engine."""
    return get_engine()
