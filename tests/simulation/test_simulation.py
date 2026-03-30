import asyncio
import random
import string
import time
import uuid

import pytest

from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.hpc_utils import get_correlation_id
from sms_api.simulation.models import (
    JobType,
    ParcaDatasetRequest,
    ParcaOptions,
    SimulationConfig,
    SimulationRequest,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationServiceHpc
from tests.fixtures.api_fixtures import SimulatorRepoInfo


@pytest.mark.integration
@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_simulate(
    simulation_service_slurm: SimulationServiceHpc,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    repo_url, main_branch, commit_hash = simulator_repo_info

    # check if the latest commit is already installed
    simulator: SimulatorVersion | None = None
    for _simulator in await database_service.list_simulators():
        if (
            _simulator.git_commit_hash == commit_hash
            and _simulator.git_repo_url == repo_url
            and _simulator.git_branch == main_branch
        ):
            simulator = _simulator
            break

    # insert the latest commit into the database
    if simulator is None:
        simulator = await database_service.insert_simulator(
            git_commit_hash=commit_hash, git_repo_url=repo_url, git_branch=main_branch
        )

    from sms_api.common.models import JobStatus

    # Submit build job
    build_job_id = await simulation_service_slurm.submit_build_image_job(simulator_version=simulator)
    assert build_job_id is not None

    start_time = time.time()
    build_status = None
    while start_time + 60 > time.time():
        build_status = await simulation_service_slurm.get_job_status(job_id=build_job_id)
        if build_status is not None and build_status.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            break
        await asyncio.sleep(5)

    assert build_status is not None
    assert build_status.status in (JobStatus.COMPLETED, JobStatus.FAILED)

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=ParcaOptions())
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    # run parca
    parca_job_id = await simulation_service_slurm.submit_parca_job(parca_dataset=parca_dataset)
    assert parca_job_id is not None

    start_time = time.time()
    parca_status = None
    while start_time + 60 > time.time():
        parca_status = await simulation_service_slurm.get_job_status(job_id=parca_job_id)
        if parca_status is not None and parca_status.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            break
        await asyncio.sleep(5)

    assert parca_status is not None
    assert parca_status.status in (JobStatus.COMPLETED, JobStatus.FAILED)

    expid = f"test-{uuid.uuid4()!s}"
    simulation_request = SimulationRequest(
        experiment_id=expid,
        simulation_config_filename="api_simulation_default_with_profile.json",
        simulator_id=simulator.database_id,
        parca_dataset_id=parca_dataset.database_id,
        config=SimulationConfig(experiment_id=expid),
    )
    simulation = await database_service.insert_simulation(sim_request=simulation_request)

    random_string = "".join(random.choices(string.hexdigits, k=7))
    correlation_id = get_correlation_id(ecoli_simulation=simulation, random_string=random_string, simulator=simulator)
    sim_job_id = await simulation_service_slurm.submit_ecoli_simulation_job(
        ecoli_simulation=simulation, database_service=database_service, correlation_id=correlation_id
    )
    assert sim_job_id is not None

    hpcrun = await database_service.insert_hpcrun(
        external_job_id=sim_job_id,
        job_backend="slurm",
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id=correlation_id,
    )
    assert hpcrun is not None
    assert hpcrun.slurmjobid == int(sim_job_id)
    assert hpcrun.job_type == JobType.SIMULATION
    assert hpcrun.ref_id == simulation.database_id

    start_time = time.time()
    sim_status = None
    while start_time + 300 > time.time():  # 5 minutes for simulation to complete
        sim_status = await simulation_service_slurm.get_job_status(job_id=sim_job_id)
        if sim_status is not None and sim_status.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            break
        await asyncio.sleep(5)

    assert sim_status is not None
    assert sim_status.status in (JobStatus.COMPLETED, JobStatus.FAILED)
