"""add observability columns, event/span tables, PARTIAL status

Revision ID: a3b5c7d9e1f2
Revises: f76e43d01841
Create Date: 2026-09-10

Observability plan (docs/plan-observability.md), viva-api part A/B storage:

* ``hpcrun`` gains ``exit_code``, ``attempt``, ``error_source``, ``trace_id``
  (indexed), ``campaign_span_id``, ``events_s3_prefix``, ``events_cursor``
  (JSONB), ``stage``, ``generation``, ``last_event_at`` -- all nullable, so
  every existing row is untouched.
* ``hpcrun_event``: one structured event per row from a run's task stream
  (``tick`` heartbeats are never stored); unique on ``(trace_id, source, seq)``
  so re-ingesting an ``events.jsonl`` object is idempotent.
* ``hpcrun_span``: the run's trace tree (campaign > parca / lineage / analysis >
  generation > ...), materialised from ``span_start``/``span_end`` events.
* ``jobstatusdb`` gains the ``PARTIAL`` label (bound by NAME, see 44335812e447):
  a terminal state that is not a success -- a Nextflow head that exited 0 under
  ``errorStrategy finish`` after a task failed, or a chain campaign with k/N
  seeds succeeded. Both were reported as FAILED before.

Idempotent throughout (``IF NOT EXISTS``) so it is a no-op on a fresh
``create_all`` database that already has every object.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b5c7d9e1f2"
down_revision: str | Sequence[str] | None = "f76e43d01841"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_HPCRUN_COLUMNS: tuple[tuple[str, str], ...] = (
    ("exit_code", "INTEGER"),
    ("attempt", "INTEGER"),
    ("error_source", "VARCHAR"),
    ("trace_id", "VARCHAR"),
    ("campaign_span_id", "VARCHAR"),
    ("events_s3_prefix", "VARCHAR"),
    ("events_cursor", "JSONB"),
    ("stage", "VARCHAR"),
    ("generation", "INTEGER"),
    ("last_event_at", "TIMESTAMP WITHOUT TIME ZONE"),
)


def upgrade() -> None:
    for name, sql_type in _HPCRUN_COLUMNS:
        op.execute(f"ALTER TABLE hpcrun ADD COLUMN IF NOT EXISTS {name} {sql_type}")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hpcrun_trace_id ON hpcrun (trace_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hpcrun_event (
            id SERIAL PRIMARY KEY,
            hpcrun_id INTEGER NOT NULL REFERENCES hpcrun (id),
            trace_id VARCHAR NOT NULL,
            source VARCHAR NOT NULL,
            seq INTEGER NOT NULL,
            ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            layer VARCHAR NOT NULL,
            event VARCHAR NOT NULL,
            level VARCHAR NOT NULL DEFAULT 'info',
            generation INTEGER,
            global_time DOUBLE PRECISION,
            wall_time DOUBLE PRECISION,
            span_id VARCHAR,
            parent_span_id VARCHAR,
            payload JSONB,
            tags JSONB,
            CONSTRAINT uq_hpcrun_event_trace_source_seq UNIQUE (trace_id, source, seq)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_hpcrun_event_hpcrun_id ON hpcrun_event (hpcrun_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hpcrun_event_trace_id ON hpcrun_event (trace_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hpcrun_event_trace_span ON hpcrun_event (trace_id, span_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hpcrun_span (
            id SERIAL PRIMARY KEY,
            hpcrun_id INTEGER NOT NULL REFERENCES hpcrun (id),
            trace_id VARCHAR NOT NULL,
            span_id VARCHAR NOT NULL,
            parent_span_id VARCHAR,
            name VARCHAR NOT NULL,
            attrs JSONB,
            start_ts TIMESTAMP WITHOUT TIME ZONE,
            end_ts TIMESTAMP WITHOUT TIME ZONE,
            status VARCHAR,
            error VARCHAR,
            CONSTRAINT uq_hpcrun_span_trace_span UNIQUE (trace_id, span_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_hpcrun_span_hpcrun_id ON hpcrun_span (hpcrun_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hpcrun_span_trace_id ON hpcrun_span (trace_id)")

    op.execute("ALTER TYPE jobstatusdb ADD VALUE IF NOT EXISTS 'PARTIAL'")


def downgrade() -> None:
    """Drop the tables and columns. The enum label stays: Postgres has no DROP
    VALUE (see 44335812e447's downgrade for the same reasoning)."""
    op.execute("DROP TABLE IF EXISTS hpcrun_span")
    op.execute("DROP TABLE IF EXISTS hpcrun_event")
    op.execute("DROP INDEX IF EXISTS ix_hpcrun_trace_id")
    for name, _ in _HPCRUN_COLUMNS:
        op.execute(f"ALTER TABLE hpcrun DROP COLUMN IF EXISTS {name}")
