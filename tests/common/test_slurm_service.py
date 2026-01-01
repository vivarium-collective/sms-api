import asyncio
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.common.storage.file_paths import HPCFilePath
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


# =============================================================================
# Nextflow Workflow Tests
# =============================================================================


@dataclass
class NextflowTestResult:
    """Result from running a Nextflow workflow test."""

    job_id: int
    final_job: SlurmJob
    remote_output_file: HPCFilePath
    remote_error_file: HPCFilePath
    remote_events_file: HPCFilePath
    remote_report_file: HPCFilePath
    remote_trace_file: HPCFilePath


async def _run_nextflow_workflow_test(
    slurm_service: SlurmService,
    nextflow_script: str,
    nextflow_config: str,
    sbatch_template: str,
    *,
    file_prefix: str,
    expected_job_name: str,
    max_wait_seconds: int = 300,
    poll_interval_seconds: int = 5,
) -> NextflowTestResult:
    """
    Shared helper to run a Nextflow workflow via Slurm and poll for completion.

    Args:
        slurm_service: The Slurm service for job submission and status checks
        nextflow_script: The Nextflow workflow script content
        nextflow_config: Nextflow config file content (sets executor and workDir)
        sbatch_template: The sbatch template with placeholders
        file_prefix: Prefix for all generated files (e.g., "nextflow_test_<uuid>")
        expected_job_name: Expected Slurm job name for assertion
        max_wait_seconds: Maximum time to wait for job completion
        poll_interval_seconds: Interval between status checks

    Returns:
        NextflowTestResult with job details and file paths

    Raises:
        AssertionError: If job fails or times out
    """
    settings = get_settings()
    remote_base_path = settings.slurm_log_base_path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)

        # Write Nextflow script to local temp file
        local_nf_script = tmp_dir / f"{file_prefix}.nf"
        with open(local_nf_script, "w") as f:
            f.write(nextflow_script)

        # Calculate remote paths
        remote_nf_script = remote_base_path / local_nf_script.name
        remote_output_file = remote_base_path / f"{file_prefix}.out"
        remote_error_file = remote_base_path / f"{file_prefix}.err"
        remote_report_file = remote_base_path / f"{file_prefix}.report.html"
        remote_trace_file = remote_base_path / f"{file_prefix}.trace.txt"
        remote_events_file = remote_base_path / f"{file_prefix}.events.ndjson"

        # Start with common placeholder replacements
        sbatch_content = (
            sbatch_template.replace("NEXTFLOW_SCRIPT_PATH", str(remote_nf_script))
            .replace("REMOTE_LOG_OUTPUT_FILE", str(remote_output_file))
            .replace("REMOTE_LOG_ERROR_FILE", str(remote_error_file))
            .replace("REMOTE_REPORT_FILE", str(remote_report_file))
            .replace("REMOTE_TRACE_FILE", str(remote_trace_file))
            .replace("REMOTE_EVENTS_FILE", str(remote_events_file))
        )

        # Write Nextflow config to local temp file
        remote_work_dir = remote_base_path / f"{file_prefix}_work"
        config_content = nextflow_config.replace("WORK_DIR_PLACEHOLDER", str(remote_work_dir))

        local_nf_config = tmp_dir / f"{file_prefix}.config"
        with open(local_nf_config, "w") as f:
            f.write(config_content)

        remote_nf_config = remote_base_path / local_nf_config.name
        sbatch_content = sbatch_content.replace("NEXTFLOW_CONFIG_PATH", str(remote_nf_config))

        # Write sbatch script to local temp file
        local_sbatch_file = tmp_dir / f"{file_prefix}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(sbatch_content)

        remote_sbatch_file = remote_base_path / local_sbatch_file.name

        # Upload files to remote
        async with get_ssh_session_service().session() as ssh:
            await ssh.scp_upload(local_file=local_nf_script, remote_path=remote_nf_script)
            await ssh.scp_upload(local_file=local_nf_config, remote_path=remote_nf_config)

        # Submit the Slurm job
        job_id: int = await slurm_service.submit_job(
            local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
        )
        assert job_id > 0, "Failed to get valid job ID"

        # Poll for job completion
        elapsed_seconds = 0
        final_job: SlurmJob | None = None

        while elapsed_seconds < max_wait_seconds:
            # Check squeue first (for running/pending jobs)
            jobs: list[SlurmJob] = await slurm_service.get_job_status_squeue(job_ids=[job_id])
            if len(jobs) > 0 and jobs[0].job_state.upper() in ["PENDING", "RUNNING", "CONFIGURING"]:
                await asyncio.sleep(poll_interval_seconds)
                elapsed_seconds += poll_interval_seconds
                continue

            # Check sacct for completed jobs (may have delay before appearing)
            jobs = await slurm_service.get_job_status_sacct(job_ids=[job_id])
            if len(jobs) > 0:
                final_job = jobs[0]
                if final_job.is_done():
                    break

            await asyncio.sleep(poll_interval_seconds)
            elapsed_seconds += poll_interval_seconds

        # Assertions
        assert final_job is not None, (
            f"Nextflow job {job_id} not found in squeue or sacct after {max_wait_seconds} seconds"
        )
        assert final_job.name == expected_job_name, f"Unexpected job name: {final_job.name}"
        assert final_job.job_state.upper() == "COMPLETED", (
            f"Nextflow job failed with state: {final_job.job_state}, exit code: {final_job.exit_code}"
        )

        return NextflowTestResult(
            job_id=job_id,
            final_job=final_job,
            remote_output_file=remote_output_file,
            remote_error_file=remote_error_file,
            remote_events_file=remote_events_file,
            remote_report_file=remote_report_file,
            remote_trace_file=remote_trace_file,
        )


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_nextflow_workflow_local_executor(
    slurm_service: SlurmService,
    ssh_session_service: SSHSessionService,
    nextflow_script_hello: str,
    nextflow_config_local_executor: str,
    slurm_template_nextflow: str,
) -> None:
    """
    Test Nextflow workflow using the LOCAL executor.

    In this mode:
    - Nextflow runs as a Slurm job
    - Each Nextflow process runs on the SAME node as the parent job
    - No additional Slurm jobs are submitted for processes
    - Faster execution, simpler setup
    - Uses unique work directory per run
    """
    job_uuid = uuid.uuid4().hex

    result = await _run_nextflow_workflow_test(
        slurm_service=slurm_service,
        nextflow_script=nextflow_script_hello,
        nextflow_config=nextflow_config_local_executor,
        sbatch_template=slurm_template_nextflow,
        file_prefix=f"nextflow_test_{job_uuid}",
        expected_job_name="nextflow_test",
        max_wait_seconds=300,
        poll_interval_seconds=5,
    )

    assert result.final_job.job_state.upper() == "COMPLETED"


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_nextflow_workflow_slurm_executor(
    slurm_service: SlurmService,
    ssh_session_service: SSHSessionService,
    nextflow_script_hello_slurm: str,
    nextflow_config_slurm_executor: str,
    slurm_template_nextflow_slurm_executor: str,
) -> None:
    """
    Test Nextflow workflow using the SLURM executor.

    In this mode:
    - Nextflow runs as a parent Slurm job
    - Each Nextflow process is submitted as a SEPARATE Slurm job
    - Child jobs can run on different nodes in the cluster
    - Better for distributed workloads, but has scheduling overhead
    """
    job_uuid = uuid.uuid4().hex

    result = await _run_nextflow_workflow_test(
        slurm_service=slurm_service,
        nextflow_script=nextflow_script_hello_slurm,
        nextflow_config=nextflow_config_slurm_executor,
        sbatch_template=slurm_template_nextflow_slurm_executor,
        file_prefix=f"nextflow_slurm_{job_uuid}",
        expected_job_name="nextflow_slurm_test",
        max_wait_seconds=600,
        poll_interval_seconds=10,
    )

    assert result.final_job.job_state.upper() == "COMPLETED"
