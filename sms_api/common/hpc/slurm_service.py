import logging
from pathlib import Path

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.ssh.ssh_service import SSHService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlurmService:
    ssh_service: SSHService

    def __init__(self, ssh_service: SSHService):
        self.ssh_service = ssh_service

    async def get_job_status_squeue(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        command = f'squeue -u $USER --noheader --format="{SlurmJob.get_squeue_format_string()}"'
        if job_ids is not None:
            job_ids_str = ",".join(map(str, job_ids))
            command = command + f" -j {job_ids_str}"
        return_code, stdout, stderr = await self.ssh_service.run_command(command=command)
        if return_code != 0:
            raise Exception(
                f"failed to get job status with command {command} return code {return_code} stderr {stderr[:100]}"
            )
        slurm_jobs: list[SlurmJob] = []
        for line in stdout.splitlines():
            if not line.strip():
                continue
            slurm_jobs.append(SlurmJob.from_squeue_formatted_output(line.strip()))
        return slurm_jobs

    async def get_job_status_sacct(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        command = (
            f'sacct -u $USER --parsable --delimiter="|" --noheader --format="{SlurmJob.get_sacct_format_string()}"'
        )
        if job_ids is not None:
            job_ids_str = ",".join(map(str, job_ids))
            command = command + f" -j {job_ids_str}"
        return_code, stdout, stderr = await self.ssh_service.run_command(command=command)
        if return_code != 0:
            raise Exception(
                f"failed to get job status with command {command} return code {return_code} stderr {stderr[:100]}"
            )
        slurm_jobs: list[SlurmJob] = []
        for line in stdout.splitlines():
            if not line.strip():
                continue
            # skip lines which are .batch and ?? jobs
            if line.split("|")[0].endswith(".batch"):
                continue
            if line.split("|")[0].endswith(".extern"):
                continue
            slurm_jobs.append(SlurmJob.from_sacct_formatted_output(line.strip()))
        return slurm_jobs

    async def submit_job(self, local_sbatch_file: Path, remote_sbatch_file: Path) -> int:
        await self.ssh_service.scp_upload(local_file=local_sbatch_file, remote_path=remote_sbatch_file)
        command = f"sbatch --parsable {remote_sbatch_file}"
        return_code, stdout, stderr = await self.ssh_service.run_command(command=command)
        if return_code != 0:
            raise Exception(
                f"failed to get job status with command {command} return code {return_code} stderr {stderr[:100]}"
            )
        return int(stdout)
