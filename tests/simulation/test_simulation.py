import asyncio
import json
import time

import pytest

from sms_api.common.hpc.sim_utils import read_latest_commit
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.database_service import SimulationDatabaseService
from sms_api.simulation.models import EcoliSimulation, EcoliSimulationRequest, ParcaDatasetRequest, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationServiceHpc

main_branch = "master"
repo_url = "https://github.com/CovertLab/vEcoli"
# latest_commit_hash = "96bb7a2"
latest_commit_hash = read_latest_commit()


async def write_test_request(simulation: EcoliSimulation) -> None:
    try:
        with open("assets/tests/test_request.json", "w") as f:
            json.dump(simulation.model_dump(), f, indent=4)
    except Exception as e:
        print(e)


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_latest_repo_installed(ssh_service: SSHService) -> None:
    return_code, stdout, stderr = await ssh_service.run_command(f"git ls-remote -h {repo_url} {main_branch}")
    assert return_code == 0
    assert stdout.strip("\n").split()[0][:7] == latest_commit_hash


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_simulate(
    simulation_service_slurm: SimulationServiceHpc, database_service: SimulationDatabaseService
) -> None:
    # check if the latest commit is already installed
    simulator: SimulatorVersion | None = None
    for _simulator in await database_service.list_simulators():
        if (
            _simulator.git_commit_hash == latest_commit_hash
            and _simulator.git_repo_url == repo_url
            and _simulator.git_branch == main_branch
        ):
            simulator = _simulator
            break

    # insert the latest commit into the database
    if simulator is None:
        simulator = await database_service.insert_simulator(
            git_commit_hash=latest_commit_hash, git_repo_url=repo_url, git_branch=main_branch
        )

    # clone the repository if needed
    await simulation_service_slurm.clone_repository_if_needed(
        git_commit_hash=simulator.git_commit_hash, git_repo_url=simulator.git_repo_url, git_branch=simulator.git_branch
    )

    # build the image
    build_job_id = await simulation_service_slurm.submit_build_image_job(simulator_version=simulator)
    assert build_job_id is not None

    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_build = await simulation_service_slurm.get_slurm_job_status(slurmjobid=build_job_id)
        if slurm_job_build is not None and slurm_job_build.is_done():
            break
        await asyncio.sleep(5)

    assert slurm_job_build is not None
    assert slurm_job_build.is_done()
    assert slurm_job_build.job_id == build_job_id
    assert slurm_job_build.name.startswith(f"build-image-{latest_commit_hash}-")

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config={"param1": 5})
    parca_dataset = await database_service.get_or_insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    # run parca
    parca_job_id = await simulation_service_slurm.submit_parca_job(parca_dataset=parca_dataset)
    assert parca_job_id is not None

    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_parca = await simulation_service_slurm.get_slurm_job_status(slurmjobid=parca_job_id)
        if slurm_job_parca is not None and slurm_job_parca.is_done():
            break
        await asyncio.sleep(5)

    assert slurm_job_parca is not None
    assert slurm_job_parca.is_done()
    assert slurm_job_parca.job_id == parca_job_id
    assert slurm_job_parca.name.startswith(f"parca-{latest_commit_hash}-")

    # create new simulation instance by inserting it into the db (not yet submitted to hpc)
    simulation_request = EcoliSimulationRequest(
        simulator=simulator,
        parca_dataset_id=parca_dataset.database_id,
        variant_config={"named_parameters": {"param1": 0.5, "param2": 0.5}},
    )
    simulation = await database_service.insert_simulation(sim_request=simulation_request)

    # write test request (TODO: move this)
    await write_test_request(simulation=simulation)

    # actually submit the simulation to the hpc and return an indexable sim job id
    sim_job_id = await simulation_service_slurm.submit_ecoli_simulation_job(
        ecoli_simulation=simulation, simulation_database_service=database_service
    )
    assert sim_job_id is not None

    # poll for job status
    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_sim = await simulation_service_slurm.get_slurm_job_status(slurmjobid=sim_job_id)
        if slurm_job_sim is not None and slurm_job_sim.is_done():
            break
        await asyncio.sleep(5)

    assert slurm_job_sim is not None
    assert slurm_job_sim.is_done()
    assert slurm_job_sim.job_id == sim_job_id
    assert slurm_job_sim.name.startswith(f"sim-{latest_commit_hash}-")


# async def test_read_chunks():
#     pass
