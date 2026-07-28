"""Configuração de banco (SQLAlchemy)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parent / ".env")

DEFAULT_DATABASE_URL = f"sqlite:///{_ROOT / 'laje_signature.db'}"


@lru_cache(maxsize=1)
def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL
    # Render / Neon costumam entregar postgresql:// — SQLAlchemy + psycopg3 precisa do driver.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def is_sqlite(url: str | None = None) -> bool:
    return (url or get_database_url()).startswith("sqlite")
