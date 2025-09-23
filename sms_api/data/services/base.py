import abc
import tempfile
from pathlib import Path
from typing import Any

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import Settings
from sms_api.simulation.hpc_utils import get_slurmjob_name, get_slurm_submit_file


class DataService(abc.ABC):
    def __init__(self, env: Settings):
        self.env = env

    @abc.abstractmethod
    def _generate_slurm_script(
            self,
            slurm_log_file: Path,
            slurm_job_name: str,
            current_simulator_hash: str,
            *request_args: Any
    ) -> str:
        pass

    def _get_slurmjob_name(self, experiment_id: str, simulator_hash: str) -> str:
        return get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)

    async def dispatch(
        self,
        experiment_id: str,
        current_simulator_hash: str,
        *request_args: Any
    ) -> int:
        ssh_service = get_ssh_service(self.env)
        slurm_service = SlurmService(ssh_service=ssh_service)

        slurm_job_name = self._get_slurmjob_name(experiment_id=experiment_id, simulator_hash=current_simulator_hash)
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
        base_path = Path(self.env.slurm_base_path)
        slurm_log_file = base_path / f"prod/htclogs/{experiment_id}.out"

        script_content = self._generate_slurm_script(
            slurm_log_file=slurm_log_file,
            slurm_job_name=slurm_job_name,
            current_simulator_hash=current_simulator_hash,
            *request_args
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                f.write(script_content)

            base_path = Path(self.env.slurm_base_path)
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid
