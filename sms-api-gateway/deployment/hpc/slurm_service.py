import json
import logging
from pathlib import Path
from typing import Any

from biosim_server.common.hpc.models import SlurmJob
from biosim_server.common.ssh.ssh_service import SSHService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlurmService:
    ssh_service: SSHService

    def __init__(self, ssh_service: SSHService):
        self.ssh_service = ssh_service

    async def get_job_status(self, job_id: int | None = None) -> list[SlurmJob]:
        command = f'squeue --json'
        if job_id is not None:
             command = command + f' -j {job_id}'
        return_code, stdout, stderr = await self.ssh_service.run_command(command=command)
        if return_code != 0:
            raise Exception(f"failed to get job status with command {command} return code {return_code} stderr {stderr[:100]}")
        result_json_obj = json.loads(stdout)
        job_dicts: list[dict[str, Any]] = result_json_obj['jobs']
        return [SlurmJob.model_validate(job_dict) for job_dict in job_dicts]

    async def submit_job(self, local_sbatch_file: Path, remote_sbatch_file: Path) -> int:
        await self.ssh_service.scp_upload(local_file=local_sbatch_file, remote_path=remote_sbatch_file)
        command = f'sbatch --parsable {local_sbatch_file}'
        return_code, stdout, stderr = await self.ssh_service.run_command(command=command)
        if return_code != 0:
            raise Exception(f"failed to get job status with command {command} return code {return_code} stderr {stderr[:100]}")
        return int(stdout)

