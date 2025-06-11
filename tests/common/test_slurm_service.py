import uuid
from pathlib import Path

import pytest

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.config import get_settings


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_query(slurm_service: SlurmService) -> None:
    all_jobs: list[SlurmJob] = await slurm_service.get_job_status()
    assert all_jobs is not None
    if len(all_jobs) > 0:
        assert isinstance(all_jobs[0], SlurmJob)
        one_job: list[SlurmJob] = await slurm_service.get_job_status(job_id=all_jobs[0].job_id)
        assert one_job is not None
        assert len(one_job) == 1
        assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_submit(slurm_service: SlurmService, slurm_template_hello: str) -> None:
    _all_jobs_before_submit: list[SlurmJob] = await slurm_service.get_job_status()
    # write slurm_template_hello to a temp file
    local_sbatch_file = Path(f"job_{uuid.uuid4().hex}.sbatch")
    with open(local_sbatch_file, "w") as f:
        f.write(slurm_template_hello)

    remote_sbatch_file = Path(local_sbatch_file.name)
    job_id: int = await slurm_service.submit_job(
        local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
    )

    submitted_job: list[SlurmJob] = await slurm_service.get_job_status(job_id=job_id)
    assert submitted_job is not None and len(submitted_job) == 1
    assert submitted_job[0].job_id == job_id
    assert submitted_job[0].name == "my_test_job"

    local_sbatch_file.unlink()
