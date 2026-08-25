"""SQLite engine factory, dialect-guarded connection hooks, and session management."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.modules.storage.models import Base

__all__ = [
    "Base",
    "create_db_engine",
    "init_db",
    "session_factory_for",
    "session_scope",
]


def _adapt_datetime_to_iso(value: datetime) -> str:
    """SQLite datetime format used by SQLAlchemy's DateTime type (space sep).

    sqlite3's built-in datetime adapter is deprecated as of Python 3.12;
    registering an explicit equivalent keeps bound datetime parameters in the
    same ISO form so lexicographic comparisons against stored strings stay
    consistent and the deprecation warning is silenced.
    """
    return value.isoformat(sep=" ")


sqlite3.register_adapter(datetime, _adapt_datetime_to_iso)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    """Applies SQLite-only performance PRAGMAs on every new connection.

    Dialect-guarded: non-SQLite connections (e.g. PostgreSQL in tests) are
    left untouched. WAL + synchronous=NORMAL trade a little durability for
    much higher read/write throughput; temp_store=MEMORY keeps temp tables
    (used by the grid CTE VALUES population) off disk.
    """
    module_name = getattr(dbapi_connection.__class__, "__module__", "")
    if "sqlite" not in module_name.lower():
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA temp_store=MEMORY;")
    cursor.close()


def create_db_engine(database_url: str = "sqlite:///rae_smart_report.db", **engine_kwargs: object) -> Engine:
    """Creates a SQLite engine with the optimized PRAGMA set applied.

    ``database_url`` defaults to a local ``rae_smart_report.db`` beside the
    process working directory; pass ``sqlite://`` plus ``poolclass=StaticPool``
    for in-memory test databases.
    """
    connect_args_raw = engine_kwargs.pop("connect_args", None)
    connect_args: dict[str, Any] = connect_args_raw if isinstance(connect_args_raw, dict) else {}
    connect_args.setdefault("check_same_thread", False)
    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


def init_db(engine: Engine) -> None:
    """Creates all tables on the given engine."""
    Base.metadata.create_all(engine)


def session_factory_for(engine: Engine) -> sessionmaker[Session]:
    """Builds a configured session factory bound to the engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Context-managed session: commits on success, rolls back on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
