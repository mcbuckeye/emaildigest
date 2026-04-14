"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from src.database import db_session
from src.models.base import Base
from src.models.user import User
from src.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory SQLite engine for testing."""
    return create_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True,
    )


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create database tables and yield session."""
    Base.metadata.create_all(bind=test_engine)
    SessionLocal = sessionmaker(bind=test_engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="function")
def test_user(test_db):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.GEjCYKyLwvX4AC",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application instance."""
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
