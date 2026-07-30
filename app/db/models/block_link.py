"""Ligação ponderada entre blocos de sabor (peso 1 leve … 3 forte)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class BlockLink(Base):
    __tablename__ = "block_links"
    __table_args__ = (
        UniqueConstraint("source_block_id", "target_block_id", name="uq_block_links_pair"),
        CheckConstraint("weight >= 1 AND weight <= 3", name="ck_block_links_weight"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_block_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_block_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
        return (
            f"<BlockLink {self.source_block_id!r}->{self.target_block_id!r} w={self.weight}>"
        )
