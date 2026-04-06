"""Kubernetes + AWS Batch implementation of SimulationService.

Two-phase execution model:
  Phase 1 (build): DinD Batch jobs build Docker images (ARM64 task + AMD64 submit)
  Phase 2 (workflow): K8s Job running Nextflow head, which submits tasks to AWS Batch
"""

import json
import logging
import re

import boto3
import httpx
from kubernetes import client as k8s_client
from typing_extensions import override

from sms_api.common.hpc.job_service import JobStatusInfo
from sms_api.common.hpc.k8s_job_service import K8sJobService
from sms_api.common.hpc.local_task_service import LocalTaskService
from sms_api.common.models import JobBackend, JobId
from sms_api.common.simulator_defaults import DEFAULT_BRANCH, DEFAULT_REPO
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import ParcaDataset, Simulation, Simulator, SimulatorVersion
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
        """Build Docker images via DinD Batch jobs (ARM64 task + AMD64 submit).

        Submits two parallel Batch jobs:
        - ARM64 queue: builds vecoli:{commit} (task image for Batch Graviton)
        - AMD64 queue: builds vecoli:{commit}-submit (submit image for EKS K8s Job)

        Returns immediately with a LOCAL JobId. The _run_build method polls
        both Batch jobs for completion.
        """
        commit = simulator_version.git_commit_hash
        return self._local.submit(
            self._run_build(simulator_version),
            name=f"build-{commit}",
        )

    def _build_command(self, simulator_version: Simulator, image_tag: str, submit_image: bool = False) -> list[str]:
        """Generate the DinD build command for a Batch job.

        Args:
            simulator_version: Simulator with commit, branch, repo URL
            image_tag: ECR image tag to build and push
            submit_image: If True, also build the submit image (base + Java + Nextflow)
        """
        settings = get_settings()
        commit = simulator_version.git_commit_hash
        branch = simulator_version.git_branch

        # Convert HTTPS GitHub URL to SSH for deploy key auth
        repo_url = simulator_version.git_repo_url
        https_match = re.match(r"https://github\.com/(.+)", repo_url)
        if https_match:
            ssh_url = f"git@github.com:{https_match.group(1)}"
            if not ssh_url.endswith(".git"):
                ssh_url += ".git"
        else:
            ssh_url = repo_url

        base_script = f"""\
set -ex

# Start Docker daemon
dockerd &
for i in $(seq 1 30); do docker info >/dev/null 2>&1 && break || sleep 1; done

# Get GitHub SSH key from Secrets Manager
mkdir -p ~/.ssh
aws secretsmanager get-secret-value \
    --secret-id {settings.build_git_secret_arn} \
    --query SecretString --output text > ~/.ssh/id_ed25519
chmod 600 ~/.ssh/id_ed25519
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null

# Clone repo
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    git clone --depth 1 --branch {branch} --single-branch {ssh_url} /build/vEcoli
cd /build/vEcoli
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    git fetch --depth 1 origin {commit}
git checkout {commit}

# ECR login
aws ecr get-login-password --region $AWS_DEFAULT_REGION | \
    docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push
bash runscripts/container/build-and-push-ecr.sh \
    -i {image_tag} -r {settings.ecr_repository} -R {settings.batch_region}
"""

        if submit_image:
            base_script += f"""
# Build submit image (base + Java + Nextflow) on top
BASE_URI=$ECR_REGISTRY/{settings.ecr_repository}:{image_tag}

cat > /tmp/Dockerfile-submit <<'DOCKERFILE'
ARG BASE_IMAGE
FROM ${{BASE_IMAGE}}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless \\
    && apt-get clean && rm -rf /var/lib/apt/lists/*
ARG NEXTFLOW_VERSION=25.10.2
RUN curl -fsSL "https://github.com/nextflow-io/nextflow/releases/download/v${{NEXTFLOW_VERSION}}/nextflow" \\
    -o /usr/local/bin/nextflow && chmod +x /usr/local/bin/nextflow
WORKDIR /vEcoli
DOCKERFILE

docker build -t "$ECR_REGISTRY/{settings.ecr_repository}:{commit}-submit" \
    --build-arg BASE_IMAGE="$BASE_URI" \
    -f /tmp/Dockerfile-submit /tmp
docker push "$ECR_REGISTRY/{settings.ecr_repository}:{commit}-submit"
echo "Submit image pushed: $ECR_REGISTRY/{settings.ecr_repository}:{commit}-submit"
"""

        return ["sh", "-c", base_script]

    async def _submit_batch_build(
        self, job_name: str, queue: str, command: list[str], commit: str
    ) -> str:
        """Submit a DinD build job to AWS Batch. Returns the Batch job ID."""
        settings = get_settings()
        batch = boto3.client("batch", region_name=settings.batch_region)
        response = batch.submit_job(
            jobName=job_name,
            jobQueue=queue,
            jobDefinition=settings.build_job_definition,
            containerOverrides={
                "command": command,
                "environment": [
                    {"name": "IMAGE_TAG", "value": commit},
                ],
            },
        )
        batch_job_id = response["jobId"]
        logger.info(f"Submitted Batch build job {job_name} (id={batch_job_id}) to queue {queue}")
        return batch_job_id

    async def _poll_batch_jobs(self, job_ids: list[str]) -> None:
        """Poll Batch jobs until all complete. Raises on failure."""
        import asyncio

        settings = get_settings()
        batch = boto3.client("batch", region_name=settings.batch_region)

        while True:
            response = batch.describe_jobs(jobs=job_ids)
            statuses = {j["jobId"]: j["status"] for j in response["jobs"]}

            failed = [jid for jid, s in statuses.items() if s == "FAILED"]
            if failed:
                # Get failure reason
                reasons = []
                for job in response["jobs"]:
                    if job["jobId"] in failed:
                        reason = job.get("statusReason", "unknown")
                        reasons.append(f"{job['jobName']}: {reason}")
                raise RuntimeError(f"Batch build job(s) failed: {'; '.join(reasons)}")

            if all(s == "SUCCEEDED" for s in statuses.values()):
                logger.info(f"All {len(job_ids)} Batch build jobs completed successfully")
                return

            await asyncio.sleep(15)

    async def _run_build(self, simulator_version: SimulatorVersion) -> None:
        """Build Docker images via parallel DinD Batch jobs.

        Submits two Batch jobs in parallel:
        - ARM64: builds vecoli:{commit} (task image for Graviton Batch compute)
        - AMD64: builds vecoli:{commit}-submit (submit image for AMD64 EKS)

        Polls both jobs until completion.
        """
        settings = get_settings()
        commit = simulator_version.git_commit_hash

        # ARM64: task image only
        arm64_cmd = self._build_command(simulator_version, image_tag=commit)
        arm64_job_id = await self._submit_batch_build(
            job_name=f"build-arm64-{commit}",
            queue=settings.build_arm64_queue,
            command=arm64_cmd,
            commit=commit,
        )

        # AMD64: base image + submit image
        amd64_cmd = self._build_command(simulator_version, image_tag=commit, submit_image=True)
        amd64_job_id = await self._submit_batch_build(
            job_name=f"build-amd64-{commit}",
            queue=settings.build_amd64_queue,
            command=amd64_cmd,
            commit=commit,
        )

        # Poll both until done
        await self._poll_batch_jobs([arm64_job_id, amd64_job_id])
        logger.info(f"Multi-arch build complete for {settings.ecr_repository}:{commit}")

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
        # K8s names must be RFC 1123: lowercase alphanumeric, '-' or '.'
        safe_id = experiment_id.replace("_", "-").lower()
        job_name = f"nf-{safe_id}"[:63]

        # Build the workflow config from the simulation record
        # (AWS overrides already applied by handler before DB insert)
        config_data = ecoli_simulation.config.model_dump()
        config_json = json.dumps(config_data)

        # Build full ECR URI for the submit image (vecoli + Java + Nextflow)
        simulator = await database_service.get_simulator(simulator_id=ecoli_simulation.simulator_id)
        if simulator is None:
            raise ValueError(f"Simulator {ecoli_simulation.simulator_id} not found")
        submit_image = (
            f"{settings.ecr_account_id}.dkr.ecr.{settings.batch_region}.amazonaws.com"
            f"/{settings.ecr_repository}:{simulator.git_commit_hash}-submit"
        )

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

        # Build the container command:
        # 1. Inject GovCloud S3 endpoint into config.template (before workflow.py reads it)
        # 2. Run workflow.py in full mode (generates Nextflow files + runs Nextflow)
        # 3. Upload .nextflow.log to S3 on completion (success or failure)
        s3_endpoint = f"https://s3.{settings.batch_region}.amazonaws.com"
        s3_log_dir = f"s3://{settings.s3_work_bucket}/{settings.s3_work_prefix}/{experiment_id}/logs"
        command = (
            f'sed -i "/region = params.aws_region/a\\            client {{ endpoint = \\"{s3_endpoint}\\" }}"'
            " runscripts/nextflow/config.template"
            " && python runscripts/workflow.py --config /config/workflow.json"
            f" ; NF_EXIT=$? ; aws s3 cp .nextflow.log {s3_log_dir}/.nextflow.log 2>/dev/null || true"
            " ; exit $NF_EXIT"
        )

        # Single-container K8s Job using vecoli-submit image (vEcoli + Java + Nextflow)
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
                                name="workflow",
                                image=submit_image,
                                command=["/bin/bash", "-c", command],
                                env=[
                                    k8s_client.V1EnvVar(name="AWS_DEFAULT_REGION", value=settings.batch_region),
                                    k8s_client.V1EnvVar(name="AWS_REGION", value=settings.batch_region),
                                    k8s_client.V1EnvVar(name="AWS_STS_REGIONAL_ENDPOINTS", value="regional"),
                                    k8s_client.V1EnvVar(name="USER", value="sms-api"),
                                ],
                                volume_mounts=[
                                    k8s_client.V1VolumeMount(name="config", mount_path="/config"),
                                ],
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={"cpu": "500m", "memory": "1Gi"},
                                    limits={"cpu": "1", "memory": "2Gi"},
                                ),
                            ),
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
