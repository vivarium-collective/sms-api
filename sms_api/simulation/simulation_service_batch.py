import logging

import httpx
from typing_extensions import override

from sms_api.common.hpc.batch_service import AwsBatchService
from sms_api.common.hpc.job_service import JobStatusInfo
from sms_api.common.simulator_defaults import DEFAULT_BRANCH, DEFAULT_REPO
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import ParcaDataset, Simulation, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationService

logger = logging.getLogger(__name__)


class SimulationServiceBatch(SimulationService):
    """AWS Batch implementation of SimulationService."""

    def __init__(self, batch_service: AwsBatchService) -> None:
        self._batch_service = batch_service

    @override
    async def get_latest_commit_hash(
        self,
        git_repo_url: str = DEFAULT_REPO,
        git_branch: str = DEFAULT_BRANCH,
    ) -> str:
        """Get the latest commit hash from GitHub API (no SSH needed)."""
        settings = get_settings()
        # Convert git URL to API URL
        # https://github.com/org/repo -> https://api.github.com/repos/org/repo
        api_url = git_repo_url.replace("https://github.com/", "https://api.github.com/repos/")
        if api_url.endswith(".git"):
            api_url = api_url[:-4]
        api_url = f"{api_url}/commits/{git_branch}"

        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if settings.github_token:
            headers["Authorization"] = f"token {settings.github_token}"

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return str(data["sha"])[:7]

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> str:
        """Submit a Docker image build job to AWS Batch.

        TODO: Configure container commands for building the simulator Docker image.
        The Batch job definition should handle:
        - Cloning the vEcoli repository
        - Building the Docker image
        - Pushing to ECR
        """
        settings = get_settings()
        job_name = f"build-image-{simulator_version.git_commit_hash}"
        container_overrides = {
            "environment": [
                {"name": "GIT_REPO_URL", "value": simulator_version.git_repo_url},
                {"name": "GIT_BRANCH", "value": simulator_version.git_branch},
                {"name": "GIT_COMMIT_HASH", "value": simulator_version.git_commit_hash},
            ],
        }
        job_id = await self._batch_service.submit_job(
            job_name=job_name,
            job_definition=settings.batch_job_definition_build,
            job_queue=settings.batch_job_queue,
            container_overrides=container_overrides,
        )
        return job_id

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> str:
        """Submit a parca parameter calculator job to AWS Batch.

        TODO: Configure container commands for running parca.
        The Batch job definition should handle:
        - Running the parca parameter calculator
        - Uploading results to S3
        """
        settings = get_settings()
        simulator_version = parca_dataset.parca_dataset_request.simulator_version
        job_name = f"parca-{simulator_version.git_commit_hash}-{parca_dataset.database_id}"
        container_overrides = {
            "environment": [
                {"name": "GIT_COMMIT_HASH", "value": simulator_version.git_commit_hash},
                {"name": "PARCA_DATASET_ID", "value": str(parca_dataset.database_id)},
            ],
        }
        job_id = await self._batch_service.submit_job(
            job_name=job_name,
            job_definition=settings.batch_job_definition_parca,
            job_queue=settings.batch_job_queue,
            container_overrides=container_overrides,
        )
        return job_id

    @override
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: Simulation, database_service: DatabaseService, correlation_id: str
    ) -> str:
        """Submit a vEcoli simulation job to AWS Batch.

        TODO: Configure container commands for running the Nextflow workflow.
        The Batch job definition should handle:
        - Running the Nextflow-based simulation workflow
        - Writing outputs to S3
        """
        settings = get_settings()
        parca_dataset = await database_service.get_parca_dataset(parca_dataset_id=ecoli_simulation.parca_dataset_id)
        if parca_dataset is None:
            raise ValueError(f"ParcaDataset with ID {ecoli_simulation.parca_dataset_id} not found.")

        simulator_version = parca_dataset.parca_dataset_request.simulator_version
        job_name = f"sim-{simulator_version.git_commit_hash}-{ecoli_simulation.database_id}"
        container_overrides = {
            "environment": [
                {"name": "GIT_COMMIT_HASH", "value": simulator_version.git_commit_hash},
                {"name": "EXPERIMENT_ID", "value": ecoli_simulation.config.experiment_id},
                {"name": "CORRELATION_ID", "value": correlation_id},
                {"name": "SIMULATION_ID", "value": str(ecoli_simulation.database_id)},
            ],
        }
        job_id = await self._batch_service.submit_job(
            job_name=job_name,
            job_definition=settings.batch_job_definition_simulation,
            job_queue=settings.batch_job_queue,
            container_overrides=container_overrides,
        )
        return job_id

    @override
    async def read_config_template(self, simulator_version: SimulatorVersion, config_filename: str) -> str:
        """Read a vEcoli config template from the GitHub repo via the Contents API.

        Uses the GitHub API to fetch the file at:
            {repo}/contents/configs/{config_filename}?ref={commit_hash}
        """
        settings = get_settings()
        api_url = simulator_version.git_repo_url.replace("https://github.com/", "https://api.github.com/repos/")
        if api_url.endswith(".git"):
            api_url = api_url[:-4]
        api_url = f"{api_url}/contents/configs/{config_filename}?ref={simulator_version.git_commit_hash}"

        headers: dict[str, str] = {"Accept": "application/vnd.github.v3.raw"}
        if settings.github_token:
            headers["Authorization"] = f"token {settings.github_token}"

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.text

    @override
    async def get_job_status(self, job_id: str) -> JobStatusInfo | None:
        statuses = await self._batch_service.get_job_statuses([job_id])
        return statuses[0] if statuses else None

    @override
    async def close(self) -> None:
        pass
