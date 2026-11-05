from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def database_url(override: str | None = None) -> str:
    if override:
        return override
    return (
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def make_engine(url: str | None = None):
    # pool_pre_ping: a connection a hosted database dropped while idle is replaced, not failed.
    full = database_url(url)
    if full.startswith("sqlite"):  # SQLite's pool takes no size settings
        return create_engine(full, future=True, pool_pre_ping=True)
    return create_engine(full, future=True, pool_pre_ping=True, pool_size=10, max_overflow=10)


_shared_engine: Engine | None = None
_shared_factory: sessionmaker[Session] | None = None


def shared_factory() -> sessionmaker[Session]:
    """The one process-wide engine and session factory, built on first use and then reused.

    A new engine per request opened a new connection (and a new pool) every time."""
    global _shared_engine, _shared_factory
    if _shared_factory is None:
        _shared_engine = make_engine()
        _shared_factory = sessionmaker(
            bind=_shared_engine, autoflush=False, autocommit=False, future=True
        )
    return _shared_factory


def session_factory(url: str | None = None) -> sessionmaker[Session]:
    if url is None:
        return shared_factory()
    return sessionmaker(bind=make_engine(url), autoflush=False, autocommit=False, future=True)


def get_session(url: str | None = None) -> Generator[Session, None, None]:
    factory = session_factory(url)
    session = factory()
    try:
        yield session
        session.commit()
    except HTTPException:
        session.commit()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    yield from get_session()
