"""Unit tests for the pure schema-diff logic (no database access)."""

from sms_api.simulation.schema_diff import DbSchema, diff_schemas


def _expected() -> DbSchema:
    return DbSchema(
        tables={
            "simulation": {"id", "experiment_id", "config", "tags"},
            "hpcrun": {"id", "job_id_ext", "job_backend"},
            "compose_run": {"id", "status"},  # a table create_all would add on boot
        },
        enums={"jobstatusdb": {"waiting", "running", "cancelled"}},
    )


def test_no_drift_when_db_matches_orm() -> None:
    actual = DbSchema(
        tables={
            "simulation": {"id", "experiment_id", "config", "tags"},
            "hpcrun": {"id", "job_id_ext", "job_backend"},
            "compose_run": {"id", "status"},
        },
        enums={"jobstatusdb": {"waiting", "running", "cancelled"}},
    )
    diff = diff_schemas(_expected(), actual)
    assert not diff.has_blocking_drift
    assert diff.missing_tables == []
    assert diff.missing_columns == {}


def test_missing_column_on_existing_table_is_blocking() -> None:
    # tags column absent on the existing simulation table -> blocking (create_all won't add it).
    actual = DbSchema(
        tables={
            "simulation": {"id", "experiment_id", "config"},  # no 'tags'
            "hpcrun": {"id", "job_id_ext", "job_backend"},
            "compose_run": {"id", "status"},
        },
        enums={"jobstatusdb": {"waiting", "running", "cancelled"}},
    )
    diff = diff_schemas(_expected(), actual)
    assert diff.has_blocking_drift
    assert diff.missing_columns == {"simulation": ["tags"]}


def test_missing_table_is_info_not_blocking() -> None:
    # compose_run entirely absent -> create_all creates it on boot -> INFO only.
    actual = DbSchema(
        tables={
            "simulation": {"id", "experiment_id", "config", "tags"},
            "hpcrun": {"id", "job_id_ext", "job_backend"},
        },
        enums={"jobstatusdb": {"waiting", "running", "cancelled"}},
    )
    diff = diff_schemas(_expected(), actual)
    assert diff.missing_tables == ["compose_run"]
    assert not diff.has_blocking_drift


def test_missing_enum_value_is_blocking() -> None:
    actual = DbSchema(
        tables=_expected().tables,
        enums={"jobstatusdb": {"waiting", "running"}},  # missing 'cancelled'
    )
    diff = diff_schemas(_expected(), actual)
    assert diff.has_blocking_drift
    assert diff.missing_enum_values == {"jobstatusdb": ["cancelled"]}


def test_missing_enum_type_is_blocking() -> None:
    actual = DbSchema(tables=_expected().tables, enums={})
    diff = diff_schemas(_expected(), actual)
    assert diff.has_blocking_drift
    assert diff.missing_enum_types == ["jobstatusdb"]


def test_alembic_version_table_is_ignored() -> None:
    actual = DbSchema(
        tables={**_expected().tables, "alembic_version": {"version_num"}},
        enums=_expected().enums,
    )
    diff = diff_schemas(_expected(), actual)
    assert "alembic_version" not in diff.extra_tables
    assert not diff.has_blocking_drift


def test_extra_tables_and_columns_are_info_only() -> None:
    actual = DbSchema(
        tables={
            "simulation": {"id", "experiment_id", "config", "tags", "legacy_col"},
            "hpcrun": {"id", "job_id_ext", "job_backend"},
            "compose_run": {"id", "status"},
            "old_orphan_table": {"id"},
        },
        enums={"jobstatusdb": {"waiting", "running", "cancelled"}},
    )
    diff = diff_schemas(_expected(), actual)
    assert not diff.has_blocking_drift
    assert diff.extra_tables == ["old_orphan_table"]
    assert diff.extra_columns == {"simulation": ["legacy_col"]}
