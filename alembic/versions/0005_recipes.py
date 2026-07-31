"""create recipes table

Revision ID: 0005_recipes
Revises: 0004_block_links
Create Date: 2026-07-31

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_recipes"
down_revision: Union[str, Sequence[str], None] = "0004_block_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("composition_id", sa.Uuid(), nullable=True),
        sa.Column("block_ids", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["composition_id"], ["composition_graphs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recipes_owner_id"), "recipes", ["owner_id"])
    op.create_index(op.f("ix_recipes_composition_id"), "recipes", ["composition_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_recipes_composition_id"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_owner_id"), table_name="recipes")
    op.drop_table("recipes")
