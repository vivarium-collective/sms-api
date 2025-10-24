import asyncio
import os
import random
import string
import tempfile
import uuid
from pathlib import Path

import pytest
from nats.aio.client import Client as NATSClient

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.storage import FileService, FileServiceQumuloS3, FileServiceS3
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.hpc_utils import get_correlation_id
from sms_api.simulation.job_scheduler import JobScheduler
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    HpcRun,
    JobStatus,
    JobType,
    ParcaDatasetRequest,
    WorkerEventMessagePayload,
)


def is_ci_environment() -> bool:
    """Check if running in CI/CD environment (GitHub Actions, etc.)."""
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


async def insert_job(database_service: DatabaseServiceSQL, slurmjobid: int) -> tuple[EcoliSimulation, SlurmJob, HpcRun]:
    latest_commit_hash = str(uuid.uuid4())
    repo_url = "https://github.com/some/repo"
    main_branch = "main"

    simulator = await database_service.insert_simulator(
        git_commit_hash=latest_commit_hash, git_repo_url=repo_url, git_branch=main_branch
    )

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config={"param1": 5})
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    simulation_request = EcoliSimulationRequest(
        simulator=simulator,
        parca_dataset_id=parca_dataset.database_id,
        variant_config={"named_parameters": {"param1": 0.5, "param2": 0.5}},
    )
    simulation = await database_service.insert_simulation(sim_request=simulation_request)
    slurm_job = SlurmJob(
        job_id=slurmjobid,
        name="name",
        account="acct",
        user_name="user",
        job_state="RUNNING",
    )

    random_string = "".join(random.choices(string.hexdigits, k=7))  # noqa: S311 doesn't need to be secure
    correlation_id = get_correlation_id(ecoli_simulation=simulation, random_string=random_string)
    hpcrun = await database_service.insert_hpcrun(
        slurmjobid=slurm_job.job_id,
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id=correlation_id,
    )

    return simulation, slurm_job, hpcrun


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_messaging(
    nats_subscriber_client: NATSClient,
    nats_producer_client: NATSClient,
    database_service: DatabaseServiceSQL,
    slurm_service: SlurmService,
) -> None:
    scheduler = JobScheduler(
        nats_client=nats_subscriber_client, database_service=database_service, slurm_service=slurm_service
    )
    await scheduler.subscribe()

    # Simulate a job submission and worker event handling
    simulation, slurm_job, hpc_run = await insert_job(database_service=database_service, slurmjobid=1)

    # get the initial state of a job
    sequence_number = 1
    worker_event = WorkerEventMessagePayload(
        sequence_number=sequence_number,
        correlation_id=hpc_run.correlation_id,
        time=0.1,
        mass={"water": 1.0, "glucose": 0.5},
        bulk=None,
    )

    # send worker messages to the broker
    await nats_producer_client.publish(
        subject=get_settings().nats_worker_event_subject,
        payload=worker_event.model_dump_json(exclude_unset=True).encode("utf-8"),
    )
    # get the updated state of the job
    await asyncio.sleep(0.1)
    _updated_worker_events = await database_service.list_worker_events(
        hpcrun_id=hpc_run.database_id, prev_sequence_number=sequence_number - 1
    )
    assert len(_updated_worker_events) == 1


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_job_scheduler(
    nats_subscriber_client: NATSClient,
    database_service: DatabaseServiceSQL,
    slurm_service: SlurmService,
    slurm_template_hello_10s: str,
) -> None:
    scheduler = JobScheduler(
        nats_client=nats_subscriber_client, database_service=database_service, slurm_service=slurm_service
    )
    await scheduler.subscribe()
    await scheduler.start_polling(interval_seconds=1)

    # Submit a toy slurm job which takes 10 seconds to run
    _all_jobs_before_submit: list[SlurmJob] = await slurm_service.get_job_status_squeue()
    settings = get_settings()
    remote_path = Path(settings.slurm_log_base_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        # write slurm_template_hello_1s to a temp file
        local_sbatch_file = tmp_dir / f"job_{uuid.uuid4().hex}.sbatch"
        with open(local_sbatch_file, "w") as f:
            f.write(slurm_template_hello_10s)

        remote_sbatch_file = remote_path / local_sbatch_file.name
        job_id: int = await slurm_service.submit_job(
            local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
        )

    # Simulate job submission
    simulation, slurm_job, hpc_run = await insert_job(database_service=database_service, slurmjobid=job_id)
    assert hpc_run.status == JobStatus.RUNNING

    # Wait for the job to receive a RUNNING status
    await asyncio.sleep(5)

    # Check if the job is in the database
    running_hpcrun: HpcRun | None = await database_service.get_hpcrun_by_slurmjobid(slurmjobid=job_id)
    assert running_hpcrun is not None
    assert running_hpcrun.status == JobStatus.RUNNING

    # Wait for the job to receive a COMPLETE status
    await asyncio.sleep(20)

    # Check if the job is in the database
    completed_hpcrun: HpcRun | None = await database_service.get_hpcrun_by_slurmjobid(slurmjobid=job_id)
    assert completed_hpcrun is not None
    assert completed_hpcrun.status == JobStatus.COMPLETED

    # Stop polling
    await scheduler.stop_polling()


@pytest.mark.skipif(
    is_ci_environment()
    or len(get_settings().slurm_submit_key_path) == 0
    or (len(get_settings().storage_s3_bucket) == 0 and len(get_settings().storage_qumulo_endpoint_url) == 0),
    reason="Skipped in CI/CD or missing slurm ssh key or storage backend configuration",
)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_type",
    [
        pytest.param(
            "aws",
            marks=pytest.mark.skipif(
                is_ci_environment() or len(get_settings().storage_s3_bucket) == 0,
                reason="Skipped in CI/CD or AWS S3 not configured",
            ),
        ),
        pytest.param(
            "qumulo",
            marks=pytest.mark.skipif(
                is_ci_environment() or len(get_settings().storage_qumulo_endpoint_url) == 0,
                reason="Skipped in CI/CD or Qumulo not configured",
            ),
        ),
    ],
)
async def test_job_scheduler_with_storage(
    nats_subscriber_client: NATSClient,
    database_service: DatabaseServiceSQL,
    slurm_service: SlurmService,
    slurm_template_with_storage: str,
    storage_type: str,
) -> None:
    """
    Test Slurm job that downloads from S3-compatible storage, processes data, and uploads back.
    This test validates the complete workflow with the same storage provider for both download/upload:
    1. Upload test input file to storage
    2. Submit Slurm job that downloads from storage
    3. Job processes the file
    4. Job uploads result to same storage using s3_upload function
    5. Verify the output file exists in storage
    6. Cleanup both input and output files

    Tests run with both storage_type="aws" and storage_type="qumulo" (if configured).
    """
    settings = get_settings()
    test_id = uuid.uuid4().hex[:8]
    input_key = f"test/slurm/input_{test_id}.txt"
    output_key = f"test/slurm/output_{test_id}.txt"

    # Initialize the appropriate storage service based on storage_type
    storage_service: FileService
    if storage_type == "aws":
        storage_service = FileServiceS3()
        print(f"\n=== Using AWS S3 storage: {settings.storage_s3_bucket} ===")
    else:  # qumulo
        storage_service = FileServiceQumuloS3()
        print(
            f"\n=== Using Qumulo storage: {settings.storage_qumulo_bucket} "
            f"at {settings.storage_qumulo_endpoint_url} ==="
        )

    try:
        # Step 1: Upload test input file to storage
        print(f"\n=== Step 1: Uploading test input to {storage_type}: {input_key} ===")
        test_input_content = f"Test input file created at {uuid.uuid4()}\n"
        await storage_service.upload_bytes(file_contents=test_input_content.encode("utf-8"), gcs_path=input_key)
        print(f"✅ Test input uploaded to {storage_type}")

        # Step 2: Prepare Slurm job script
        print("\n=== Step 2: Preparing Slurm job ===")
        scheduler = JobScheduler(
            nats_client=nats_subscriber_client, database_service=database_service, slurm_service=slurm_service
        )
        await scheduler.subscribe()
        await scheduler.start_polling(interval_seconds=2)

        # Upload helper script to remote host
        remote_path = Path(settings.slurm_log_base_path)
        helpers_script_path = Path(__file__).parent.parent / "fixtures" / "s3_helpers.sh"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dir = Path(tmpdir)

            # Copy helpers script to temp dir and upload to remote
            remote_helpers = remote_path / "s3_helpers.sh"
            await slurm_service.ssh_service.scp_upload(local_file=helpers_script_path, remote_path=remote_helpers)
            print(f"✅ Uploaded helper script to {remote_helpers}")

            # Prepare the sbatch script with substitutions
            sbatch_content = slurm_template_with_storage
            sbatch_content = sbatch_content.replace("HELPERS_PATH", str(remote_helpers))
            sbatch_content = sbatch_content.replace("INPUT_KEY", input_key)
            sbatch_content = sbatch_content.replace("OUTPUT_KEY", output_key)

            # Add environment variables for storage access based on storage type
            if storage_type == "aws":
                env_vars = f"""
# Set environment variables for AWS S3 access
export STORAGE_TYPE="aws"
export STORAGE_BUCKET="{settings.storage_s3_bucket}"
export AWS_DEFAULT_REGION="{settings.storage_s3_region}"
export AWS_ACCESS_KEY_ID="{settings.storage_s3_access_key_id}"
export AWS_SECRET_ACCESS_KEY="{settings.storage_s3_secret_access_key}"
export AWS_SESSION_TOKEN="{settings.storage_s3_session_token}"
"""
            else:  # qumulo
                env_vars = f"""
# Set environment variables for Qumulo S3 access
export STORAGE_TYPE="qumulo"
export STORAGE_BUCKET="{settings.storage_qumulo_bucket}"
export STORAGE_ENDPOINT_URL="{settings.storage_qumulo_endpoint_url}"
export STORAGE_VERIFY_SSL="false"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="{settings.storage_qumulo_access_key_id}"
export AWS_SECRET_ACCESS_KEY="{settings.storage_qumulo_secret_access_key}"
"""
            # Insert env vars after the SBATCH directives but before the actual commands
            sbatch_lines = sbatch_content.split("\n")
            # Find where to insert (after last #SBATCH line)
            insert_idx = 0
            for i, line in enumerate(sbatch_lines):
                if line.strip().startswith("#SBATCH"):
                    insert_idx = i + 1
            sbatch_lines.insert(insert_idx, env_vars)
            sbatch_content = "\n".join(sbatch_lines)

            # Write sbatch script to temp file
            local_sbatch_file = tmp_dir / f"storage_test_{test_id}.sbatch"
            with open(local_sbatch_file, "w") as f:
                f.write(sbatch_content)

            # Submit job
            remote_sbatch_file = remote_path / local_sbatch_file.name
            print(f"✅ Submitting job with script: {remote_sbatch_file}")
            job_id: int = await slurm_service.submit_job(
                local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
            )
            print(f"✅ Job submitted with ID: {job_id}")

        # Step 3: Insert job into database for tracking
        print("\n=== Step 3: Tracking job in database ===")
        simulation, slurm_job, hpc_run = await insert_job(database_service=database_service, slurmjobid=job_id)
        assert hpc_run.status == JobStatus.RUNNING

        # Step 4: Wait for job to complete
        print("\n=== Step 4: Waiting for job to complete (max 60s) ===")
        max_wait = 60
        check_interval = 5
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(check_interval)
            elapsed += check_interval

            completed_hpcrun: HpcRun | None = await database_service.get_hpcrun_by_slurmjobid(slurmjobid=job_id)
            if completed_hpcrun and completed_hpcrun.status == JobStatus.COMPLETED:
                print(f"✅ Job completed after {elapsed}s")
                break
            print(f"   Waiting... ({elapsed}s / {max_wait}s)")

        # Verify job completed
        final_hpcrun: HpcRun | None = await database_service.get_hpcrun_by_slurmjobid(slurmjobid=job_id)
        assert final_hpcrun is not None, "Job not found in database"
        assert final_hpcrun.status == JobStatus.COMPLETED, f"Job failed with status: {final_hpcrun.status}"

        # Step 5: Verify output file exists in storage
        print(f"\n=== Step 5: Verifying output file in {storage_type} ===")
        output_contents = await storage_service.get_file_contents(output_key)
        assert output_contents is not None, f"Output file not found in {storage_type}: {output_key}"

        output_text = output_contents.decode("utf-8")
        print(f"✅ Output file found in {storage_type} ({len(output_contents)} bytes)")
        print(f"Output contents:\n{output_text}")

        # Verify output contains expected data
        assert "Processed at" in output_text, "Output missing timestamp"
        assert test_input_content.strip() in output_text, "Output missing input file contents"
        assert f"Job ID: {job_id}" in output_text, "Output missing job ID"

        print(f"\n✅ All assertions passed for {storage_type} storage!")

    finally:
        # Step 6: Cleanup
        print("\n=== Step 6: Cleaning up test files ===")
        try:
            # Clean up input file
            print(f"Cleaning up {storage_type} input file: {input_key}")
            await storage_service.delete_file(input_key)
            print(f"✅ Deleted {storage_type} file: {input_key}")

            # Clean up output file
            print(f"Cleaning up {storage_type} output file: {output_key}")
            await storage_service.delete_file(output_key)
            print(f"✅ Deleted {storage_type} file: {output_key}")

        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")

        # Close services
        await storage_service.close()
        await scheduler.stop_polling()
