import logging
from pathlib import Path

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.ssh.ssh_service import SSHSession
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.dependencies import get_ssh_session_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlurmService:
    verified_htc_dir: bool = False

    async def get_job_status_squeue(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        command = f'squeue -u $USER --noheader --format="{SlurmJob.get_squeue_format_string()}"'
        if job_ids is not None:
            job_ids_str = ",".join(map(str, job_ids)) if len(job_ids) > 1 else str(job_ids[0])
            command = command + f" -j {job_ids_str}"

        async with get_ssh_session_service().session() as ssh:
            return_code, stdout, stderr = await ssh.run_command(command=command)

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
            job_ids_str = ",".join(map(str, job_ids)) if len(job_ids) > 1 else str(job_ids[0])
            command = command + f" -j {job_ids_str}"

        async with get_ssh_session_service().session() as ssh:
            return_code, stdout, stderr = await ssh.run_command(command=command)

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

    async def submit_job(
        self, local_sbatch_file: Path, remote_sbatch_file: HPCFilePath, args: tuple[str, ...] | None = None
    ) -> int:
        async with get_ssh_session_service().session() as ssh:
            if not self.verified_htc_dir:
                await ssh.run_command("mkdir -p " + str(remote_sbatch_file.parent))
                self.verified_htc_dir = True
            await ssh.scp_upload(local_file=local_sbatch_file, remote_path=remote_sbatch_file)
            command = f"sbatch --parsable {remote_sbatch_file}"
            if args:
                for arg in args:
                    command += f" {arg}"
            return_code, stdout, stderr = await ssh.run_command(command=command)

        if return_code != 0:
            raise Exception(
                f"failed to get job status with command {command} return code {return_code} stderr {stderr[:100]}"
            )
        return int(stdout)


async def run_command_with_session(command: str) -> tuple[int, str, str]:
    """Helper function to run a single command using the SSHSessionService singleton."""
    async with get_ssh_session_service().session() as ssh:
        return await ssh.run_command(command)


async def run_command_with_ssh(ssh: SSHSession, command: str) -> tuple[int, str, str]:
    """Helper function to run a command with an existing SSHSession."""
    return await ssh.run_command(command)
