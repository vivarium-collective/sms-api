import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.models import EcoliSimulationRequest

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SimulationService(ABC):
    @abstractmethod
    async def submit_parca_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        pass

    @abstractmethod
    async def submit_sim_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        pass

    @abstractmethod
    async def get_slurm_job_status(self, slurm_job_id: str) -> SlurmJob | None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class SimulationServiceSlurm(SimulationService):
    @override
    async def submit_parca_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )
        slurm_service = SlurmService(ssh_service=ssh_service)

        # create Parca job submission script
        parca_submission_script = """
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            local_sbatch_file_path = tmpdir_path / "parca_submission.sbatch"
            remote_sbatch_file_path = Path("parca_files") / "parca_submission.sbatch"

            # write the sbatch file
            with open(local_sbatch_file_path, "w") as sbatch_file:
                sbatch_file.write(parca_submission_script)

            # submit the job to Slurm
            slurm_job_id = await slurm_service.submit_job(
                local_sbatch_file=local_sbatch_file_path, remote_sbatch_file=remote_sbatch_file_path
            )

            return slurm_job_id

    @override
    async def submit_sim_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        return -1

    @override
    async def get_slurm_job_status(self, slurm_job_id: str) -> SlurmJob | None:
        return None

    @override
    async def close(self) -> None:
        pass
