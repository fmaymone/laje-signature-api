"""Base declarativa SQLAlchemy."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base para todos os models ORM."""
