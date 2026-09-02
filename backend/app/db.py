"""Database access.

Without DATABASE_URL there is no engine and callers fall back to demo data, so a
first launch never fails on a missing database (architecture.md, Runtime modes).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine | None:
    url = get_settings().database_url
    return create_engine(url, pool_pre_ping=True) if url else None


@lru_cache
def get_session_factory() -> sessionmaker[Session] | None:
    engine = get_engine()
    return sessionmaker(engine, expire_on_commit=False) if engine else None


def database_configured() -> bool:
    return get_engine() is not None


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL is not configured; callers must check database_configured() first.")
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
