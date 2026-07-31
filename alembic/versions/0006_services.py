"""create services table

Revision ID: 0006_services
Revises: 0005_recipes
Create Date: 2026-07-31

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_services"
down_revision: Union[str, Sequence[str], None] = "0005_recipes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("recipe_ids", sa.JSON(), nullable=False),
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
    op.create_index(op.f("ix_services_owner_id"), "services", ["owner_id"])
    op.create_index(op.f("ix_services_service_date"), "services", ["service_date"])


def downgrade() -> None:
    op.drop_index(op.f("ix_services_service_date"), table_name="services")
    op.drop_index(op.f("ix_services_owner_id"), table_name="services")
    op.drop_table("services")
