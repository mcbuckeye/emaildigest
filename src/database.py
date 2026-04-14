"""Database connection and sessions."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import config


def create_db_engine() -> async_sessionmaker[AsyncSession]:
    """Create async database engine and session factory."""
    engine = create_async_engine(
        config().database_url,
        echo=config().app_debug,
        future=True,
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def get_db_session() -> async_sessionmaker[AsyncSession]:
    """Get the session factory."""
    return create_db_engine()


db_session = get_db_session()


async def get_db() -> AsyncSession:
    """Dependency for FastAPI to get database session."""
    async with db_session() as session:
        yield session
        await session.close()
