"""ingredients + stocks + recipe servings/ingredients

Revision ID: 0007_ingredients
Revises: 0006_services
Create Date: 2026-07-31

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_ingredients"
down_revision: Union[str, Sequence[str], None] = "0006_services"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("default_unit", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_ingredients_slug"), "ingredients", ["slug"])

    op.create_table(
        "ingredient_stocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("reorder_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status_override", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "ingredient_id", name="uq_ingredient_stocks_owner_ingredient"),
    )
    op.create_index(op.f("ix_ingredient_stocks_owner_id"), "ingredient_stocks", ["owner_id"])
    op.create_index(
        op.f("ix_ingredient_stocks_ingredient_id"), "ingredient_stocks", ["ingredient_id"]
    )

    op.add_column(
        "recipes",
        sa.Column("servings", sa.Integer(), nullable=False, server_default="4"),
    )
    op.add_column(
        "recipes",
        sa.Column("ingredients", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("recipes", "ingredients")
    op.drop_column("recipes", "servings")
    op.drop_index(op.f("ix_ingredient_stocks_ingredient_id"), table_name="ingredient_stocks")
    op.drop_index(op.f("ix_ingredient_stocks_owner_id"), table_name="ingredient_stocks")
    op.drop_table("ingredient_stocks")
    op.drop_index(op.f("ix_ingredients_slug"), table_name="ingredients")
    op.drop_table("ingredients")
