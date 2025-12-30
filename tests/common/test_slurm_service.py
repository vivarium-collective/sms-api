import asyncio
import tempfile
import uuid
from pathlib import Path

import pytest

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.dependencies import get_ssh_session_service


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_query_squeue(slurm_service: SlurmService) -> None:
    all_jobs: list[SlurmJob] = await slurm_service.get_job_status_squeue()
    assert all_jobs is not None
    if len(all_jobs) > 0:
        assert isinstance(all_jobs[0], SlurmJob)
        one_job: list[SlurmJob] = await slurm_service.get_job_status_squeue(job_ids=[all_jobs[0].job_id])
        assert one_job is not None
        assert len(one_job) == 1
        assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_query_sacct(slurm_service: SlurmService) -> None:
    all_jobs: list[SlurmJob] = await slurm_service.get_job_status_sacct()
    assert all_jobs is not None
    if len(all_jobs) > 0:
        assert isinstance(all_jobs[0], SlurmJob)
        one_job: list[SlurmJob] = await slurm_service.get_job_status_sacct(job_ids=[all_jobs[0].job_id])
        assert one_job is not None
        assert len(one_job) == 1
        assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_submit(slurm_service: SlurmService, slurm_template_hello_1s: str) -> None:
    _all_jobs_before_submit: list[SlurmJob] = await slurm_service.get_job_status_squeue()
    settings = get_settings()
    remote_path = settings.slurm_log_base_path
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        # write slurm_template_hello_1s to a temp file
        local_sbatch_file = tmp_dir / f"job_{uuid.uuid4().hex}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(slurm_template_hello_1s)

        remote_sbatch_file = remote_path / local_sbatch_file.name
        job_id: int = await slurm_service.submit_job(
            local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
        )

        submitted_job: list[SlurmJob] = await slurm_service.get_job_status_squeue(job_ids=[job_id])
        assert submitted_job is not None and len(submitted_job) == 1
        assert submitted_job[0].job_id == job_id
        assert submitted_job[0].name == "my_test_job"


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_nextflow_workflow_via_slurm(
    slurm_service: SlurmService,
    ssh_session_service: SSHSessionService,
    nextflow_script_hello: str,
    slurm_template_nextflow: str,
) -> None:
    """
    Test that Nextflow is properly configured on the remote Slurm cluster.

    This test:
    1. Uploads a simple Nextflow workflow and sbatch script
    2. Submits the job to Slurm
    3. Polls for job completion
    4. Verifies the workflow completed successfully
    """
    settings = get_settings()
    remote_base_path = settings.slurm_log_base_path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        job_uuid = uuid.uuid4().hex

        # Common file prefix for all job files
        file_prefix = f"nextflow_test_{job_uuid}"

        # Write Nextflow script to local temp file
        local_nf_script = tmp_dir / f"{file_prefix}.nf"
        with open(local_nf_script, "w") as f:
            f.write(nextflow_script_hello)

        # Calculate remote paths
        remote_nf_script = remote_base_path / local_nf_script.name
        remote_output_file = remote_base_path / f"{file_prefix}.out"
        remote_error_file = remote_base_path / f"{file_prefix}.err"
        remote_report_file = remote_base_path / f"{file_prefix}.report.html"
        remote_trace_file = remote_base_path / f"{file_prefix}.trace.txt"
        remote_events_file = remote_base_path / f"{file_prefix}.events.ndjson"

        # Update sbatch template with the remote paths
        sbatch_content = slurm_template_nextflow.replace(
            "NEXTFLOW_SCRIPT_PATH", str(remote_nf_script)
        ).replace(
            "REMOTE_LOG_OUTPUT_FILE", str(remote_output_file)
        ).replace(
            "REMOTE_LOG_ERROR_FILE", str(remote_error_file)
        ).replace(
            "REMOTE_REPORT_FILE", str(remote_report_file)
        ).replace(
            "REMOTE_TRACE_FILE", str(remote_trace_file)
        ).replace(
            "REMOTE_EVENTS_FILE", str(remote_events_file)
        )

        # Write sbatch script to local temp file
        local_sbatch_file = tmp_dir / f"{file_prefix}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(sbatch_content)

        remote_sbatch_file = remote_base_path / local_sbatch_file.name

        # Upload Nextflow script first
        async with get_ssh_session_service().session() as ssh:
            await ssh.scp_upload(local_file=local_nf_script, remote_path=remote_nf_script)

        # Submit the Slurm job
        job_id: int = await slurm_service.submit_job(
            local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
        )
        assert job_id > 0, "Failed to get valid job ID"

        # Poll for job completion (max 5 minutes)
        # Note: We go straight to polling since squeue/sacct may have delays
        max_wait_seconds = 300
        poll_interval_seconds = 5
        elapsed_seconds = 0
        final_job: SlurmJob | None = None

        while elapsed_seconds < max_wait_seconds:
            # Check squeue first (for running/pending jobs)
            jobs: list[SlurmJob] = await slurm_service.get_job_status_squeue(job_ids=[job_id])
            if len(jobs) > 0:
                if jobs[0].job_state.upper() in ["PENDING", "RUNNING", "CONFIGURING"]:
                    # Job still in progress
                    await asyncio.sleep(poll_interval_seconds)
                    elapsed_seconds += poll_interval_seconds
                    continue

            # Check sacct for completed jobs (may have delay before appearing)
            jobs = await slurm_service.get_job_status_sacct(job_ids=[job_id])
            if len(jobs) > 0:
                final_job = jobs[0]
                if final_job.is_done():
                    # Job completed
                    break

            await asyncio.sleep(poll_interval_seconds)
            elapsed_seconds += poll_interval_seconds

        assert final_job is not None, f"Nextflow job {job_id} not found in squeue or sacct after {max_wait_seconds} seconds"
        assert final_job.name == "nextflow_test", f"Unexpected job name: {final_job.name}"
        assert final_job.job_state.upper() == "COMPLETED", (
            f"Nextflow job failed with state: {final_job.job_state}, "
            f"exit code: {final_job.exit_code}"
        )
