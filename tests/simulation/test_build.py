import asyncio
import time

import pytest

from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.dependencies import get_ssh_session_service
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.simulation_service import SimulationServiceHpc
from tests.fixtures.api_fixtures import SimulatorRepoInfo


@pytest.mark.skip(reason="doesn't matter if this is the latest commit")
@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_latest_repo_installed(
    ssh_session_service: SSHSessionService, simulator_repo_info: SimulatorRepoInfo
) -> None:
    repo_url, main_branch, commit_hash = simulator_repo_info
    async with ssh_session_service.session() as ssh:
        return_code, stdout, stderr = await ssh.run_command(f"git ls-remote -h {repo_url} {main_branch}")
    assert return_code == 0
    assert stdout.strip("\n").split()[0][:7] == commit_hash


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_build(
    simulation_service_slurm: SimulationServiceHpc,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    repo_url, main_branch, commit_hash = simulator_repo_info

    # insert the latest commit into the database
    simulator = await database_service.insert_simulator(
        git_commit_hash=commit_hash, git_repo_url=repo_url, git_branch=main_branch
    )

    # Use single SSH session for job submission and polling
    async with get_ssh_session_service().session() as ssh:
        # Submit build job (which now includes cloning the repository)
        job_id = await simulation_service_slurm.submit_build_image_job(simulator_version=simulator, ssh=ssh)
        assert job_id is not None

        start_time = time.time()
        while start_time + 60 > time.time():
            slurm_job = await simulation_service_slurm.get_slurm_job_status(slurmjobid=job_id, ssh=ssh)
            if slurm_job is not None and slurm_job.is_done():
                break
            await asyncio.sleep(5)

        assert slurm_job is not None
        assert slurm_job.is_done()
        assert slurm_job.job_id == job_id
        assert slurm_job.name.startswith(f"build-image-{commit_hash}-")
