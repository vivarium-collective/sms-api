"""Tests for the Ray-on-Batch backend: JobId.ray, Batch state mapping, ComputeBackend.RAY,
and SimulationServiceRay submission/status/cancel (boto3 mocked, Postgres via testcontainers)."""

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from sms_api.common.hpc.job_service import JobStatusInfo
from sms_api.common.models import JobBackend, JobId, JobStatus
from sms_api.config import ComputeBackend
from sms_api.simulation.simulation_service_ray import (
    PARCA_CACHE_DIR,
    SIM_OUT_DIR,
    SimulationServiceRay,
)

if TYPE_CHECKING:
    from sms_api.simulation.database_service import DatabaseServiceSQL
    from sms_api.simulation.models import SimulationRequest


def _ray_settings() -> MagicMock:
    """A settings double with the ray_* / S3 fields SimulationServiceRay reads."""
    return MagicMock(
        batch_region="us-gov-west-1",
        s3_work_bucket="mybucket",
        s3_output_prefix="vecoli-output",
        ray_mnp_queue="smscdk-ray-mnp",
        ray_mnp_job_definition="smscdk-ray-mnp",
        ray_num_nodes=3,
        ray_image_tag="ray",
        ray_parca_mode="fast",
        ray_parca_cpus=8,
        ray_n_steps=600,
        ray_chunk=60,
        ray_log_s3_prefix="s3://mybucket/ray-logs/",
        github_token=None,
    )


def _env_of(call: Any) -> dict[str, str]:
    """Extract the node-0 environment dict from a submit_job call's nodeOverrides."""
    node0 = call.kwargs["nodeOverrides"]["nodePropertyOverrides"][0]
    return {e["name"]: e["value"] for e in node0["containerOverrides"]["environment"]}


class TestJobIdRay:
    def test_ray_factory(self) -> None:
        job_id = JobId.ray("abc-123")
        assert job_id.value == "abc-123"
        assert job_id.backend == JobBackend.RAY

    def test_ray_is_not_slurm_int(self) -> None:
        with pytest.raises(TypeError):
            _ = JobId.ray("abc-123").as_slurm_int


class TestFromBatchState:
    @pytest.mark.parametrize(
        ("batch_state", "expected"),
        [
            ("SUBMITTED", JobStatus.QUEUED),
            ("PENDING", JobStatus.QUEUED),
            ("RUNNABLE", JobStatus.QUEUED),
            ("STARTING", JobStatus.PENDING),
            ("RUNNING", JobStatus.RUNNING),
            ("SUCCEEDED", JobStatus.COMPLETED),
            ("FAILED", JobStatus.FAILED),
            ("running", JobStatus.RUNNING),  # case-insensitive
            ("", JobStatus.UNKNOWN),
            ("BOGUS", JobStatus.UNKNOWN),
        ],
    )
    def test_mapping(self, batch_state: str, expected: JobStatus) -> None:
        assert JobStatus.from_batch_state(batch_state) == expected


class TestComputeBackendRay:
    def test_enum_value(self) -> None:
        assert ComputeBackend("ray") == ComputeBackend.RAY

    def test_get_job_backend(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(compute_backend="ray")
            assert get_job_backend() == ComputeBackend.RAY


@pytest.mark.asyncio
class TestSimulationServiceRaySubmit:
    """submit_ecoli_simulation_job submits ParCa (1 node) + sim (N nodes, dependsOn)."""

    async def test_submit_parca_then_sim_with_dependency(
        self,
        experiment_request: "SimulationRequest",
        database_service: "DatabaseServiceSQL",
    ) -> None:
        # Make the seed count deterministic (SimulationConfig allows extra fields).
        setattr(experiment_request.config, "n_init_sims", 2)  # noqa: B010
        simulation = await database_service.insert_simulation(sim_request=experiment_request)

        mock_batch = MagicMock()
        mock_batch.submit_job.side_effect = [{"jobId": "parca-123"}, {"jobId": "sim-456"}]

        service = SimulationServiceRay()
        with (
            patch("sms_api.simulation.simulation_service_ray.get_settings", _ray_settings),
            patch("sms_api.simulation.simulation_service_ray.boto3.client", return_value=mock_batch),
        ):
            job_id = await service.submit_ecoli_simulation_job(
                ecoli_simulation=simulation, database_service=database_service, correlation_id="corr-1"
            )

        # The tracked job is the simulation job.
        assert job_id == JobId.ray("sim-456")
        assert mock_batch.submit_job.call_count == 2

        parca_call, sim_call = mock_batch.submit_job.call_args_list
        parca_env, sim_env = _env_of(parca_call), _env_of(sim_call)

        # ParCa: 1 node, parca command, captures the cache to S3, no dependency.
        assert parca_call.kwargs["nodeOverrides"]["numNodes"] == 1
        assert "v2ecoli-parca" in parca_env["RAY_JOB_CMD"]
        assert parca_env["RAY_OUT_DIR"] == PARCA_CACHE_DIR
        assert "dependsOn" not in parca_call.kwargs

        # Sim: N nodes, ensemble command, gated on the parca job, stages the same cache.
        assert sim_call.kwargs["nodeOverrides"]["numNodes"] == 3
        assert sim_call.kwargs["dependsOn"] == [{"jobId": "parca-123", "type": "SEQUENTIAL"}]
        assert "run_phase0_xarray_ensemble.py" in sim_env["RAY_JOB_CMD"]
        assert "--n-seeds 2" in sim_env["RAY_JOB_CMD"]
        assert "--parallel ray" in sim_env["RAY_JOB_CMD"]
        assert sim_env["RAY_OUT_DIR"] == SIM_OUT_DIR
        assert sim_env["RAY_OUT_S3"] == "s3://mybucket/vecoli-output/" + simulation.config.experiment_id + "/"

        # Cache hand-off: sim stages exactly what parca produced.
        assert sim_env["RAY_STAGE_S3"] == parca_env["RAY_OUT_S3"]
        assert sim_env["RAY_STAGE_DIR"] == PARCA_CACHE_DIR

        # Queue/job-def come from settings.
        assert sim_call.kwargs["jobQueue"] == "smscdk-ray-mnp"
        assert sim_call.kwargs["jobDefinition"] == "smscdk-ray-mnp"


@pytest.mark.asyncio
class TestSimulationServiceRayStatusCancel:
    async def test_get_job_status_running(self) -> None:
        mock_batch = MagicMock()
        mock_batch.describe_jobs.return_value = {
            "jobs": [{"jobId": "sim-456", "status": "RUNNING", "startedAt": 111}]
        }
        service = SimulationServiceRay()
        with (
            patch("sms_api.simulation.simulation_service_ray.get_settings", _ray_settings),
            patch("sms_api.simulation.simulation_service_ray.boto3.client", return_value=mock_batch),
        ):
            info = await service.get_job_status(JobId.ray("sim-456"))
        assert info is not None
        assert info.status == JobStatus.RUNNING
        assert info.job_id == JobId.ray("sim-456")

    async def test_get_job_status_not_found(self) -> None:
        mock_batch = MagicMock()
        mock_batch.describe_jobs.return_value = {"jobs": []}
        service = SimulationServiceRay()
        with (
            patch("sms_api.simulation.simulation_service_ray.get_settings", _ray_settings),
            patch("sms_api.simulation.simulation_service_ray.boto3.client", return_value=mock_batch),
        ):
            assert await service.get_job_status(JobId.ray("missing")) is None

    async def test_get_job_status_local_dispatches_to_local(self) -> None:
        local = MagicMock()
        local.get_status.return_value = JobStatusInfo(job_id=JobId.local("t"), status=JobStatus.COMPLETED)
        service = SimulationServiceRay(local_task_service=local)
        info = await service.get_job_status(JobId.local("t"))
        assert info is not None and info.status == JobStatus.COMPLETED
        local.get_status.assert_called_once_with("t")

    async def test_cancel_terminates_batch_job(self) -> None:
        mock_batch = MagicMock()
        service = SimulationServiceRay()
        with (
            patch("sms_api.simulation.simulation_service_ray.get_settings", _ray_settings),
            patch("sms_api.simulation.simulation_service_ray.boto3.client", return_value=mock_batch),
        ):
            await service.cancel_job(JobId.ray("sim-456"))
        mock_batch.terminate_job.assert_called_once()
        assert mock_batch.terminate_job.call_args.kwargs["jobId"] == "sim-456"
