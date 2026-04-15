"""Database connection and sessions."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.config import config


# Create one shared async engine and session factory
engine: AsyncEngine = create_async_engine(
    config().database_url,
    echo=config().app_debug,
    future=True,
)

db_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def create_db_engine() -> AsyncEngine:
    """Return the shared async engine."""
    return engine


async def get_db() -> AsyncSession:
    """Dependency for FastAPI to get database session."""
    async with db_session() as session:
        yield session
        await session.close()
