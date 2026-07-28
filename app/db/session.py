"""Engine e sessão do banco."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.config import get_database_url, is_sqlite

engine: Engine
SessionLocal: sessionmaker[Session]


def configure_engine(url: str | None = None) -> Engine:
    """(Re)configura engine/sessão — útil em testes."""
    global engine, SessionLocal

    resolved = url or get_database_url()
    connect_args = {"check_same_thread": False} if is_sqlite(resolved) else {}
    engine = create_engine(resolved, pool_pre_ping=True, connect_args=connect_args)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return engine


configure_engine()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
