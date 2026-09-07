"""add analysis_options to compose_simulation

Revision ID: f76e43d01841
Revises: c7d1f3a9b2e4
Create Date: 2026-09-07

The compose subsystem's ``compose_simulation`` table is normally bootstrapped
by ``create_compose_db`` (``create_all``), not Alembic -- so a DB the app
already touched has the OLD shape and ``create_all`` never ALTERs it. This
adds ``analysis_options`` (JSONB, nullable) so a compose-run request's
analysis config can be persisted on the row and read back by a later analysis-
chaining task. Idempotent: ``ADD COLUMN IF NOT EXISTS`` so it's a no-op on a
fresh ``create_all`` DB that already has the column.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f76e43d01841"
down_revision: str | Sequence[str] | None = "c7d1f3a9b2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE compose_simulation ADD COLUMN IF NOT EXISTS analysis_options JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE compose_simulation DROP COLUMN IF EXISTS analysis_options")
