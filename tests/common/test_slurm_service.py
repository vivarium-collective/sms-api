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
    async with get_ssh_session_service().session() as ssh:
        all_jobs: list[SlurmJob] = await slurm_service.get_job_status_squeue(ssh)
        assert all_jobs is not None
        if len(all_jobs) > 0:
            assert isinstance(all_jobs[0], SlurmJob)
            one_job: list[SlurmJob] = await slurm_service.get_job_status_squeue(ssh, job_ids=[all_jobs[0].job_id])
            assert one_job is not None
            assert len(one_job) == 1
            assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_query_sacct(slurm_service: SlurmService) -> None:
    async with get_ssh_session_service().session() as ssh:
        all_jobs: list[SlurmJob] = await slurm_service.get_job_status_sacct(ssh)
        assert all_jobs is not None
        if len(all_jobs) > 0:
            assert isinstance(all_jobs[0], SlurmJob)
            one_job: list[SlurmJob] = await slurm_service.get_job_status_sacct(ssh, job_ids=[all_jobs[0].job_id])
            assert one_job is not None
            assert len(one_job) == 1
            assert one_job[0] == all_jobs[0]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_slurm_job_submit(slurm_service: SlurmService, slurm_template_hello_1s: str) -> None:
    settings = get_settings()
    remote_path = settings.slurm_log_base_path
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        # write slurm_template_hello_1s to a temp file
        local_sbatch_file = tmp_dir / f"job_{uuid.uuid4().hex}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(slurm_template_hello_1s)

        remote_sbatch_file = remote_path / local_sbatch_file.name
        async with get_ssh_session_service().session() as ssh:
            job_id: int = await slurm_service.submit_job(
                ssh, local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
            )

            submitted_job: list[SlurmJob] = await slurm_service.get_job_status_squeue(ssh, job_ids=[job_id])
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

        # Use single SSH session for file upload, job submission, and polling
        async with get_ssh_session_service().session() as ssh:
            # Upload files to remote
            await ssh.scp_upload(local_file=local_nf_script, remote_path=remote_nf_script)
            await ssh.scp_upload(local_file=local_nf_config, remote_path=remote_nf_config)

            # Submit the Slurm job
            job_id: int = await slurm_service.submit_job(
                ssh, local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
            )
            assert job_id > 0, "Failed to get valid job ID"

            # Poll for job completion
            elapsed_seconds = 0
            final_job: SlurmJob | None = None

            while elapsed_seconds < max_wait_seconds:
                # Check squeue first (for running/pending jobs)
                jobs: list[SlurmJob] = await slurm_service.get_job_status_squeue(ssh, job_ids=[job_id])
                if len(jobs) > 0 and jobs[0].job_state.upper() in ["PENDING", "RUNNING", "CONFIGURING"]:
                    await asyncio.sleep(poll_interval_seconds)
                    elapsed_seconds += poll_interval_seconds
                    continue

                # Check sacct for completed jobs (may have delay before appearing)
                jobs = await slurm_service.get_job_status_sacct(ssh, job_ids=[job_id])
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


# =============================================================================
# SMS CCAM Nextflow Workflow Integration Test
# =============================================================================


async def _run_sms_ccam_nextflow_test(
    slurm_service: SlurmService,
    main_nf_content: str,
    workflow_config_content: str,
    nextflow_config: str,
    sbatch_template: str,
    *,
    file_prefix: str,
    expected_job_name: str,
    use_stub_mode: bool = True,
    max_wait_seconds: int = 600,
    poll_interval_seconds: int = 10,
) -> NextflowTestResult:
    """
    Run the SMS CCAM Nextflow workflow via Slurm with workflow_config.json support.

    This helper handles the SMS CCAM workflow which requires:
    - Uploading the main.nf workflow file
    - Uploading the workflow_config.json file (referenced from main.nf via params.config)
    - Optionally running in stub mode to skip actual process execution

    Args:
        slurm_service: The Slurm service for job submission and status checks
        main_nf_content: The main.nf workflow script content
        workflow_config_content: The workflow_config.json content
        nextflow_config: Nextflow config file content
        sbatch_template: The sbatch template with placeholders
        file_prefix: Prefix for all generated files
        expected_job_name: Expected Slurm job name for assertion
        use_stub_mode: If True, runs Nextflow with -stub flag
        max_wait_seconds: Maximum time to wait for job completion
        poll_interval_seconds: Interval between status checks

    Returns:
        NextflowTestResult with job details and file paths
    """
    settings = get_settings()
    remote_base_path = settings.slurm_log_base_path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)

        # Create a subdirectory for this test run (simulates the nextflow output structure)
        test_output_dir = remote_base_path / f"{file_prefix}_output"

        # Write main.nf to local temp file
        local_nf_script = tmp_dir / f"{file_prefix}.nf"
        with open(local_nf_script, "w") as f:
            f.write(main_nf_content)

        # Write workflow_config.json to local temp file
        local_workflow_config = tmp_dir / "workflow_config.json"
        with open(local_workflow_config, "w") as f:
            f.write(workflow_config_content)

        # Calculate remote paths
        remote_nf_script = remote_base_path / local_nf_script.name
        remote_workflow_config = test_output_dir / "workflow_config.json"
        remote_output_file = remote_base_path / f"{file_prefix}.out"
        remote_error_file = remote_base_path / f"{file_prefix}.err"
        remote_report_file = remote_base_path / f"{file_prefix}.report.html"
        remote_trace_file = remote_base_path / f"{file_prefix}.trace.txt"
        remote_events_file = remote_base_path / f"{file_prefix}.events.ndjson"
        remote_work_dir = remote_base_path / f"{file_prefix}_work"

        # Update nextflow config with actual paths
        config_content = (
            nextflow_config.replace("WORK_DIR_PLACEHOLDER", str(remote_work_dir))
            .replace("WORKFLOW_CONFIG_PATH", str(remote_workflow_config))
            .replace("PUBLISH_DIR_PLACEHOLDER", str(test_output_dir))
        )

        # Write nextflow config to local temp file
        local_nf_config = tmp_dir / f"{file_prefix}.config"
        with open(local_nf_config, "w") as f:
            f.write(config_content)

        remote_nf_config = remote_base_path / local_nf_config.name

        # Build sbatch content with placeholders replaced
        sbatch_content = (
            sbatch_template.replace("NEXTFLOW_SCRIPT_PATH", str(remote_nf_script))
            .replace("REMOTE_LOG_OUTPUT_FILE", str(remote_output_file))
            .replace("REMOTE_LOG_ERROR_FILE", str(remote_error_file))
            .replace("REMOTE_REPORT_FILE", str(remote_report_file))
            .replace("REMOTE_TRACE_FILE", str(remote_trace_file))
            .replace("REMOTE_EVENTS_FILE", str(remote_events_file))
            .replace("NEXTFLOW_CONFIG_PATH", str(remote_nf_config))
        )

        # Add -stub flag if stub mode is enabled
        if use_stub_mode:
            # Insert -stub after "nextflow run"
            sbatch_content = sbatch_content.replace(
                'nextflow run "$NF_SCRIPT"',
                'nextflow run "$NF_SCRIPT" -stub',
            )

        # Write sbatch script to local temp file
        local_sbatch_file = tmp_dir / f"{file_prefix}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(sbatch_content)

        remote_sbatch_file = remote_base_path / local_sbatch_file.name

        # Use single SSH session for all operations
        async with get_ssh_session_service().session() as ssh:
            # Create remote output directory for workflow_config.json
            await ssh.run_command(f"mkdir -p {test_output_dir}")

            # Upload all files to remote
            await ssh.scp_upload(local_file=local_nf_script, remote_path=remote_nf_script)
            await ssh.scp_upload(local_file=local_nf_config, remote_path=remote_nf_config)
            await ssh.scp_upload(local_file=local_workflow_config, remote_path=remote_workflow_config)

            # Submit the Slurm job
            job_id: int = await slurm_service.submit_job(
                ssh, local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
            )
            assert job_id > 0, "Failed to get valid job ID"

            # Poll for job completion
            elapsed_seconds = 0
            final_job: SlurmJob | None = None

            while elapsed_seconds < max_wait_seconds:
                # Check squeue first (for running/pending jobs)
                jobs: list[SlurmJob] = await slurm_service.get_job_status_squeue(ssh, job_ids=[job_id])
                if len(jobs) > 0 and jobs[0].job_state.upper() in ["PENDING", "RUNNING", "CONFIGURING"]:
                    await asyncio.sleep(poll_interval_seconds)
                    elapsed_seconds += poll_interval_seconds
                    continue

                # Check sacct for completed jobs
                jobs = await slurm_service.get_job_status_sacct(ssh, job_ids=[job_id])
                if len(jobs) > 0:
                    final_job = jobs[0]
                    if final_job.is_done():
                        break

                await asyncio.sleep(poll_interval_seconds)
                elapsed_seconds += poll_interval_seconds

        # Assertions
        assert final_job is not None, (
            f"SMS CCAM Nextflow job {job_id} not found in squeue or sacct after {max_wait_seconds} seconds"
        )
        assert final_job.name == expected_job_name, f"Unexpected job name: {final_job.name}"
        assert final_job.job_state.upper() == "COMPLETED", (
            f"SMS CCAM Nextflow job failed with state: {final_job.job_state}, exit code: {final_job.exit_code}"
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
async def test_nextflow_workflow_sms_ccam_slurm_executor(
    slurm_service: SlurmService,
    ssh_session_service: SSHSessionService,
    sms_ccam_main_stub_nf: str,
    sms_ccam_workflow_config: str,
    nextflow_config_sms_ccam_executor: str,
    slurm_template_nextflow_sms_ccam: str,
) -> None:
    """
    Integration test for SMS CCAM Nextflow workflow using SLURM executor.

    This test:
    - Uploads the self-contained main_stub.nf workflow from tests/fixtures/nextflow_inputs/
    - Uploads the workflow_config.json (referenced from main.nf via params.config)
    - Runs the workflow in stub mode to test the workflow structure without
      actually running the computationally expensive simulation processes
    - Verifies the Nextflow job completes successfully

    Note: This test uses main_stub.nf instead of main.nf because the original
    workflow includes external vEcoli modules that don't have stub blocks.
    The main_stub.nf version has self-contained process definitions with stub
    blocks for all processes, allowing the workflow DAG to be tested in -stub mode.
    """
    job_uuid = uuid.uuid4().hex

    result = await _run_sms_ccam_nextflow_test(
        slurm_service=slurm_service,
        main_nf_content=sms_ccam_main_stub_nf,
        workflow_config_content=sms_ccam_workflow_config,
        nextflow_config=nextflow_config_sms_ccam_executor,
        sbatch_template=slurm_template_nextflow_sms_ccam,
        file_prefix=f"sms_ccam_{job_uuid}",
        expected_job_name="nextflow_sms_ccam_test",
        use_stub_mode=True,
        max_wait_seconds=900,  # 15 minutes for stub mode
        poll_interval_seconds=15,
    )

    assert result.final_job.job_state.upper() == "COMPLETED"


@pytest.mark.skip(reason="BLOCKED: vEcoli NegativeCountsError bug - infrastructure works, simulation has model issues")
@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_nextflow_workflow_sms_ccam_real_simulation(
    slurm_service: SlurmService,
    ssh_session_service: SSHSessionService,
    sms_ccam_main_real_nf: str,
    sms_ccam_workflow_config_real: str,
    nextflow_config_sms_ccam_real: str,
    slurm_template_nextflow_sms_ccam_real: str,
) -> None:
    """
    Integration test for real SMS CCAM simulation using SLURM executor.

    This test:
    - Runs an actual vEcoli simulation (not stub mode)
    - Uses existing parca dataset to skip ParCa step
    - Uses Singularity container with vEcoli image
    - Produces parquet output files
    - Uses hpc_sim_base_path for output directory

    Note: This test takes longer than the stub test (~5-30 minutes depending
    on simulation parameters). It's meant to verify the full simulation
    pipeline works correctly.
    """
    settings = get_settings()
    job_uuid = uuid.uuid4().hex[:8]
    experiment_id = f"integration_test_{job_uuid}"

    # Use hpc_sim_base_path for output
    output_base_path = settings.hpc_sim_base_path
    remote_base_path = settings.slurm_log_base_path

    # Paths for existing resources
    sim_data_path = "/projects/SMS/sms_api/alex/parca/parca_8f119dd_id_1/kb/simData.cPickle"
    container_image = "/projects/SMS/sms_api/alex/images/vecoli-8f119dd.sif"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        file_prefix = f"sms_ccam_real_{job_uuid}"

        # Output directory for simulation results
        test_output_dir = HPCFilePath(remote_path=Path(str(output_base_path.remote_path) + f"/{experiment_id}"))

        # Write main.nf to local temp file
        local_nf_script = tmp_dir / f"{file_prefix}.nf"
        with open(local_nf_script, "w") as f:
            f.write(sms_ccam_main_real_nf)

        # Update workflow config with actual paths
        workflow_config_content = (
            sms_ccam_workflow_config_real.replace("PUBLISH_DIR_PLACEHOLDER", str(test_output_dir.remote_path))
        )

        # Write workflow_config.json to local temp file
        local_workflow_config = tmp_dir / "workflow_config.json"
        with open(local_workflow_config, "w") as f:
            f.write(workflow_config_content)

        # Calculate remote paths (wrap in HPCFilePath for scp_upload)
        remote_nf_script = HPCFilePath(remote_path=remote_base_path.remote_path / local_nf_script.name)
        remote_workflow_config = HPCFilePath(remote_path=test_output_dir.remote_path / "workflow_config.json")
        remote_nf_config_path = HPCFilePath(remote_path=remote_base_path.remote_path / f"{file_prefix}.config")
        remote_output_file = remote_base_path.remote_path / f"{file_prefix}.out"
        remote_error_file = remote_base_path.remote_path / f"{file_prefix}.err"
        remote_report_file = remote_base_path.remote_path / f"{file_prefix}.report.html"
        remote_trace_file = remote_base_path.remote_path / f"{file_prefix}.trace.txt"
        remote_events_file = remote_base_path.remote_path / f"{file_prefix}.events.ndjson"
        remote_work_dir = remote_base_path.remote_path / f"{file_prefix}_work"

        # Update nextflow config with actual paths
        config_content = (
            nextflow_config_sms_ccam_real.replace("WORK_DIR_PLACEHOLDER", str(remote_work_dir))
            .replace("WORKFLOW_CONFIG_PATH", str(remote_workflow_config.remote_path))
            .replace("PUBLISH_DIR_PLACEHOLDER", str(test_output_dir.remote_path))
            .replace("EXPERIMENT_ID_PLACEHOLDER", experiment_id)
            .replace("SIM_DATA_PATH_PLACEHOLDER", sim_data_path)
            .replace("CONTAINER_IMAGE_PLACEHOLDER", container_image)
        )

        # Write nextflow config to local temp file
        local_nf_config = tmp_dir / f"{file_prefix}.config"
        with open(local_nf_config, "w") as f:
            f.write(config_content)

        # Build sbatch content with placeholders replaced
        sbatch_content = (
            slurm_template_nextflow_sms_ccam_real.replace("NEXTFLOW_SCRIPT_PATH", str(remote_nf_script.remote_path))
            .replace("REMOTE_LOG_OUTPUT_FILE", str(remote_output_file))
            .replace("REMOTE_LOG_ERROR_FILE", str(remote_error_file))
            .replace("REMOTE_REPORT_FILE", str(remote_report_file))
            .replace("REMOTE_TRACE_FILE", str(remote_trace_file))
            .replace("REMOTE_EVENTS_FILE", str(remote_events_file))
            .replace("NEXTFLOW_CONFIG_PATH", str(remote_nf_config_path.remote_path))
        )

        # Use real profile instead of stub mode
        sbatch_content = sbatch_content.replace(
            'nextflow run "$NF_SCRIPT"',
            'nextflow run "$NF_SCRIPT" -profile ccam_real',
        )

        # Write sbatch script to local temp file
        local_sbatch_file = tmp_dir / f"{file_prefix}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(sbatch_content)

        remote_sbatch_file = HPCFilePath(remote_path=remote_base_path.remote_path / local_sbatch_file.name)

        # Use single SSH session for all operations
        async with get_ssh_session_service().session() as ssh:
            # Create remote output directory for workflow_config.json
            await ssh.run_command(f"mkdir -p {test_output_dir.remote_path}")

            # Upload all files to remote
            await ssh.scp_upload(local_nf_script, remote_nf_script)
            await ssh.scp_upload(local_nf_config, remote_nf_config_path)
            await ssh.scp_upload(local_workflow_config, remote_workflow_config)

            # Submit the Slurm job
            job_id: int = await slurm_service.submit_job(
                ssh, local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
            )
            assert job_id > 0, "Failed to get valid job ID"

            # Poll for job completion (longer timeout for real simulation)
            max_wait_seconds = 7200  # 2 hours
            poll_interval_seconds = 30
            elapsed_seconds = 0
            final_job: SlurmJob | None = None

            while elapsed_seconds < max_wait_seconds:
                # Check squeue first (for running/pending jobs)
                jobs: list[SlurmJob] = await slurm_service.get_job_status_squeue(ssh, job_ids=[job_id])
                if len(jobs) > 0 and jobs[0].job_state.upper() in ["PENDING", "RUNNING", "CONFIGURING"]:
                    await asyncio.sleep(poll_interval_seconds)
                    elapsed_seconds += poll_interval_seconds
                    continue

                # Check sacct for completed jobs
                jobs = await slurm_service.get_job_status_sacct(ssh, job_ids=[job_id])
                if len(jobs) > 0:
                    final_job = jobs[0]
                    if final_job.is_done():
                        break

                await asyncio.sleep(poll_interval_seconds)
                elapsed_seconds += poll_interval_seconds

            # Assertions
            assert final_job is not None, (
                f"Real simulation job {job_id} not found after {max_wait_seconds} seconds"
            )
            assert final_job.name == "nextflow_sms_ccam_real", f"Unexpected job name: {final_job.name}"
            assert final_job.job_state.upper() == "COMPLETED", (
                f"Real simulation failed with state: {final_job.job_state}, exit code: {final_job.exit_code}. "
                f"Check logs at {remote_output_file} and {remote_error_file}"
            )

            # Verify simulation output files were created (using timeseries emitter)
            retcode, stdout, stderr = await ssh.run_command(
                f"find {test_output_dir.remote_path} -type f | head -5"
            )
            output_files = [f for f in stdout.strip().split("\n") if f]
            assert len(output_files) > 0, (
                f"No output files found in output directory {test_output_dir.remote_path}. "
                f"Check logs at {remote_output_file}"
            )
