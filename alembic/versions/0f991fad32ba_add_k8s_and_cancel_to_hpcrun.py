"""add k8s_job_name, job_backend, and cancelled status to hpcrun

Revision ID: 0f991fad32ba
Revises: fb7621a73e24
Create Date: 2026-03-31

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f991fad32ba"
down_revision: Union[str, Sequence[str], None] = "fb7621a73e24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add k8s_job_name and job_backend columns, and cancelled status to hpcrun."""
    op.add_column("hpcrun", sa.Column("k8s_job_name", sa.String(), nullable=True))
    op.add_column("hpcrun", sa.Column("job_backend", sa.String(), nullable=False, server_default="slurm"))
    # slurmjobid was NOT NULL in baseline; make it nullable for non-SLURM backends
    op.alter_column("hpcrun", "slurmjobid", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Remove k8s_job_name and job_backend columns."""
    op.alter_column("hpcrun", "slurmjobid", existing_type=sa.Integer(), nullable=False)
    op.drop_column("hpcrun", "job_backend")
    op.drop_column("hpcrun", "k8s_job_name")
