"""create flavor_block_records table

Revision ID: 0003_flavor_block_records
Revises: 0002_composition_graphs
Create Date: 2026-07-30

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_flavor_block_records"
down_revision: Union[str, Sequence[str], None] = "0002_composition_graphs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flavor_block_records",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("payload", sa.JSON(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("flavor_block_records")
