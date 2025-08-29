import tempfile
import uuid
from pathlib import Path

import pytest

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmServiceLocalHPC, SlurmServiceRemoteHPC
from sms_api.config import get_settings


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_query_squeue_remote(slurm_service_remote: SlurmServiceRemoteHPC) -> None:
    all_jobs: list[SlurmJob] = await slurm_service_remote.get_job_status_squeue()
    assert all_jobs is not None
    if len(all_jobs) > 0:
        assert isinstance(all_jobs[0], SlurmJob)
        one_job: list[SlurmJob] = await slurm_service_remote.get_job_status_squeue(job_ids=[all_jobs[0].job_id])
        assert one_job is not None
        assert len(one_job) == 1
        assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_query_squeue_local(slurm_service_local: SlurmServiceLocalHPC) -> None:
    all_jobs: list[SlurmJob] = await slurm_service_local.get_job_status_squeue()
    assert all_jobs is not None
    if len(all_jobs) > 0:
        assert isinstance(all_jobs[0], SlurmJob)
        one_job: list[SlurmJob] = await slurm_service_local.get_job_status_squeue(job_ids=[all_jobs[0].job_id])
        assert one_job is not None
        assert len(one_job) == 1
        assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_query_sacct_remote(slurm_service_remote: SlurmServiceRemoteHPC) -> None:
    all_jobs: list[SlurmJob] = await slurm_service_remote.get_job_status_sacct()
    assert all_jobs is not None
    if len(all_jobs) > 0:
        assert isinstance(all_jobs[0], SlurmJob)
        one_job: list[SlurmJob] = await slurm_service_remote.get_job_status_sacct(job_ids=[all_jobs[0].job_id])
        assert one_job is not None
        assert len(one_job) == 1
        assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_query_sacct_local(slurm_service_local: SlurmServiceLocalHPC) -> None:
    all_jobs: list[SlurmJob] = await slurm_service_local.get_job_status_sacct()
    assert all_jobs is not None
    if len(all_jobs) > 0:
        assert isinstance(all_jobs[0], SlurmJob)
        one_job: list[SlurmJob] = await slurm_service_local.get_job_status_sacct(job_ids=[all_jobs[0].job_id])
        assert one_job is not None
        assert len(one_job) == 1
        assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_submit_remote(
    slurm_service_remote: SlurmServiceRemoteHPC, slurm_template_hello_1s: str
) -> None:
    _all_jobs_before_submit: list[SlurmJob] = await slurm_service_remote.get_job_status_squeue()
    settings = get_settings()
    remote_path = Path(settings.slurm_log_base_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        # write slurm_template_hello_1s to a temp file
        local_sbatch_file = tmp_dir / f"job_{uuid.uuid4().hex}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(slurm_template_hello_1s)

        remote_sbatch_file = remote_path / local_sbatch_file.name
        job_id: int = await slurm_service_remote.submit_job(
            local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
        )

        submitted_job: list[SlurmJob] = await slurm_service_remote.get_job_status_squeue(job_ids=[job_id])
        assert submitted_job is not None and len(submitted_job) == 1
        assert submitted_job[0].job_id == job_id
        assert submitted_job[0].name == "my_test_job"


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_submit_local(slurm_service_local: SlurmServiceLocalHPC, slurm_template_hello_1s: str) -> None:
    _all_jobs_before_submit: list[SlurmJob] = await slurm_service_local.get_job_status_squeue()
    settings = get_settings()
    remote_path = Path(settings.slurm_log_base_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        # write slurm_template_hello_1s to a temp file
        local_sbatch_file = tmp_dir / f"job_{uuid.uuid4().hex}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(slurm_template_hello_1s)

        remote_sbatch_file = remote_path / local_sbatch_file.name
        job_id: int = await slurm_service_local.submit_job(
            local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
        )

        submitted_job: list[SlurmJob] = await slurm_service_local.get_job_status_squeue(job_ids=[job_id])
        assert submitted_job is not None and len(submitted_job) == 1
        assert submitted_job[0].job_id == job_id
        assert submitted_job[0].name == "my_test_job"
