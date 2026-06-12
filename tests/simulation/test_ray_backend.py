"""Tests for the Ray-on-Batch backend: JobId.ray, Batch state mapping, ComputeBackend.RAY,
and SimulationServiceRay submission/status/cancel (boto3 mocked, Postgres via testcontainers)."""

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

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
        ray_ecr_repository="v2ecoli",
        ecr_account_id="476270107793",
        ray_parca_mode="fast",
        ray_parca_cpus=8,
        ray_n_steps=600,
        ray_chunk=60,
        ray_log_s3_prefix="s3://mybucket/ray-logs/",
        # build settings (DooD image build)
        build_amd64_queue="smscdk-vecoli-build-amd64",
        build_job_definition="smscdk-vecoli-dind-build",
        build_git_secret_arn="arn:aws-us-gov:secretsmanager:us-gov-west-1:123:secret:vecoli-github-pat",  # noqa: S106  (ARN, not a secret)
        github_token=None,
    )


def _fake_batch(submit_ids: list[str]) -> MagicMock:
    """A boto3 Batch mock that supports the per-commit job-def derivation + submits.

    describe_job_definitions returns the CDK base (with node properties to clone) for the
    base name, and "no existing revision" for the per-commit name; register returns rev 1.
    """
    b = MagicMock()
    base_node_props = {
        "numNodes": 4,
        "mainNode": 0,
        "nodeRangeProperties": [
            {"targetNodes": "0:", "container": {"image": "111.dkr.ecr.x/vecoli:ray", "vcpus": 16}}
        ],
    }

    def _describe(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("jobDefinitionName") == "smscdk-ray-mnp":  # the base
            return {"jobDefinitions": [{"revision": 7, "nodeProperties": base_node_props}]}
        return {"jobDefinitions": []}  # per-commit: none yet

    b.describe_job_definitions.side_effect = _describe
    b.register_job_definition.side_effect = lambda **kw: {"jobDefinitionName": kw["jobDefinitionName"], "revision": 1}
    b.submit_job.side_effect = [{"jobId": jid} for jid in submit_ids]
    return b


def _overrides(call: Any) -> list[dict[str, Any]]:
    return list(call.kwargs["nodeOverrides"]["nodePropertyOverrides"])


def _env_at(call: Any, index: int) -> dict[str, str]:
    """Env dict for the override at `index` (0 = head/`0:0`, 1 = workers/`1:`)."""
    ov = _overrides(call)[index]
    return {e["name"]: e["value"] for e in ov["containerOverrides"]["environment"]}


def _env_of(call: Any) -> dict[str, str]:
    """Head (node 0) environment dict."""
    return _env_at(call, 0)


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

        mock_batch = _fake_batch(["parca-123", "sim-456"])

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
        # A 1-node job has only the head override (no worker `1:` range).
        assert parca_call.kwargs["nodeOverrides"]["numNodes"] == 1
        assert len(_overrides(parca_call)) == 1
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

        # Multi-node env targeting: workers (`1:`) must ALSO get the staging + output
        # knobs (they need the cache to run seeds and must ship their own zarr), but
        # NOT RAY_JOB_CMD (only the head runs the driver).
        sim_overrides = _overrides(sim_call)
        assert len(sim_overrides) == 2
        assert sim_overrides[0]["targetNodes"] == "0:0"
        assert sim_overrides[1]["targetNodes"] == "1:"
        worker_env = _env_at(sim_call, 1)
        assert "RAY_JOB_CMD" not in worker_env
        assert "RAY_REPORT_PATH" not in worker_env
        assert worker_env["RAY_STAGE_S3"] == sim_env["RAY_STAGE_S3"]
        assert worker_env["RAY_STAGE_DIR"] == PARCA_CACHE_DIR
        assert worker_env["RAY_OUT_S3"] == sim_env["RAY_OUT_S3"]
        assert worker_env["RAY_OUT_DIR"] == SIM_OUT_DIR

        # Queue comes from settings; both jobs run the SAME per-commit job-def revision
        # (derived from the base) so they use the simulator's TRUE commit image.
        simulator = await database_service.get_simulator(simulator_id=simulation.simulator_id)
        assert simulator is not None
        commit = simulator.git_commit_hash
        assert sim_call.kwargs["jobQueue"] == "smscdk-ray-mnp"
        assert sim_call.kwargs["jobDefinition"] == f"smscdk-ray-mnp-{commit}:1"
        assert parca_call.kwargs["jobDefinition"] == sim_call.kwargs["jobDefinition"]

        # The per-commit job def was registered cloning the base, with the image swapped
        # to v2ecoli:<commit> on every node range (never vecoli, never :latest).
        reg = mock_batch.register_job_definition.call_args
        assert reg.kwargs["type"] == "multinode"
        reg_images = {nr["container"]["image"] for nr in reg.kwargs["nodeProperties"]["nodeRangeProperties"]}
        assert reg_images == {f"476270107793.dkr.ecr.us-gov-west-1.amazonaws.com/v2ecoli:{commit}"}


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


def _v2ecoli_simulator() -> Any:
    from sms_api.simulation.models import SimulatorVersion

    return SimulatorVersion(
        database_id=1,
        git_commit_hash="abc1234",
        git_repo_url="https://github.com/vivarium-collective/v2Ecoli",
        git_branch="main",
    )


class TestSimulationServiceRayBuild:
    """submit_build_image_job builds the workload-owned v2ecoli image via a DooD Batch job."""

    def test_build_command_clones_v2ecoli_and_runs_its_recipe(self) -> None:
        service = SimulationServiceRay()
        with patch("sms_api.simulation.simulation_service_ray.get_settings", _ray_settings):
            cmd = service._build_command(_v2ecoli_simulator())
        assert cmd[0] == "sh" and cmd[1] == "-c"
        script = cmd[2]
        assert "git clone --branch main --single-branch" in script
        assert "v2Ecoli" in script  # the workload repo, not vEcoli
        assert "git checkout abc1234" in script
        # runs v2ecoli's OWN recipe (symmetric with K8s running vEcoli's), not an sms-cdk script
        assert "docker/build-and-push-ecr.sh -i abc1234 -r v2ecoli -R us-gov-west-1" in script

    @pytest.mark.asyncio
    async def test_run_build_submits_to_amd64_queue_and_polls(self) -> None:
        service = SimulationServiceRay()
        with (
            patch("sms_api.simulation.simulation_service_ray.get_settings", _ray_settings),
            patch(
                "sms_api.simulation.simulation_service_ray.batch_build.submit_batch_build",
                new=AsyncMock(return_value="build-job-1"),
            ) as mock_submit,
            patch(
                "sms_api.simulation.simulation_service_ray.batch_build.poll_batch_jobs",
                new=AsyncMock(),
            ) as mock_poll,
        ):
            await service._run_build(_v2ecoli_simulator())
        assert mock_submit.await_count == 1
        assert mock_submit.call_args.kwargs["queue"] == "smscdk-vecoli-build-amd64"
        assert "docker/build-and-push-ecr.sh" in mock_submit.call_args.kwargs["command"][2]
        mock_poll.assert_awaited_once_with(["build-job-1"])

    @pytest.mark.asyncio
    async def test_submit_build_returns_local_job(self) -> None:
        service = SimulationServiceRay()
        with (
            patch("sms_api.simulation.simulation_service_ray.get_settings", _ray_settings),
            patch(
                "sms_api.simulation.simulation_service_ray.batch_build.submit_batch_build",
                new=AsyncMock(return_value="bj"),
            ),
            patch("sms_api.simulation.simulation_service_ray.batch_build.poll_batch_jobs", new=AsyncMock()),
        ):
            job_id = await service.submit_build_image_job(_v2ecoli_simulator())
        assert job_id.backend == JobBackend.LOCAL


class TestEnsureMnpJobDef:
    """Per-commit MNP job-def derivation (true commit image, no per-submission override)."""

    def test_reuses_existing_revision_for_same_image(self) -> None:
        image = "476270107793.dkr.ecr.us-gov-west-1.amazonaws.com/v2ecoli:abc1234"
        mock_batch = MagicMock()
        mock_batch.describe_job_definitions.return_value = {
            "jobDefinitions": [
                {"revision": 5, "nodeProperties": {"nodeRangeProperties": [{"container": {"image": image}}]}}
            ]
        }
        service = SimulationServiceRay()
        with (
            patch("sms_api.simulation.simulation_service_ray.get_settings", _ray_settings),
            patch("sms_api.simulation.simulation_service_ray.boto3.client", return_value=mock_batch),
        ):
            jd = service._ensure_mnp_job_def(image, "abc1234")
        assert jd == "smscdk-ray-mnp-abc1234:5"
        mock_batch.register_job_definition.assert_not_called()
