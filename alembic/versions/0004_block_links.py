"""create block_links table

Revision ID: 0004_block_links
Revises: 0003_flavor_block_records
Create Date: 2026-07-30

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_block_links"
down_revision: Union[str, Sequence[str], None] = "0003_flavor_block_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "block_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_block_id", sa.String(length=120), nullable=False),
        sa.Column("target_block_id", sa.String(length=120), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("weight >= 1 AND weight <= 3", name="ck_block_links_weight"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_block_id", "target_block_id", name="uq_block_links_pair"),
    )
    op.create_index(op.f("ix_block_links_source_block_id"), "block_links", ["source_block_id"])
    op.create_index(op.f("ix_block_links_target_block_id"), "block_links", ["target_block_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_block_links_target_block_id"), table_name="block_links")
    op.drop_index(op.f("ix_block_links_source_block_id"), table_name="block_links")
    op.drop_table("block_links")
