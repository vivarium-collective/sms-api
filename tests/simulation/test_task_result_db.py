"""DatabaseService tests for the `task` table (viva-api#631 slice 1).

Run against the testcontainer Postgres (the enum + table are created by
create_all from the ORM). Mirrors tests/simulation/test_analysis_result_db.py.
"""

import pytest

from viva_api.common.models import JobStatus
from viva_api.simulation.database_service import DatabaseServiceSQL
from viva_api.simulation.tables_orm import TaskStatusDB


@pytest.mark.asyncio
async def test_record_and_get_task(database_service: DatabaseServiceSQL) -> None:
    rec = await database_service.record_task(
        name="footask",
        script="scripts/foo.py",
        args=["--x", "1"],
        sim_data_refs={"chassis": "s3://bucket/chassis.tar"},
        memory_class="standard",
        status=TaskStatusDB.COMPUTING,
        job_id_ext="c-1",
        out_uri="s3://bucket/vecoli-output/tasks/footask-abcdef",
    )
    assert rec.name == "footask"
    assert rec.script == "scripts/foo.py"
    assert rec.args == ["--x", "1"]
    assert rec.sim_data_refs == {"chassis": "s3://bucket/chassis.tar"}
    assert rec.status == JobStatus.RUNNING  # COMPUTING -> RUNNING in the DTO
    assert rec.job_id_ext == "c-1"

    fetched = await database_service.get_task(rec.database_id)
    assert fetched.database_id == rec.database_id
    assert fetched.name == "footask"
    assert fetched.out_uri and fetched.out_uri.endswith("footask-abcdef")


@pytest.mark.asyncio
async def test_record_task_no_dedup_inserts_a_new_row_each_time(database_service: DatabaseServiceSQL) -> None:
    """Unlike record_analysis, record_task is a plain insert -- two submissions
    of the "same" script produce two distinct rows, not an update-in-place."""
    r1 = await database_service.record_task(
        name="dup",
        script="scripts/dup.py",
        args=[],
        sim_data_refs=None,
        memory_class="standard",
        status=TaskStatusDB.COMPUTING,
    )
    r2 = await database_service.record_task(
        name="dup",
        script="scripts/dup.py",
        args=[],
        sim_data_refs=None,
        memory_class="standard",
        status=TaskStatusDB.COMPUTING,
    )
    assert r1.database_id != r2.database_id


@pytest.mark.asyncio
async def test_update_task_status(database_service: DatabaseServiceSQL) -> None:
    rec = await database_service.record_task(
        name="footask",
        script="scripts/foo.py",
        args=[],
        sim_data_refs=None,
        memory_class="standard",
        status=TaskStatusDB.COMPUTING,
    )
    updated = await database_service.update_task_status(
        rec.database_id, TaskStatusDB.READY, result_uri="s3://bucket/footask/result.json"
    )
    assert updated.status == JobStatus.COMPLETED
    assert updated.result_uri == "s3://bucket/footask/result.json"


@pytest.mark.asyncio
async def test_update_task_status_failed_carries_error_message(database_service: DatabaseServiceSQL) -> None:
    rec = await database_service.record_task(
        name="footask",
        script="scripts/foo.py",
        args=[],
        sim_data_refs=None,
        memory_class="standard",
        status=TaskStatusDB.COMPUTING,
    )
    updated = await database_service.update_task_status(rec.database_id, TaskStatusDB.FAILED, error_message="boom")
    assert updated.status == JobStatus.FAILED
    assert updated.error_message == "boom"


@pytest.mark.asyncio
async def test_get_missing_task_raises(database_service: DatabaseServiceSQL) -> None:
    with pytest.raises(RuntimeError):
        await database_service.get_task(999999)
