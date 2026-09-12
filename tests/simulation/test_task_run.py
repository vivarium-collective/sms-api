"""In-region task-run verb (viva-api#631 slice 1).

``SimulationServiceRay.submit_task``/``get_task_status`` reuse the SAME
standalone container path (``_ensure_container_job_def`` + ``_submit_container``)
ParCa and the analysis DAG node already use -- the only new behavior is
building the ``python <script> <args...>`` command line and recording/polling
the result through ``DatabaseService.record_task``/``get_task``/
``update_task_status``.

Offline: an explicit batch double, settings doubles, a mocked database_service,
no sockets.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.simulation.test_ray_backend import (
    _container_settings,
    _fake_container_batch,
)
from viva_api.common.models import JobStatus
from viva_api.simulation.models import TaskDTO, TaskRunRequest
from viva_api.simulation.simulation_service_ray import SimulationServiceRay
from viva_api.simulation.tables_orm import TaskStatusDB


def _submitted_task_dto(**overrides: object) -> TaskDTO:
    base: dict[str, object] = {
        "database_id": 1,
        "name": "footask",
        "script": "scripts/foo.py",
        "args": ["--x", "1"],
        "sim_data_refs": None,
        "memory_class": "standard",
        "status": JobStatus.RUNNING,
        "job_id_ext": "c-1",
        "out_uri": "s3://mybucket/vecoli-output/tasks/footask-abcdef",
        "result_uri": None,
        "error_message": None,
    }
    base.update(overrides)
    return TaskDTO(**base)  # type: ignore[arg-type]


def _submit_task(
    request: TaskRunRequest, *, database_service: AsyncMock, submit_ids: list[str]
) -> tuple[TaskDTO, MagicMock]:
    batch = _fake_container_batch(submit_ids)
    service = SimulationServiceRay()
    with (
        patch("viva_api.simulation.simulation_service_ray.get_settings", _container_settings),
        patch("viva_api.common.storage.data_layout.get_settings", _container_settings),
        patch("viva_api.simulation.simulation_service_ray.boto3.client", return_value=batch),
    ):
        import asyncio

        result = asyncio.run(service.submit_task(request, database_service))
    return result, batch


def test_submit_task_builds_expected_job_cmd_and_memory_class() -> None:
    request = TaskRunRequest(
        script="scripts/foo.py",
        args=["--x", "1"],
        memory_class="standard",
        commit="abc1234",
        name="footask",
    )
    database_service = AsyncMock()
    database_service.record_task.return_value = _submitted_task_dto()

    result, batch = _submit_task(request, database_service=database_service, submit_ids=["c-1"])

    (call,) = batch.submit_job.call_args_list
    env = {e["name"]: e["value"] for e in call.kwargs["containerOverrides"]["environment"]}
    assert env["CONTAINER_JOB_CMD"] == "python scripts/foo.py --x 1"
    assert call.kwargs["jobQueue"] == "smscdk-ray-standalone"  # memory_class=standard -> standard queue

    database_service.record_task.assert_awaited_once()
    kwargs = database_service.record_task.call_args.kwargs
    assert kwargs["name"] == "footask"
    assert kwargs["script"] == "scripts/foo.py"
    assert kwargs["args"] == ["--x", "1"]
    assert kwargs["status"] == TaskStatusDB.COMPUTING
    assert kwargs["job_id_ext"] == "c-1"
    assert kwargs["out_uri"] and "tasks/" in kwargs["out_uri"]

    assert result.database_id == 1
    assert result.job_id_ext == "c-1"


def test_submit_task_routes_large_memory_class_to_large_queue() -> None:
    request = TaskRunRequest(script="scripts/foo.py", memory_class="large", commit="abc1234")
    database_service = AsyncMock()
    database_service.record_task.return_value = _submitted_task_dto(memory_class="large")

    batch = _fake_container_batch(["c-2"])
    service = SimulationServiceRay()
    settings = _container_settings(ray_container_large_queue="smscdk-ray-standalone-large")
    with (
        patch("viva_api.simulation.simulation_service_ray.get_settings", lambda: settings),
        patch("viva_api.common.storage.data_layout.get_settings", lambda: settings),
        patch("viva_api.simulation.simulation_service_ray.boto3.client", return_value=batch),
    ):
        import asyncio

        asyncio.run(service.submit_task(request, database_service))

    (call,) = batch.submit_job.call_args_list
    assert call.kwargs["jobQueue"] == "smscdk-ray-standalone-large"


def test_submit_task_no_args_omits_trailing_space() -> None:
    request = TaskRunRequest(script="scripts/foo.py", commit="abc1234")
    database_service = AsyncMock()
    database_service.record_task.return_value = _submitted_task_dto(args=[])

    _, batch = _submit_task(request, database_service=database_service, submit_ids=["c-3"])
    (call,) = batch.submit_job.call_args_list
    env = {e["name"]: e["value"] for e in call.kwargs["containerOverrides"]["environment"]}
    assert env["CONTAINER_JOB_CMD"] == "python scripts/foo.py"


def test_submit_task_passes_sim_data_refs_as_json_env() -> None:
    request = TaskRunRequest(
        script="scripts/foo.py",
        sim_data_refs={"chassis": "s3://bucket/chassis.tar"},
        commit="abc1234",
    )
    database_service = AsyncMock()
    database_service.record_task.return_value = _submitted_task_dto(sim_data_refs=request.sim_data_refs)

    _, batch = _submit_task(request, database_service=database_service, submit_ids=["c-4"])
    (call,) = batch.submit_job.call_args_list
    env = {e["name"]: e["value"] for e in call.kwargs["containerOverrides"]["environment"]}
    assert env["TASK_SIM_DATA_REFS"] == '{"chassis": "s3://bucket/chassis.tar"}'


@pytest.mark.asyncio
async def test_get_task_status_maps_succeeded_to_ready() -> None:
    service = SimulationServiceRay()
    database_service = AsyncMock()
    database_service.get_task.return_value = _submitted_task_dto(status=JobStatus.RUNNING)
    database_service.update_task_status.return_value = _submitted_task_dto(status=JobStatus.COMPLETED)

    with patch.object(service, "get_batch_job_statuses", return_value={"c-1": JobStatus.COMPLETED}):
        result = await service.get_task_status(1, database_service)

    database_service.update_task_status.assert_awaited_once_with(1, TaskStatusDB.READY)
    assert result.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_task_status_maps_failed_to_failed() -> None:
    service = SimulationServiceRay()
    database_service = AsyncMock()
    database_service.get_task.return_value = _submitted_task_dto(status=JobStatus.RUNNING)
    database_service.update_task_status.return_value = _submitted_task_dto(status=JobStatus.FAILED)

    with patch.object(service, "get_batch_job_statuses", return_value={"c-1": JobStatus.FAILED}):
        result = await service.get_task_status(1, database_service)

    database_service.update_task_status.assert_awaited_once_with(1, TaskStatusDB.FAILED)
    assert result.status == JobStatus.FAILED


@pytest.mark.asyncio
async def test_get_task_status_without_job_id_ext_skips_batch_poll() -> None:
    service = SimulationServiceRay()
    database_service = AsyncMock()
    database_service.get_task.return_value = _submitted_task_dto(job_id_ext=None)

    result = await service.get_task_status(1, database_service)

    database_service.update_task_status.assert_not_called()
    assert result.job_id_ext is None


@pytest.mark.asyncio
async def test_get_task_status_not_yet_visible_in_batch_leaves_status_unchanged() -> None:
    """An id absent from describe_jobs (eventual-consistency lag right after
    submission) must not be treated as terminal -- same discipline
    get_batch_job_statuses already documents for its other callers."""
    service = SimulationServiceRay()
    database_service = AsyncMock()
    database_service.get_task.return_value = _submitted_task_dto(status=JobStatus.RUNNING)

    with patch.object(service, "get_batch_job_statuses", return_value={}):
        result = await service.get_task_status(1, database_service)

    database_service.update_task_status.assert_not_called()
    assert result.status == JobStatus.RUNNING
