import asyncio
import time

import pytest

from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import EcoliSimulationRequest, JobType, ParcaDatasetRequest, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationServiceHpc

main_branch = "master"
repo_url = "https://github.com/CovertLab/vEcoli"


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_latest_repo_installed(ssh_service: SSHService, latest_commit_hash: str) -> None:
    return_code, stdout, stderr = await ssh_service.run_command(f"git ls-remote -h {repo_url} {main_branch}")
    assert return_code == 0
    assert stdout.strip("\n").split()[0][:7] == latest_commit_hash


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_simulate(
    simulation_service_slurm: SimulationServiceHpc, database_service: DatabaseService, latest_commit_hash: str
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
    parca_slurmjobid = await simulation_service_slurm.submit_parca_job(parca_dataset=parca_dataset)
    assert parca_slurmjobid is not None

    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_parca = await simulation_service_slurm.get_slurm_job_status(slurmjobid=parca_slurmjobid)
        if slurm_job_parca is not None and slurm_job_parca.is_done():
            break
        await asyncio.sleep(5)

    assert slurm_job_parca is not None
    assert slurm_job_parca.is_done()
    assert slurm_job_parca.job_id == parca_slurmjobid
    assert slurm_job_parca.name.startswith(f"parca-{latest_commit_hash}-")

    simulation_request = EcoliSimulationRequest(
        simulator=simulator,
        parca_dataset_id=parca_dataset.database_id,
        variant_config={"named_parameters": {"param1": 0.5, "param2": 0.5}},
    )
    simulation = await database_service.insert_simulation(sim_request=simulation_request)

    sim_slurmjobid = await simulation_service_slurm.submit_ecoli_simulation_job(
        ecoli_simulation=simulation, database_service=database_service
    )
    assert sim_slurmjobid is not None

    hpcrun = await database_service.insert_hpcrun(
        slurmjobid=sim_slurmjobid, job_type=JobType.SIMULATION, ref_id=simulation.database_id
    )
    assert hpcrun is not None
    assert hpcrun.slurmjobid == sim_slurmjobid
    assert hpcrun.job_type == JobType.SIMULATION
    assert hpcrun.ref_id == simulation.database_id

    start_time = time.time()
    while start_time + 60 > time.time():
        sim_slurmjob = await simulation_service_slurm.get_slurm_job_status(slurmjobid=sim_slurmjobid)
        if sim_slurmjob is not None and sim_slurmjob.is_done():
            break
        await asyncio.sleep(5)

    assert sim_slurmjob is not None
    assert sim_slurmjob.is_done()
    assert sim_slurmjob.job_id == sim_slurmjobid
    assert sim_slurmjob.name.startswith(f"sim-{latest_commit_hash}-")
