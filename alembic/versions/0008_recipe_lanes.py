"""recipe parallel work lanes

Revision ID: 0008_recipe_lanes
Revises: 0007_ingredients
Create Date: 2026-07-31

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_recipe_lanes"
down_revision: Union[str, Sequence[str], None] = "0007_ingredients"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column(
            "lanes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text(
                '\'[{"id": "main", "name": "Principal"}]\''
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("recipes", "lanes")
