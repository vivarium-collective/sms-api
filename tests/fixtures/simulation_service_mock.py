import logging

from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.simulation.models import EcoliSimulation, EcoliSimulationRequest
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
    async def submit_parca_job(self, simulation_run_id: EcoliSimulationRequest) -> SlurmJob:
        pass

    @override
    async def submit_sim_job(self, simulation_run_id: EcoliSimulationRequest) -> SlurmJob:
        pass

    @override
    async def get_slurm_job_status(self, slurm_job_id: str) -> SlurmJob:
        pass

    @override
    async def close(self) -> None:
        pass
