"""add tags column to simulation

Revision ID: c1a2b3d4e5f6
Revises: a1c3e5f7b9d2
Create Date: 2026-07-14

Adds a free-form ``tags`` JSONB column (default ``[]``) to the simulation table,
plus a GIN index for containment queries. Tags are site-local data used for
filtering/bundling (e.g. "cd1"), replacing the previous hard-coded tag registry.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: str | Sequence[str] | None = "a1c3e5f7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulation",
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_simulation_tags", "simulation", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_simulation_tags", table_name="simulation")
    op.drop_column("simulation", "tags")
