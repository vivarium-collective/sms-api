"""add 'cancelled' value to jobstatusdb enum

Revision ID: a1c3e5f7b9d2
Revises: 0f991fad32ba
Create Date: 2026-05-11

Formalises the live patch applied to the production database on 2026-05-11.
The jobstatusdb PostgreSQL enum was missing the 'cancelled' value, causing
SQLAlchemy to crash when the job scheduler attempted to write a CANCELLED
status after SLURM jobs were cancelled via scancel.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c3e5f7b9d2"
down_revision: str | Sequence[str] | None = "0f991fad32ba"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 'cancelled' to the jobstatusdb enum.

    Uses IF NOT EXISTS to be idempotent — safe to run against a database
    that already received the live patch.
    """
    op.execute("ALTER TYPE jobstatusdb ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    """Downgrade is a no-op.

    PostgreSQL does not support removing enum values. Removing 'cancelled'
    would require recreating the type and all columns that depend on it,
    which is unsafe to automate. If a rollback is needed, handle manually.
    """
