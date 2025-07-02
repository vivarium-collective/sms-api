import asyncio
import uuid

import pytest
from nats.aio.client import Client as NATSClient

from sms_api.common.hpc.models import SlurmJob
from sms_api.config import get_settings
from sms_api.simulation.job_scheduler import JobScheduler
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    HpcRun,
    JobType,
    ParcaDatasetRequest,
    WorkerEvent,
)
from sms_api.simulation.simulation_database import SimulationDatabaseService


async def insert_job(database_service: SimulationDatabaseService) -> tuple[EcoliSimulation, SlurmJob, HpcRun]:
    latest_commit_hash = str(uuid.uuid4())
    repo_url = "https://github.com/some/repo"
    main_branch = "main"

    simulator = await database_service.insert_simulator(
        git_commit_hash=latest_commit_hash, git_repo_url=repo_url, git_branch=main_branch
    )

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config={"param1": 5})
    parca_dataset = await database_service.get_or_insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    simulation_request = EcoliSimulationRequest(
        simulator=simulator,
        parca_dataset_id=parca_dataset.database_id,
        variant_config={"named_parameters": {"param1": 0.5, "param2": 0.5}},
    )
    simulation = await database_service.insert_simulation(sim_request=simulation_request)
    slurm_job = SlurmJob(
        job_id=1,
        name="name",
        account="acct",
        batch_flag=False,
        batch_host="host",
        cluster="cluster",
        command="run a sim",
        user_name="user",
        job_state=["Running"],
    )

    hpcrun = await database_service.insert_hpcrun(
        slurmjobid=slurm_job.job_id, job_type=JobType.SIMULATION, ref_id=simulation.database_id
    )

    return simulation, slurm_job, hpcrun


@pytest.mark.asyncio
async def test_messaging(
    nats_subscriber_client: NATSClient, nats_producer_client: NATSClient, database_service: SimulationDatabaseService
) -> None:
    scheduler = JobScheduler(nats_client=nats_subscriber_client, database_service=database_service)
    await scheduler.subscribe()

    # Simulate a job submission and worker event handling
    simulation, slurm_job, hpc_run = await insert_job(database_service=database_service)

    # get the initial state of a job
    sequence_number = 1
    worker_event = WorkerEvent(
        database_id=simulation.database_id,
        sequence_number=sequence_number,
        sim_data=[("mass", "path__to__mass", 1.0)],
        hpcrun_id=hpc_run.database_id,
    )

    # send worker messages to the broker
    await nats_producer_client.publish(
        subject=get_settings().nats_worker_event_subject,
        payload=worker_event.model_dump_json(exclude_unset=True, exclude_none=True).encode("utf-8"),
    )
    # get the updated state of the job
    await asyncio.sleep(0.1)
    _updated_worker_events = await database_service.list_worker_events(
        hpcrun_id=hpc_run.database_id, prev_sequence_number=sequence_number - 1
    )
    assert len(_updated_worker_events) == 1
