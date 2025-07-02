import asyncio
import time

import pytest

from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.simulation_database import SimulationDatabaseService
from sms_api.simulation.simulation_service import SimulationServiceHpc

main_branch = "master"
repo_url = "https://github.com/CovertLab/vEcoli"
latest_commit_hash = "d24e988"


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_latest_repo_installed(ssh_service: SSHService) -> None:
    return_code, stdout, stderr = await ssh_service.run_command(f"git ls-remote -h {repo_url} {main_branch}")
    assert return_code == 0
    assert stdout.strip("\n").split()[0][:7] == latest_commit_hash


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_build(
    simulation_service_slurm: SimulationServiceHpc, database_service: SimulationDatabaseService
) -> None:
    # insert the latest commit into the database
    simulator = await database_service.insert_simulator(
        git_commit_hash=latest_commit_hash, git_repo_url=repo_url, git_branch=main_branch
    )

    # clone the repository if needed
    await simulation_service_slurm.clone_repository_if_needed(
        git_commit_hash=simulator.git_commit_hash, git_repo_url=simulator.git_repo_url, git_branch=simulator.git_branch
    )

    # build the image
    job_id = await simulation_service_slurm.submit_build_image_job(simulator_version=simulator)
    assert job_id is not None

    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job = await simulation_service_slurm.get_slurm_job_status(slurmjobid=job_id)
        if slurm_job is not None and slurm_job.is_done():
            break
        await asyncio.sleep(5)

    assert slurm_job is not None
    assert slurm_job.is_done()
    assert slurm_job.job_id == job_id
    assert slurm_job.name.startswith(f"build-image-{latest_commit_hash}-")
