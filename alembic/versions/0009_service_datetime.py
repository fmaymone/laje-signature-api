"""service_date as datetime (with time of day)

Revision ID: 0009_service_datetime
Revises: 0008_recipe_lanes
Create Date: 2026-08-03

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_service_datetime"
down_revision: Union[str, Sequence[str], None] = "0008_recipe_lanes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.alter_column(
            "services",
            "service_date",
            existing_type=sa.Date(),
            type_=sa.DateTime(timezone=True),
            postgresql_using="((service_date::timestamp + time '12:00') AT TIME ZONE 'UTC')",
            nullable=False,
        )
    else:
        with op.batch_alter_table("services") as batch_op:
            batch_op.alter_column(
                "service_date",
                existing_type=sa.Date(),
                type_=sa.DateTime(timezone=True),
                nullable=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.alter_column(
            "services",
            "service_date",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.Date(),
            postgresql_using="(service_date AT TIME ZONE 'UTC')::date",
            nullable=False,
        )
    else:
        with op.batch_alter_table("services") as batch_op:
            batch_op.alter_column(
                "service_date",
                existing_type=sa.DateTime(timezone=True),
                type_=sa.Date(),
                nullable=False,
            )
