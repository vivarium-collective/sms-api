import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, override

from sms_api.common.hpc.job_service import JobStatusInfo, JobStatusService
from sms_api.common.models import JobStatus
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    ParcaDataset,
    ParcaDatasetRequest,
    ParcaOptions,
    Simulation,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationService


class MockSSHSession:
    """Mock SSH session for tests that don't need real SSH."""

    async def run_command(self, command: str) -> tuple[int, str, str]:
        """Mock run_command that returns success."""
        return 0, "", ""


class MockSSHSessionService:
    """Mock SSH session service for tests that use mock simulation services."""

    @asynccontextmanager
    async def session(self, wait_closed: bool = True) -> AsyncIterator[MockSSHSession]:
        """Yield a mock SSH session."""
        yield MockSSHSession()


class ConcreteSimulationService(SimulationService):
    @override
    async def get_latest_commit_hash(
        self,
        git_repo_url: str = "https://github.com/vivarium-collective/vEcoli",
        git_branch: str = "api-support",
    ) -> str:
        raise NotImplementedError()

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> str:
        raise NotImplementedError()

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> str:
        raise NotImplementedError()

    @override
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: Simulation, database_service: DatabaseService, correlation_id: str
    ) -> str:
        raise NotImplementedError

    @override
    async def get_job_status(self, job_id: str) -> JobStatusInfo | None:
        raise NotImplementedError

    @override
    async def close(self) -> None:
        raise NotImplementedError


class SimulationServiceMockCloneAndBuild(ConcreteSimulationService):
    submit_build_args: tuple[Any, ...] = ()
    expected_build_slurm_job_id: int = -1

    def __init__(self, expected_build_slurm_job_id: int) -> None:
        self.expected_build_slurm_job_id = expected_build_slurm_job_id

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> str:
        self.submit_build_args = (simulator_version,)
        return str(self.expected_build_slurm_job_id)


class SimulationServiceMockParca(ConcreteSimulationService):
    submit_parca_args: tuple[ParcaDataset] = (
        ParcaDataset(
            database_id=0,
            parca_dataset_request=ParcaDatasetRequest(
                simulator_version=SimulatorVersion(database_id=0, git_branch="", git_repo_url="", git_commit_hash=""),
                parca_config=ParcaOptions(),
            ),
        ),
    )
    expected_slurmjobid: int

    def __init__(self, expected_slurmjobid: int) -> None:
        self.expected_slurmjobid = expected_slurmjobid

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> str:
        return str(self.expected_slurmjobid)


class MockAwsBatchService(JobStatusService):
    """Mock AWS Batch service that returns fake job IDs and configurable statuses.

    Tracks all submitted jobs and their arguments for assertion in tests.
    By default, get_job_statuses returns COMPLETED for any job ID.
    """

    def __init__(self, default_status: JobStatus = JobStatus.COMPLETED) -> None:
        self._default_status = default_status
        self.submitted_jobs: list[dict[str, Any]] = []

    async def submit_job(
        self,
        job_name: str,
        job_definition: str,
        job_queue: str,
        container_overrides: dict[str, Any] | None = None,
        parameters: dict[str, str] | None = None,
        tags: dict[str, str] | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        self.submitted_jobs.append({
            "job_id": job_id,
            "job_name": job_name,
            "job_definition": job_definition,
            "job_queue": job_queue,
            "container_overrides": container_overrides,
            "parameters": parameters,
            "tags": tags,
        })
        return job_id

    @override
    async def get_job_statuses(self, job_ids: list[str]) -> list[JobStatusInfo]:
        return [
            JobStatusInfo(
                job_id=jid,
                status=self._default_status,
                start_time="1711800000",
                end_time="1711803600",
                exit_code="0" if self._default_status == JobStatus.COMPLETED else "1",
            )
            for jid in job_ids
        ]
