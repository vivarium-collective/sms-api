import asyncio
import random
import string
import time

import pytest

from sms_api.config import get_settings
from sms_api.dependencies import get_ssh_session_service
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

    # Use single SSH session for all HPC operations
    async with get_ssh_session_service().session() as ssh:
        # Submit build job (which now includes cloning the repository)
        build_job_id = await simulation_service_slurm.submit_build_image_job(simulator_version=simulator, ssh=ssh)
        assert build_job_id is not None

        start_time = time.time()
        while start_time + 60 > time.time():
            slurm_job_build = await simulation_service_slurm.get_slurm_job_status(slurmjobid=build_job_id, ssh=ssh)
            if slurm_job_build is not None and slurm_job_build.is_done():
                break
            await asyncio.sleep(5)

        assert slurm_job_build is not None
        assert slurm_job_build.is_done()
        assert slurm_job_build.job_id == build_job_id
        assert slurm_job_build.name.startswith(f"build-image-{commit_hash}-")

        parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=ParcaOptions())
        parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

        # run parca
        parca_slurmjobid = await simulation_service_slurm.submit_parca_job(parca_dataset=parca_dataset, ssh=ssh)
        assert parca_slurmjobid is not None

        start_time = time.time()
        while start_time + 60 > time.time():
            slurm_job_parca = await simulation_service_slurm.get_slurm_job_status(slurmjobid=parca_slurmjobid, ssh=ssh)
            if slurm_job_parca is not None and slurm_job_parca.is_done():
                break
            await asyncio.sleep(5)

        assert slurm_job_parca is not None
        assert slurm_job_parca.is_done()
        assert slurm_job_parca.job_id == parca_slurmjobid
        assert slurm_job_parca.name.startswith(f"parca-{commit_hash}-")

        simulation_request = SimulationRequest(
            simulator_id=simulator.database_id,
            parca_dataset_id=parca_dataset.database_id,
            config=SimulationConfig(experiment_id="test_simulate"),
        )
        simulation = await database_service.insert_simulation(sim_request=simulation_request)

        random_string = "".join(random.choices(string.hexdigits, k=7))
        correlation_id = get_correlation_id(
            ecoli_simulation=simulation, random_string=random_string, simulator=simulator
        )
        sim_slurmjobid = await simulation_service_slurm.submit_ecoli_simulation_job(
            ecoli_simulation=simulation, database_service=database_service, correlation_id=correlation_id, ssh=ssh
        )
        assert sim_slurmjobid is not None

        hpcrun = await database_service.insert_hpcrun(
            slurmjobid=sim_slurmjobid,
            job_type=JobType.SIMULATION,
            ref_id=simulation.database_id,
            correlation_id=correlation_id,
        )
        assert hpcrun is not None
        assert hpcrun.slurmjobid == sim_slurmjobid
        assert hpcrun.job_type == JobType.SIMULATION
        assert hpcrun.ref_id == simulation.database_id

        start_time = time.time()
        while start_time + 300 > time.time():  # 5 minutes for simulation to complete
            sim_slurmjob = await simulation_service_slurm.get_slurm_job_status(slurmjobid=sim_slurmjobid, ssh=ssh)
            if sim_slurmjob is not None and sim_slurmjob.is_done():
                break
            await asyncio.sleep(5)

        assert sim_slurmjob is not None
        assert sim_slurmjob.is_done()
        assert sim_slurmjob.job_id == sim_slurmjobid
        assert sim_slurmjob.name.startswith(f"sim-{commit_hash}-")
