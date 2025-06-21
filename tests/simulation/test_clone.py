import pytest

from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.simulation_service import SimulationService

main_branch = "master"
repo_url = "https://github.com/CovertLab/vEcoli"
latest_commit_hash = '96bb7a2'


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_latest_repo_installed(ssh_service: SSHService) -> None:
    return_code, stdout, stderr = await ssh_service.run_command(f"git ls-remote -h {repo_url} {main_branch}")
    assert return_code == 0
    assert stdout.strip("\n").split()[0][:7] == latest_commit_hash


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_clone(simulation_service_slurm: SimulationService) -> None:
    with pytest.raises(ValueError):
        await simulation_service_slurm.clone_repository_if_needed(
            git_commit_hash="invalid_commit_hash", git_repo_url=repo_url, git_branch=main_branch
        )

    await simulation_service_slurm.clone_repository_if_needed(
        git_commit_hash=latest_commit_hash, git_repo_url=repo_url, git_branch=main_branch
    )
