# =============================================================================
# Professional Resume Builder — Database Engine & Session Management
# =============================================================================
"""
Async SQLAlchemy database setup.

Provides:
- Async engine creation
- Session factory
- Dependency-injectable session generator
- Database initialization (create tables)
"""

from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def _build_engine_kwargs(url: str) -> dict:
    """
    Build engine kwargs based on database URL.

    SQLite requires special handling for async and in-memory connections.
    """
    kwargs: dict = {
        "echo": settings.debug,
        "future": True,
    }

    if "sqlite" in url:
        # Ensure the data directory exists for file-based SQLite
        if ":memory:" not in url and "mode=memory" not in url:
            db_path = url.split("///")[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        kwargs.update({
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        })

    return kwargs


# --- Async Engine ---
engine = create_async_engine(
    settings.database_url,
    **_build_engine_kwargs(settings.database_url),
)

# --- Session Factory ---
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency-injectable async database session.

    Usage in FastAPI:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            ...

    The session is automatically committed on success and rolled back on error.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize the database by creating all tables.

    Called during application startup. In production, use Alembic migrations
    instead of this function.
    """
    from app.models.base import Base  # noqa: E402 — avoid circular imports
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Gracefully add section_order, hidden_sections, and theme_settings columns if database already exists
        for col in ("section_order", "hidden_sections", "theme_settings"):
            try:
                await conn.execute(text(f"ALTER TABLE resumes ADD COLUMN {col} TEXT"))
            except Exception:
                pass

        try:
            await conn.execute(text("ALTER TABLE projects ADD COLUMN date VARCHAR(100)"))
        except Exception:
            pass


async def close_db() -> None:
    """Dispose of the database engine during shutdown."""
    await engine.dispose()
