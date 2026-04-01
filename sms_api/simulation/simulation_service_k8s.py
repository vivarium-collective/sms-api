"""Kubernetes + AWS Batch implementation of SimulationService.

Two-phase execution model:
  Phase 1 (build): SSH to ARM64 EC2 submit node for Docker image build + ECR push
  Phase 2 (workflow): K8s Job running Nextflow head, which submits tasks to AWS Batch
"""

import json
import logging
import re

import httpx
from kubernetes import client as k8s_client
from typing_extensions import override

from sms_api.common.hpc.job_service import JobStatusInfo
from sms_api.common.hpc.k8s_job_service import K8sJobService
from sms_api.common.hpc.local_task_service import LocalTaskService
from sms_api.common.models import JobBackend, JobId
from sms_api.common.simulator_defaults import DEFAULT_BRANCH, DEFAULT_REPO
from sms_api.config import get_settings
from sms_api.dependencies import get_ssh_session_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import ParcaDataset, Simulation, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationService

logger = logging.getLogger(__name__)


def _github_api_url(repo_url: str) -> str:
    """Convert a GitHub HTTPS URL to the API equivalent.

    https://github.com/org/repo -> https://api.github.com/repos/org/repo
    """
    api_url = repo_url.replace("https://github.com/", "https://api.github.com/repos/")
    if api_url.endswith(".git"):
        api_url = api_url[:-4]
    return api_url


def _github_headers(token: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


class SimulationServiceK8s(SimulationService):
    """K8s Job + AWS Batch implementation of SimulationService.

    - Build phase: SSH to ARM64 EC2 submit node for Docker build + ECR push
    - Workflow phase: Creates K8s Job running Nextflow, which submits tasks to Batch
    - Config reads: GitHub API (no SSH needed)
    - Status/cancel: K8s Job API
    """

    def __init__(self, k8s_job_service: K8sJobService, local_task_service: LocalTaskService | None = None) -> None:
        self._k8s = k8s_job_service
        self._local = local_task_service or LocalTaskService()

    @override
    async def get_latest_commit_hash(
        self,
        git_repo_url: str = DEFAULT_REPO,
        git_branch: str = DEFAULT_BRANCH,
    ) -> str:
        """Get the latest commit hash from GitHub API (no SSH needed)."""
        settings = get_settings()
        api_url = f"{_github_api_url(git_repo_url)}/commits/{git_branch}"
        headers = _github_headers(settings.github_token)
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return str(data["sha"])[:7]

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> JobId:
        """Build a Docker image on the EC2 submit node via SSH (async).

        Spawns the build as a background task and returns immediately with a
        LOCAL JobId. The build clones the vEcoli repo at the specified commit,
        then uses vEcoli's build-and-push-ecr.sh to build and push to ECR.

        The image architecture matches the submit node (ARM64 for Graviton
        Batch compute, or AMD64 if configured differently). No cross-compilation.
        """
        commit = simulator_version.git_commit_hash
        return self._local.submit(
            self._run_build(simulator_version),
            name=f"build-{commit}",
        )

    async def _run_build(self, simulator_version: SimulatorVersion) -> None:
        """Execute the Docker build + ECR push on the submit node via SSH."""
        settings = get_settings()
        commit = simulator_version.git_commit_hash
        branch = simulator_version.git_branch
        repo_url = simulator_version.git_repo_url

        # Inject GitHub PAT for private repo cloning
        auth_repo_url = repo_url
        if settings.github_username and settings.github_token:
            match = re.match(r"https://github\.com/(.+)", repo_url)
            if match:
                auth_repo_url = (
                    f"https://{settings.github_username}:{settings.github_token}@github.com/{match.group(1)}"
                )

        # Clone repo, build image, push to ECR, clean up
        # build-and-push-ecr.sh handles ECR auth, repo creation, build, push, and tagging
        build_dir = f"vEcoli-build-{commit}"
        build_script = f"""\
set -e
cd /tmp
if [ -d "{build_dir}" ]; then rm -rf "{build_dir}"; fi
git clone --branch {branch} --single-branch {auth_repo_url} {build_dir}
cd {build_dir}
bash runscripts/container/build-and-push-ecr.sh \
    -i {commit} \
    -r {settings.ecr_repository} \
    -R {settings.batch_region}
cd /tmp && rm -rf {build_dir}
"""

        async with get_ssh_session_service().session() as ssh:
            return_code, _stdout, stderr = await ssh.run_command(build_script)
            if return_code != 0:
                raise RuntimeError(f"Docker build failed on submit node: {stderr[:500]}")

        logger.info(f"Built and pushed image {settings.ecr_repository}:{commit}")

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> JobId:
        """Submit parca as a K8s Job.

        Parca runs inside the Nextflow workflow (not as a separate step) when
        using the K8s/Batch backend. This creates a placeholder entry.
        For the K8s path, parca execution is handled within the Nextflow workflow
        based on the sim_data_path config (null = run parca, path = use cached).
        """
        # Parca runs as part of the Nextflow workflow, not separately
        # Return a placeholder ID
        parca_id = parca_dataset.database_id
        return JobId.k8s(f"parca-placeholder-{parca_id}")

    @override
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: Simulation, database_service: DatabaseService, correlation_id: str
    ) -> JobId:
        """Create a K8s Job that runs Nextflow with the awsbatch executor."""
        settings = get_settings()

        experiment_id = ecoli_simulation.config.experiment_id
        job_name = f"nf-{experiment_id}"[:63]  # K8s name max 63 chars

        # Get the simulator to determine the ECR image tag
        simulator = await database_service.get_simulator(simulator_id=ecoli_simulation.simulator_id)
        if simulator is None:
            raise ValueError(f"Simulator {ecoli_simulation.simulator_id} not found")

        ecr_account = settings.nextflow_container_image.split(".")[0] if settings.nextflow_container_image else ""
        ecr_region = settings.batch_region
        task_image = (
            f"{ecr_account}.dkr.ecr.{ecr_region}.amazonaws.com/{settings.ecr_repository}:{simulator.git_commit_hash}"
        )

        # Build the workflow config
        config_data = ecoli_simulation.config.model_dump()
        config_data["emitter_arg"] = {
            "out_uri": f"s3://{settings.s3_work_bucket}/{settings.s3_output_prefix}/{experiment_id}"
        }
        config_data["aws"] = {
            "build_image": False,
            "container_image": task_image,
            "region": settings.batch_region,
            "batch_queue": settings.batch_job_queue,
        }
        config_data["progress_bar"] = False
        config_json = json.dumps(config_data)

        # Create ConfigMap with workflow config
        configmap_name = f"{job_name}-config"
        configmap = k8s_client.V1ConfigMap(
            metadata=k8s_client.V1ObjectMeta(
                name=configmap_name,
                labels={"app": "sms-api", "experiment-id": experiment_id},
            ),
            data={"workflow.json": config_json},
        )
        self._k8s.create_configmap(configmap)

        # Create the K8s Job
        job = k8s_client.V1Job(
            metadata=k8s_client.V1ObjectMeta(
                name=job_name,
                labels={
                    "app": "sms-api",
                    "job-type": "simulation",
                    "experiment-id": experiment_id,
                },
            ),
            spec=k8s_client.V1JobSpec(
                backoff_limit=0,
                ttl_seconds_after_finished=86400,  # 24h for log access
                template=k8s_client.V1PodTemplateSpec(
                    spec=k8s_client.V1PodSpec(
                        service_account_name="batch-submit",
                        restart_policy="Never",
                        containers=[
                            k8s_client.V1Container(
                                name="nextflow",
                                image=settings.nextflow_container_image,
                                args=["--config", "/config/workflow.json"],
                                env=[
                                    k8s_client.V1EnvVar(
                                        name="NXF_WORK",
                                        value=f"s3://{settings.s3_work_bucket}/{settings.s3_work_prefix}/{experiment_id}",
                                    ),
                                    k8s_client.V1EnvVar(name="AWS_DEFAULT_REGION", value=settings.batch_region),
                                ],
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(name="config", mount_path="/config"),
                                ],
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={"cpu": "2", "memory": "4Gi"},
                                    limits={"cpu": "2", "memory": "4Gi"},
                                ),
                            )
                        ],
                        volumes=[
                            k8s_client.V1Volume(
                                name="config",
                                config_map=k8s_client.V1ConfigMapVolumeSource(name=configmap_name),
                            ),
                        ],
                    ),
                ),
            ),
        )
        self._k8s.create_job(job)
        logger.info(f"Created K8s Job {job_name} for experiment {experiment_id}")
        return JobId.k8s(job_name)

    @override
    async def read_config_template(self, simulator_version: SimulatorVersion, config_filename: str) -> str:
        """Read a vEcoli config template from the GitHub repo via the Contents API."""
        settings = get_settings()
        base = _github_api_url(simulator_version.git_repo_url)
        api_url = f"{base}/contents/configs/{config_filename}?ref={simulator_version.git_commit_hash}"
        headers: dict[str, str] = {"Accept": "application/vnd.github.v3.raw"}
        if settings.github_token:
            headers["Authorization"] = f"token {settings.github_token}"
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.text

    @override
    async def get_job_status(self, job_id: JobId) -> JobStatusInfo | None:
        """Get job status — dispatches to K8s or local task tracker."""
        if job_id.backend == JobBackend.LOCAL:
            return self._local.get_status(job_id.value)
        return self._k8s.get_job_status(job_id.value)

    @override
    async def cancel_job(self, job_id: JobId) -> None:
        """Cancel a job — dispatches to K8s or local task tracker."""
        if job_id.backend == JobBackend.LOCAL:
            self._local.cancel(job_id.value)
            logger.info(f"Cancelled local task {job_id.value}")
            return
        # K8s Job: delete with foreground propagation, sends SIGTERM to Nextflow head
        self._k8s.delete_job(job_id.value)
        configmap_name = f"{job_id.value}-config"
        self._k8s.delete_configmap(configmap_name)
        logger.info(f"Cancelled K8s Job {job_id.value}")

    @override
    async def close(self) -> None:
        pass
