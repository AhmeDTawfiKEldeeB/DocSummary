from collections.abc import AsyncGenerator
from typing import Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase

try:
    from src.config.settings import settings
except ModuleNotFoundError:
    from config.settings import settings


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy ORM models."""
    pass


_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None

_worker_engine: Optional[AsyncEngine] = None
_worker_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine(database_url: Optional[str] = None, echo: Optional[bool] = None) -> AsyncEngine:
    """Returns or creates the singleton AsyncEngine instance."""
    global _engine
    if _engine is None:
        url = database_url or settings.database_url
        is_echo = echo if echo is not None else settings.database_echo

        engine_kwargs = {
            "echo": is_echo,
            "future": True,
        }
        # SQLite doesn't use pool_pre_ping
        if "sqlite" not in url:
            engine_kwargs["pool_pre_ping"] = True

        _engine = create_async_engine(url, **engine_kwargs)
    return _engine


def get_sessionmaker(
    engine: Optional[AsyncEngine] = None,
    use_null_pool: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """Returns or creates the sessionmaker factory for AsyncSession."""
    global _sessionmaker, _worker_sessionmaker
    if engine is not None:
        return async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    if use_null_pool:
        if _worker_sessionmaker is None:
            url = settings.database_url
            is_echo = settings.database_echo
            engine_kwargs = {
                "echo": is_echo,
                "future": True,
            }
            if "sqlite" not in url:
                engine_kwargs["poolclass"] = NullPool

            _worker_engine = create_async_engine(url, **engine_kwargs)
            _worker_sessionmaker = async_sessionmaker(
                bind=_worker_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
        return _worker_sessionmaker

    if _sessionmaker is None:
        eng = get_engine()
        _sessionmaker = async_sessionmaker(
            bind=eng,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession.
    Ensures safe rollback on unhandled exceptions and cleans up the session.
    Transaction commits should be explicitly managed at the service or transaction boundary.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_engine() -> None:
    """Disposes of the database engine (useful for shutdown hooks and test cleanup)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
