from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
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
    return create_engine(database_url(url), future=True)


def session_factory(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=make_engine(url), autoflush=False, autocommit=False, future=True)


def get_session(url: str | None = None) -> Generator[Session, None, None]:
    factory = session_factory(url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
