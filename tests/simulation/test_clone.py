import pytest

from sms_api.config import get_settings
from sms_api.simulation.simulation_service import SimulationService

main_branch = "messages"
repo_url = "https://github.com/vivarium-collective/vEcoli"


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_clone(simulation_service_remote: SimulationService, latest_commit_hash: str) -> None:
    await simulation_service_remote.clone_repository_if_needed(
        git_commit_hash=latest_commit_hash, git_repo_url=repo_url, git_branch=main_branch
    )
