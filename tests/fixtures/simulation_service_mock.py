import logging

from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.simulation.models import EcoliSimulation, EcoliSimulationRequest, ParcaDataset, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ObjectNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class SimulationServiceMock(SimulationService):
    sim_runs: dict[str, EcoliSimulation] = {}

    def __init__(self, sim_runs: dict[str, EcoliSimulation] | None = None) -> None:
        if sim_runs:
            self.sim_runs = sim_runs

    @override
    async def clone_repository_if_needed(
        self, git_commit_hash: str, repo_url: str = "https://github.com/CovertLab/vEcoli", branch: str = "master"
    ) -> None:
        pass

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        return 1  # Mock job ID

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> int:
        return 1  # Mock job ID

    @override
    async def submit_sim_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        return 1  # Mock job ID

    @override
    async def get_slurm_job_status(self, slurm_job_id: int) -> SlurmJob | None:
        return None

    @override
    async def close(self) -> None:
        pass
