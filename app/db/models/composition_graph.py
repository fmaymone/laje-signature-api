"""Grafo de composição: blocos posicionados + ligações entre arestas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base


def _json_type():
    """JSONB no Postgres; JSON genérico (sqlite) nos demais."""
    return JSON().with_variant(JSONB(), "postgresql")


class CompositionGraph(Base):
    __tablename__ = "composition_graphs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Composição")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # [{ id, block_id, position: { x, y } }]
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(
        _json_type(),
        nullable=False,
        default=lambda: [],
    )
    # [{ id, source, target, sourceHandle?, targetHandle? }]
    edges: Mapped[list[dict[str, Any]]] = mapped_column(
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
        return f"<CompositionGraph id={self.id} title={self.title!r}>"
