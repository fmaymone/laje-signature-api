"""Receita persistida: blocos + passos com tempo antes do serviço."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base


def _json_type():
    """JSONB no Postgres; JSON genérico (sqlite) nos demais."""
    return JSON().with_variant(JSONB(), "postgresql")


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Receita")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    composition_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("composition_graphs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    # ["block_id", ...]
    block_ids: Mapped[list[str]] = mapped_column(
        _json_type(),
        nullable=False,
        default=lambda: [],
    )
    # [{ ingredient_id, quantity, unit, notes? }]
    ingredients: Mapped[list[dict[str, Any]]] = mapped_column(
        _json_type(),
        nullable=False,
        default=lambda: [],
    )
    # [{ id, name }] — sempre inclui { id: "main", name: "Principal" }
    lanes: Mapped[list[dict[str, Any]]] = mapped_column(
        _json_type(),
        nullable=False,
        default=lambda: [{"id": "main", "name": "Principal"}],
    )
    # [{ id, process, description?, time_before_service_minutes, duration_minutes, lane_id }]
    steps: Mapped[list[dict[str, Any]]] = mapped_column(
        _json_type(),
        nullable=False,
        default=lambda: [],
    )
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
        return f"<Recipe id={self.id} title={self.title!r}>"
