import asyncio
import time

import pytest

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.models import ParcaDatasetRequest, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationServiceHpc

main_branch = "messages"
repo_url = "https://github.com/vivarium-collective/vEcoli"


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_parca(
    slurm_service_remote: SlurmService,
    simulation_service_remote: SimulationServiceHpc,
    database_service: DatabaseServiceSQL,
    latest_commit_hash: str,
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
    await simulation_service_remote.clone_repository_if_needed(
        git_commit_hash=simulator.git_commit_hash, git_repo_url=simulator.git_repo_url, git_branch=simulator.git_branch
    )

    # build the image
    job_id = await simulation_service_remote.submit_build_image_job(simulator_version=simulator)
    assert job_id is not None

    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_build = await slurm_service_remote.get_job_status(slurmjobid=job_id)
        if slurm_job_build is not None and slurm_job_build.is_done():
            break
        await asyncio.sleep(5)

    assert slurm_job_build is not None
    assert slurm_job_build.is_done()
    assert slurm_job_build.job_id == job_id
    assert slurm_job_build.name.startswith(f"build-image-{latest_commit_hash}-")

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config={"param1": 5})
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    # run parca
    job_id = await simulation_service_remote.submit_parca_job(parca_dataset=parca_dataset)
    assert job_id is not None

    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_parca = await slurm_service_remote.get_job_status(slurmjobid=job_id)
        if slurm_job_parca is not None and slurm_job_parca.is_done():
            break
        await asyncio.sleep(5)

    assert slurm_job_parca is not None
    assert slurm_job_parca.is_done()
    assert slurm_job_parca.job_id == job_id
    assert slurm_job_parca.name.startswith(f"parca-{latest_commit_hash}-")
