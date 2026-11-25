from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import PRODUCTION, settings


def normalise_database_url(url: str) -> str:
    """A host's address (`postgres://` or `postgresql://`) in the form this app's driver wants."""
    address = url.strip()
    for plain in ("postgres://", "postgresql://"):
        if address.startswith(plain):
            return "postgresql+psycopg://" + address[len(plain) :]
    return address


def database_url(override: str | None = None) -> str:
    """The database address: an explicit one; in production DATABASE_URL; else the POSTGRES_* parts.

    DATABASE_URL counts only in production, so an old line in a laptop's .env cannot point dev,
    tests or migrations at a real database."""
    if override:
        return override
    if settings.database_url.strip() and settings.app_env.strip().lower() == PRODUCTION:
        return normalise_database_url(settings.database_url)
    return (
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


# A database that does not answer must fail a start or a request in seconds, not hang it.
CONNECT_TIMEOUT_SECONDS = 5


def engine_options(full_url: str) -> dict:
    """The create_engine options for a URL. pool_pre_ping: a connection a hosted database dropped
    while idle is replaced, not failed. SQLite's pool takes no size or timeout settings."""
    if full_url.startswith("sqlite"):
        return {"future": True, "pool_pre_ping": True}
    return {
        "future": True,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 10,
        "connect_args": {"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    }


def make_engine(url: str | None = None):
    full = database_url(url)
    return create_engine(full, **engine_options(full))


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
