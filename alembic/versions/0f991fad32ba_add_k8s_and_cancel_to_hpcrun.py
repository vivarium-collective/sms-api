"""add job_id_ext, job_backend, and cancelled status to hpcrun

Revision ID: 0f991fad32ba
Revises: fb7621a73e24
Create Date: 2026-03-31

Replaces the integer slurmjobid column with a generic string job_id_ext
that supports SLURM (int-as-string), K8s job names, and local task UUIDs.
Adds job_backend column to distinguish backends. Existing slurmjobid
values are migrated to job_id_ext as strings.
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
    """Add job_id_ext and job_backend, migrate slurmjobid, drop slurmjobid."""
    # 1. Add new columns
    op.add_column("hpcrun", sa.Column("job_id_ext", sa.String(), nullable=True))
    op.add_column("hpcrun", sa.Column("job_backend", sa.String(), nullable=False, server_default="slurm"))

    # 2. Migrate existing slurmjobid integers to job_id_ext strings
    op.execute("UPDATE hpcrun SET job_id_ext = CAST(slurmjobid AS VARCHAR) WHERE slurmjobid IS NOT NULL")

    # 3. Drop old column
    op.drop_column("hpcrun", "slurmjobid")


def downgrade() -> None:
    """Restore slurmjobid column, migrate back from job_id_ext."""
    # 1. Add slurmjobid back
    op.add_column("hpcrun", sa.Column("slurmjobid", sa.Integer(), nullable=True))

    # 2. Migrate SLURM job IDs back to integer (non-numeric values become NULL)
    op.execute(
        "UPDATE hpcrun SET slurmjobid = CAST(job_id_ext AS INTEGER) "
        "WHERE job_backend = 'slurm' AND job_id_ext ~ '^[0-9]+$'"
    )

    # 3. Drop new columns
    op.drop_column("hpcrun", "job_backend")
    op.drop_column("hpcrun", "job_id_ext")
