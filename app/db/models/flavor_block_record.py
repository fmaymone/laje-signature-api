"""Blocos de sabor editáveis (overrides do catálogo + blocos novos)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base


def _json_type():
    return JSON().with_variant(JSONB(), "postgresql")


class FlavorBlockRecord(Base):
    """Registro persistido que sobrescreve ou acrescenta um bloco do catálogo YAML."""

    __tablename__ = "flavor_block_records"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # True = bloco criado na UI; False = override de um id do catálogo
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    payload: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<FlavorBlockRecord id={self.id!r} custom={self.is_custom}>"
