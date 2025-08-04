import asyncio
import random
import string
import tempfile
import uuid
from pathlib import Path

import pytest
from nats.aio.client import Client as NATSClient

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
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
    WorkerEvent, WorkerEventMessagePayload,
)


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
