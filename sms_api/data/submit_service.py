import abc
import tempfile
from pathlib import Path

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import Settings, get_settings
from sms_api.simulation.hpc_utils import get_slurm_submit_file


class SubmitService(abc.ABC):
    @abc.abstractmethod
    def slurm_script(self, slurm_job_name: str, slurm_log_file: Path, env: Settings) -> str:
        pass

    @abc.abstractmethod
    async def submit_job(self) -> int:
        pass

    async def submit_slurm_script(
        self,
        script_content: str,
        slurm_job_name: str,
        env: Settings | None = None,
        ssh: SSHService | None = None,
        logfile: Path | None = None,
    ) -> int:
        settings = env or get_settings()
        ssh_service = ssh or SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
            known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
        )
        slurm_service = SlurmService(ssh_service=ssh_service)

        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                f.write(script_content)

            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid
