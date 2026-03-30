"""add batch_job_id and job_backend columns to hpcrun

Revision ID: a1b2c3d4e5f6
Revises: fb7621a73e24
Create Date: 2026-03-23

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "fb7621a73e24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add batch_job_id and job_backend columns to hpcrun table."""
    op.add_column("hpcrun", sa.Column("batch_job_id", sa.String(), nullable=True))
    op.add_column("hpcrun", sa.Column("job_backend", sa.String(), nullable=False, server_default="slurm"))


def downgrade() -> None:
    """Remove batch_job_id and job_backend columns from hpcrun table."""
    op.drop_column("hpcrun", "job_backend")
    op.drop_column("hpcrun", "batch_job_id")
