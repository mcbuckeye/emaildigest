"""Shared test fixtures."""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from alembic.config import Config as AlembicConfig
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command

TEST_DB_ADMIN_URL = os.environ.get(
    "TEST_DB_ADMIN_URL",
    "postgresql+asyncpg://emaildigest:emaildigest@localhost:5432/postgres",
)
TEST_DB_PREFIX = "emaildigest_test_"


def _sync_url(asyncpg_url: str) -> str:
    return asyncpg_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@pytest_asyncio.fixture(scope="session")
async def _test_database_url() -> AsyncIterator[str]:
    """Create a fresh database for the test session and drop it afterwards."""
    db_name = f"{TEST_DB_PREFIX}{uuid.uuid4().hex[:10]}"
    admin_engine = create_async_engine(TEST_DB_ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{db_name}" OWNER emaildigest'))
    await admin_engine.dispose()

    url = TEST_DB_ADMIN_URL.replace("/postgres", f"/{db_name}")

    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", _sync_url(url))
    # Alembic runs synchronously; run in a thread to avoid blocking the loop
    await asyncio.get_event_loop().run_in_executor(None, command.upgrade, alembic_cfg, "head")

    yield url

    admin_engine = create_async_engine(TEST_DB_ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def _configured_env(_test_database_url: str) -> AsyncIterator[str]:
    os.environ["DATABASE_URL"] = _test_database_url
    os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
    os.environ["APP_ENV"] = "test"
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["SMTP2GO_API_KEY"] = ""
    os.environ["REDIS_URL"] = "redis://localhost:6379/15"
    os.environ["RATE_LIMIT_SIGNUP"] = "1000/minute"
    os.environ["RATE_LIMIT_LOGIN"] = "1000/minute"
    os.environ["RATE_LIMIT_AI_CHAT"] = "1000/minute"
    os.environ["RATE_LIMIT_PASSWORD_RESET"] = "1000/minute"

    from src.config import reset_settings_cache
    from src.database import reset_engine

    reset_settings_cache()
    await reset_engine()
    yield _test_database_url
    await reset_engine()


@pytest_asyncio.fixture
async def db_engine(_configured_env: str):
    from src.database import get_engine

    engine = get_engine()
    yield engine
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE "
                "digest_items, digest_deliveries, digest_sources, "
                "password_reset_tokens, digests, users RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def db(db_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def app(db_engine) -> AsyncIterator[FastAPI]:
    from src.main import create_app

    application = create_app()
    async with LifespanManager(application):
        yield application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def user(db: AsyncSession):
    from src.models import User

    u = User(email=f"user-{uuid.uuid4().hex[:6]}@example.com")
    u.set_password("password123")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def other_user(db: AsyncSession):
    from src.models import User

    u = User(email=f"other-{uuid.uuid4().hex[:6]}@example.com")
    u.set_password("password123")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
def auth_headers(user):
    from datetime import timedelta

    from src.auth import create_access_token

    token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    from datetime import timedelta

    from src.auth import create_access_token

    token = create_access_token({"sub": str(other_user.id)}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def digest_with_source(db, user):
    from src.models import Digest, DigestSource, DigestStatus, SourceType

    digest = Digest(
        owner_id=user.id,
        name="Test Digest",
        description="A test digest",
        frequency_cron="0 9 * * *",
        status=DigestStatus.ACTIVE.value,
        recipient_email=user.email,
    )
    db.add(digest)
    await db.commit()
    await db.refresh(digest)

    source = DigestSource(
        digest_id=digest.id,
        source_type=SourceType.RSS.value,
        url="https://example.com/feed.xml",
    )
    db.add(source)
    await db.commit()
    await db.refresh(digest, attribute_names=["sources"])
    return digest
