import logging
from typing import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    EcoliSimulation,
    ParcaDataset,
    ParcaDatasetRequest,
    SimulationConfig,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationService


class ConcreteSimulationService(SimulationService):
    @override
    async def submit_experiment_job(
        self, config: SimulationConfig, simulation_name: str, simulator_hash: str, logger: logging.Logger
    ) -> tuple[str, int]:
        raise NotImplementedError()

    @override
    async def get_latest_commit_hash(
        self,
        git_repo_url: str = "https://github.com/CovertLab/vEcoli",
        git_branch: str = "master",
    ) -> str:
        raise NotImplementedError()

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        raise NotImplementedError()

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> int:
        raise NotImplementedError()

    @override
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: EcoliSimulation, database_service: DatabaseService, correlation_id: str
    ) -> int:
        raise NotImplementedError

    @override
    async def get_slurm_job_status(self, slurmjobid: int) -> SlurmJob | None:
        raise NotImplementedError

    @override
    async def close(self) -> None:
        raise NotImplementedError


class SimulationServiceMockCloneAndBuild(ConcreteSimulationService):
    submit_build_args: tuple[SimulatorVersion] = (
        SimulatorVersion(database_id=0, git_branch="", git_repo_url="", git_commit_hash=""),
    )
    expected_build_slurm_job_id: int = -1

    def __init__(self, expected_build_slurm_job_id: int) -> None:
        self.expected_build_slurm_job_id = expected_build_slurm_job_id

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        self.submit_build_args = (simulator_version,)
        return self.expected_build_slurm_job_id


class SimulationServiceMockParca(ConcreteSimulationService):
    submit_parca_args: tuple[ParcaDataset] = (
        ParcaDataset(
            database_id=0,
            parca_dataset_request=ParcaDatasetRequest(
                simulator_version=SimulatorVersion(database_id=0, git_branch="", git_repo_url="", git_commit_hash=""),
                parca_config={},
            ),
        ),
    )
    expected_slurmjobid: int

    def __init__(self, expected_slurmjobid: int) -> None:
        self.expected_slurmjobid = expected_slurmjobid

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> int:
        return self.expected_slurmjobid
