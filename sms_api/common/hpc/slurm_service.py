import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import cast, override

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlurmService(ABC):
    @abstractmethod
    async def get_job_status_squeue(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        pass

    @abstractmethod
    async def get_job_status_sacct(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        pass

    async def get_job_status(self, slurmjobid: int) -> SlurmJob | None:
        job_ids: list[SlurmJob] = await self.get_job_status_squeue(job_ids=[slurmjobid])
        if len(job_ids) == 0:
            job_ids = await self.get_job_status_sacct(job_ids=[slurmjobid])
            if len(job_ids) == 0:
                logger.warning(f"No job found with ID {slurmjobid} in both squeue and sacct.")
                return None
        if len(job_ids) == 1:
            return job_ids[0]
        else:
            raise RuntimeError(f"Multiple jobs found with ID {slurmjobid}: {job_ids}")

    @abstractmethod
    async def submit_job(self, local_sbatch_file: Path, remote_sbatch_file: Path) -> int:
        pass


class SlurmServiceRemoteHPC(SlurmService):
    ssh_service: SSHService

    def __init__(self, ssh_service: SSHService):
        self.ssh_service = ssh_service

    @override
    async def get_job_status_squeue(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        squeue = "squeue"
        command = f'{squeue} -u $USER --noheader --format="{SlurmJob.get_squeue_format_string()}"'
        if job_ids is not None:
            job_ids_str = ",".join(map(str, job_ids)) if len(job_ids) > 1 else str(job_ids[0])
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

    @override
    async def get_job_status_sacct(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        sacct = "sacct"
        command = (
            f'{sacct} -u $USER --parsable --delimiter="|" --noheader --format="{SlurmJob.get_sacct_format_string()}"'
        )
        if job_ids is not None:
            job_ids_str = ",".join(map(str, job_ids)) if len(job_ids) > 1 else str(job_ids[0])
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

    @override
    async def submit_job(self, local_sbatch_file: Path, remote_sbatch_file: Path) -> int:
        await self.ssh_service.scp_upload(local_file=local_sbatch_file, remote_path=remote_sbatch_file)
        sbatch = "sbatch"
        command = f"{sbatch} --parsable {remote_sbatch_file}"
        return_code, stdout, stderr = await self.ssh_service.run_command(command=command)
        if return_code != 0:
            raise Exception(
                f"failed to get job status with command {command} return code {return_code} stderr {stderr[:100]}"
            )
        return int(stdout)


async def _async_run(command: list[str]) -> tuple[int, str, str]:
    # submit the command as a subprocess and capture the return code, stdout, and stderr
    proc = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return_code = cast(int, proc.returncode)
    return return_code, stderr.decode(), stdout.decode()


class SlurmServiceLocalHPC(SlurmService):
    @override
    async def get_job_status_squeue(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        squeue = get_settings().slurm_squeue_local_command
        command = f'{squeue} -u $USER --noheader --format="{SlurmJob.get_squeue_format_string()}"'
        if job_ids is not None:
            job_ids_str = ",".join(map(str, job_ids)) if len(job_ids) > 1 else str(job_ids[0])
            command = command + f" -j {job_ids_str}"

        return_code, stderr, stdout = await _async_run(command.split())

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

    @override
    async def get_job_status_sacct(self, job_ids: list[int] | None = None) -> list[SlurmJob]:
        sacct = get_settings().slurm_sacct_local_command
        command = (
            f'{sacct} -u $USER --parsable --delimiter="|" --noheader --format="{SlurmJob.get_sacct_format_string()}"'
        )
        if job_ids is not None:
            job_ids_str = ",".join(map(str, job_ids)) if len(job_ids) > 1 else str(job_ids[0])
            command = command + f" -j {job_ids_str}"
        return_code, stdout, stderr = await _async_run(command=command.split())
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

    @override
    async def submit_job(self, local_sbatch_file: Path, remote_sbatch_file: Path) -> int:
        # for SlurmServiceLocalHPC, both local_sbatch_file and remote_sbatch_file are local paths, so no scp is needed,
        # but we still want to copy to the remote_sbatch_file path for consistency
        if local_sbatch_file != remote_sbatch_file:
            remote_sbatch_file.parent.mkdir(parents=True, exist_ok=True)
            remote_sbatch_file.write_text(local_sbatch_file.read_text())

        sbatch = get_settings().slurm_sbatch_local_command
        command = f"{sbatch} --parsable {remote_sbatch_file}"
        return_code, stdout, stderr = await _async_run(command=command.split())
        if return_code != 0:
            raise Exception(
                f"failed to get job status with command {command} return code {return_code} stderr {stderr[:100]}"
            )
        return int(stdout)
