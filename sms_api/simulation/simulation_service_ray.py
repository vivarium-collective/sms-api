"""AWS Batch multi-node-parallel (MNP) Ray implementation of SimulationService.

The v2ecoli whole-cell sim runs distributed on a *transient* Ray cluster: one
Batch MNP job gang-schedules N nodes, the sms-cdk entrypoint
(`ray-batch-entrypoint.sh`) forms the Ray cluster, stages a ParCa cache from S3,
exports ``RAY_ADDRESS``, and runs ``RAY_JOB_CMD`` (the v2ecoli ensemble) on the
head — no Nextflow. This service submits those MNP jobs.

Data flow (no shared filesystem):
  - ParCa runs first as its own 1-node MNP job; its cache is captured to a
    deterministic S3 URI (``RAY_OUT_S3``).
  - The simulation MNP job ``dependsOn`` the ParCa job (Batch gates it until
    ParCa SUCCEEDED), stages that cache (``RAY_STAGE_S3``), runs the ensemble,
    and captures the zarr/summary outputs to S3 (``RAY_OUT_S3``).

The Ray image (``vecoli:<ray_image_tag>``) is prebuilt by sms-cdk
``scripts/build-ray-image.sh``; ``submit_build_image_job`` is a no-op placeholder.
"""

import logging
import random
import string
from typing import Any, override

import boto3

from sms_api.common.hpc.job_service import JobStatusInfo
from sms_api.common.hpc.local_task_service import LocalTaskService
from sms_api.common.models import JobBackend, JobId, JobStatus
from sms_api.common.simulator_defaults import DEFAULT_BRANCH, DEFAULT_REPO
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.github_repo import (
    fetch_config_template,
    fetch_latest_commit_hash,
    fetch_repo_discovery,
)
from sms_api.simulation.models import ParcaDataset, RepoDiscovery, Simulation, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationService

logger = logging.getLogger(__name__)

# Absolute paths inside the v2ecoli Ray image (WORKDIR=/app/v2ecoli). The
# entrypoint runs RAY_JOB_CMD on the head; v2ecoli reads the cache from
# CACHE_DIR and writes the ensemble outputs under OUT_DIR.
V2ECOLI_DIR = "/app/v2ecoli"
PARCA_CACHE_DIR = f"{V2ECOLI_DIR}/out/cache"
PARCA_SIMDATA_DIR = f"{V2ECOLI_DIR}/out/sim_data"
SIM_OUT_DIR = f"{V2ECOLI_DIR}/.pbg/runs/phase0-xarray"
# Where the head writes the entrypoint's metrics report (uploaded as report.json).
REPORT_PATH = "/tmp/report.json"  # noqa: S108


def _rand_suffix() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


class SimulationServiceRay(SimulationService):
    """Ray-on-Batch (MNP) implementation of SimulationService."""

    def __init__(self, local_task_service: LocalTaskService | None = None) -> None:
        self._local = local_task_service or LocalTaskService()

    def _batch(self) -> Any:
        return boto3.client("batch", region_name=get_settings().batch_region)

    def _cache_s3_uri(self, commit: str) -> str:
        """Deterministic S3 URI for a commit's ParCa cache.

        Both the ParCa job (writes here) and the simulation job (stages from
        here) derive the same URI, so the cache hand-off needs no runtime wiring.
        """
        settings = get_settings()
        return f"s3://{settings.s3_work_bucket}/ray-parca-cache/{commit}/"

    def _results_s3_uri(self, experiment_id: str) -> str:
        settings = get_settings()
        return f"s3://{settings.s3_work_bucket}/{settings.s3_output_prefix}/{experiment_id}/"

    def _submit_mnp(
        self,
        *,
        job_name: str,
        num_nodes: int,
        ray_job_cmd: str,
        out_s3: str,
        out_dir: str,
        stage_s3: str | None = None,
        stage_dir: str | None = None,
        depends_on: list[str] | None = None,
    ) -> str:
        """Submit a Ray MNP job via boto3, mirroring sms-cdk scripts/ray_batch_submit.sh.

        Env targeting matters: the entrypoint runs ``stage_inputs`` and the periodic
        output sync on EVERY node, so the staging/output/log knobs must reach all
        nodes — the workers need the ParCa cache to run seeds and must ship their own
        zarr to S3. Only ``RAY_JOB_CMD`` (the driver) and ``RAY_REPORT_PATH`` are
        head-only. So the shared env goes on node 0 (``0:0``) and, when there are
        workers, also on the worker range (``1:``). Returns the AWS Batch job id.
        """
        settings = get_settings()
        # Per-node knobs every node acts on (stage cache in, sync results out, ship logs).
        shared_env: list[dict[str, str]] = [
            {"name": "RAY_OUT_DIR", "value": out_dir},
            {"name": "RAY_OUT_S3", "value": out_s3},
        ]
        if stage_s3 and stage_dir:
            shared_env.append({"name": "RAY_STAGE_S3", "value": stage_s3})
            shared_env.append({"name": "RAY_STAGE_DIR", "value": stage_dir})
        if settings.ray_log_s3_prefix:
            shared_env.append({"name": "RAY_LOG_S3_PREFIX", "value": settings.ray_log_s3_prefix})

        # The head additionally runs the workload (RAY_JOB_CMD) and writes the report.
        head_env: list[dict[str, str]] = [
            {"name": "RAY_JOB_CMD", "value": ray_job_cmd},
            {"name": "RAY_REPORT_PATH", "value": REPORT_PATH},
            *shared_env,
        ]

        node_property_overrides: list[dict[str, Any]] = [
            {"targetNodes": "0:0", "containerOverrides": {"environment": head_env}},
        ]
        if num_nodes > 1:
            # `1:` targets every worker node (a `1:` range is invalid for a 1-node job).
            node_property_overrides.append(
                {"targetNodes": "1:", "containerOverrides": {"environment": list(shared_env)}}
            )

        node_overrides: dict[str, Any] = {
            "numNodes": num_nodes,
            "nodePropertyOverrides": node_property_overrides,
        }
        kwargs: dict[str, Any] = {
            "jobName": job_name,
            "jobQueue": settings.ray_mnp_queue,
            "jobDefinition": settings.ray_mnp_job_definition,
            "nodeOverrides": node_overrides,
        }
        if depends_on:
            kwargs["dependsOn"] = [{"jobId": jid, "type": "SEQUENTIAL"} for jid in depends_on]

        response = self._batch().submit_job(**kwargs)
        batch_job_id = str(response["jobId"])
        logger.info(
            "Submitted Ray MNP job %s (id=%s, nodes=%d) to %s",
            job_name,
            batch_job_id,
            num_nodes,
            settings.ray_mnp_queue,
        )
        return batch_job_id

    def _parca_command(self) -> str:
        settings = get_settings()
        return (
            f"v2ecoli-parca --mode {settings.ray_parca_mode} --cpus {settings.ray_parca_cpus}"
            f" -o {PARCA_SIMDATA_DIR} --cache-dir {PARCA_CACHE_DIR}"
        )

    def _sim_command(self, n_seeds: int, n_steps: int, chunk: int) -> str:
        return (
            f"cd {V2ECOLI_DIR} && python scripts/run_phase0_xarray_ensemble.py"
            f" --n-seeds {n_seeds} --n-steps {n_steps} --chunk {chunk} --parallel ray"
        )

    @override
    async def get_latest_commit_hash(
        self,
        git_repo_url: str = DEFAULT_REPO,
        git_branch: str = DEFAULT_BRANCH,
    ) -> str:
        return await fetch_latest_commit_hash(git_repo_url, git_branch, get_settings().github_token)

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> JobId:
        """No-op placeholder: the Ray image is prebuilt by sms-cdk build-ray-image.sh.

        Returns a LOCAL task that completes immediately so build-status checks pass.
        """
        commit = simulator_version.git_commit_hash
        tag = get_settings().ray_image_tag
        logger.info(
            "Ray backend uses the prebuilt image vecoli:%s — skipping build for commit %s "
            "(rebuild via sms-cdk scripts/build-ray-image.sh if needed)",
            tag,
            commit,
        )
        return self._local.submit(self._image_prebuilt(commit, tag), name=f"ray-build-{commit}")

    async def _image_prebuilt(self, commit: str, tag: str) -> None:
        return None

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> JobId:
        """Submit ParCa as a 1-node Ray MNP job, capturing the cache to S3."""
        simulator_version = parca_dataset.parca_dataset_request.simulator_version
        commit = simulator_version.git_commit_hash
        job_id = self._submit_mnp(
            job_name=f"ray-parca-{commit}-{_rand_suffix()}",
            num_nodes=1,
            ray_job_cmd=self._parca_command(),
            out_s3=self._cache_s3_uri(commit),
            out_dir=PARCA_CACHE_DIR,
        )
        return JobId.ray(job_id)

    @override
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: Simulation, database_service: DatabaseService, correlation_id: str
    ) -> JobId:
        """Submit ParCa (1 node) + the simulation ensemble (N nodes), gated by a Batch dependency.

        The tracked job id is the *simulation* job. Batch will not start it until
        the ParCa job SUCCEEDED, so the cache is in S3 before the sim stages it.
        """
        if database_service is None:
            raise RuntimeError("DatabaseService is not available. Cannot submit Ray simulation job.")

        parca_dataset = await database_service.get_parca_dataset(parca_dataset_id=ecoli_simulation.parca_dataset_id)
        if parca_dataset is None:
            raise ValueError(f"ParcaDataset with ID {ecoli_simulation.parca_dataset_id} not found.")
        simulator = await database_service.get_simulator(simulator_id=ecoli_simulation.simulator_id)
        if simulator is None:
            raise ValueError(f"Simulator {ecoli_simulation.simulator_id} not found")

        settings = get_settings()
        commit = simulator.git_commit_hash
        experiment_id = ecoli_simulation.config.experiment_id
        cache_s3 = self._cache_s3_uri(commit)

        n_seeds = ecoli_simulation.num_seeds or getattr(ecoli_simulation.config, "n_init_sims", None) or 1
        n_steps = getattr(ecoli_simulation.config, "ray_n_steps", None) or settings.ray_n_steps
        chunk = getattr(ecoli_simulation.config, "ray_chunk", None) or settings.ray_chunk

        # 1. ParCa job (1 node) → cache to S3.
        parca_job_id = self._submit_mnp(
            job_name=f"ray-parca-{commit}-{_rand_suffix()}",
            num_nodes=1,
            ray_job_cmd=self._parca_command(),
            out_s3=cache_s3,
            out_dir=PARCA_CACHE_DIR,
        )

        # 2. Simulation ensemble (N nodes), gated on ParCa, staging the cache.
        sim_job_id = self._submit_mnp(
            job_name=f"ray-sim-{experiment_id}-{_rand_suffix()}"[:128],
            num_nodes=settings.ray_num_nodes,
            ray_job_cmd=self._sim_command(int(n_seeds), int(n_steps), int(chunk)),
            out_s3=self._results_s3_uri(experiment_id),
            out_dir=SIM_OUT_DIR,
            stage_s3=cache_s3,
            stage_dir=PARCA_CACHE_DIR,
            depends_on=[parca_job_id],
        )
        logger.info(
            "Ray simulation %s: parca job %s -> sim job %s (%d nodes)",
            experiment_id,
            parca_job_id,
            sim_job_id,
            settings.ray_num_nodes,
        )
        return JobId.ray(sim_job_id)

    @override
    async def read_config_template(
        self,
        simulator_version: SimulatorVersion,
        config_filename: str,
        allow_default_fallback: bool = False,
    ) -> str:
        return await fetch_config_template(
            simulator_version, config_filename, get_settings().github_token, allow_default_fallback
        )

    @override
    async def discover_repo_contents(self, simulator_version: SimulatorVersion) -> RepoDiscovery:
        return await fetch_repo_discovery(simulator_version, get_settings().github_token)

    @override
    async def get_job_status(self, job_id: JobId) -> JobStatusInfo | None:
        """Status — LOCAL (prebuilt-image placeholder) or AWS Batch describe_jobs."""
        if job_id.backend == JobBackend.LOCAL:
            return self._local.get_status(job_id.value)

        response = self._batch().describe_jobs(jobs=[job_id.value])
        jobs = response.get("jobs", [])
        if not jobs:
            logger.warning("No Batch job found with id %s", job_id.value)
            return None
        job = jobs[0]
        status = JobStatus.from_batch_state(job.get("status", ""))
        started = job.get("startedAt")
        stopped = job.get("stoppedAt")
        return JobStatusInfo(
            job_id=job_id,
            status=status,
            start_time=str(started) if started else None,
            end_time=str(stopped) if stopped else None,
            exit_code=None,
            error_message=job.get("statusReason") if status == JobStatus.FAILED else None,
        )

    @override
    async def cancel_job(self, job_id: JobId) -> None:
        """Cancel — LOCAL task or AWS Batch terminate_job (also kills child MNP nodes)."""
        if job_id.backend == JobBackend.LOCAL:
            self._local.cancel(job_id.value)
            logger.info("Cancelled local task %s", job_id.value)
            return
        self._batch().terminate_job(jobId=job_id.value, reason="cancelled via sms-api")
        logger.info("Terminated Ray Batch job %s", job_id.value)

    @override
    async def close(self) -> None:
        pass
