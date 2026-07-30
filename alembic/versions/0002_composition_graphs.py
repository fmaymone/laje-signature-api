"""create composition_graphs table

Revision ID: 0002_composition_graphs
Revises: 0001_users
Create Date: 2026-07-30

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_composition_graphs"
down_revision: Union[str, Sequence[str], None] = "0001_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "composition_graphs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("edges", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_composition_graphs_owner_id"),
        "composition_graphs",
        ["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_composition_graphs_owner_id"), table_name="composition_graphs")
    op.drop_table("composition_graphs")
