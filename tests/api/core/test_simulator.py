import datetime
from typing import cast

import pytest

import sms_api
import sms_api.api
from sms_api.api.client import Client
from sms_api.api.client.api.ecoli_sim.get_simulator_status import asyncio as get_simulator_status_async
from sms_api.api.client.api.ecoli_sim.get_simulator_versions import asyncio as get_simulator_versions_async
from sms_api.api.client.api.ecoli_sim.insert_simulator_version import asyncio as insert_simulator_version_async
from sms_api.api.client.models import HpcRun, HTTPValidationError, RegisteredSimulators
from sms_api.api.client.models.simulator import Simulator as SimulatorDto
from sms_api.api.client.models.simulator_version import SimulatorVersion as SimulatorVersionDto
from sms_api.api.client.types import UNSET
from sms_api.common.handlers.simulators import RepoUrl, verify_simulator_payload
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.models import JobStatus, JobType, Simulator, SimulatorVersion
from tests.fixtures.simulation_service_mocks import SimulationServiceMockCloneAndBuild


@pytest.mark.asyncio
async def test_insert_simulator_version(
    monkeypatch: pytest.MonkeyPatch,
    database_service: DatabaseServiceSQL,
    simulation_service_mock_clone_and_build: SimulationServiceMockCloneAndBuild,
    in_memory_api_client: Client,
) -> None:
    expected_commit_hash = "abc1234"
    expected_git_repo_url = "https://github.com/vivarium-collective/vEcoli"
    expected_git_branch = "messages"
    simulator_dto = SimulatorDto(
        git_commit_hash=expected_commit_hash, git_repo_url=expected_git_repo_url, git_branch=expected_git_branch
    )
    response: HTTPValidationError | SimulatorVersionDto | None = await insert_simulator_version_async(
        client=in_memory_api_client, body=simulator_dto
    )
    assert type(response) is SimulatorVersionDto
    returned_simulator_version_dto: SimulatorVersionDto = response
    assert type(returned_simulator_version_dto) is SimulatorVersionDto

    registered_simulators = await get_simulator_versions_async(client=in_memory_api_client)
    assert type(registered_simulators) is RegisteredSimulators
    assert len(registered_simulators.versions) == 1

    simulator_status = await get_simulator_status_async(
        client=in_memory_api_client, simulator_id=returned_simulator_version_dto.database_id
    )
    assert type(simulator_status) is HpcRun
    assert simulator_status.status == sms_api.api.client.models.job_status.JobStatus.RUNNING
    assert simulator_status.job_type == sms_api.api.client.models.job_type.JobType.BUILD_IMAGE
    assert simulator_status.ref_id == returned_simulator_version_dto.database_id

    # Verify that the build job was submitted (cloning now happens in the SBATCH script)
    created_at: datetime.datetime | None = None
    if returned_simulator_version_dto.created_at is not UNSET:
        created_at = cast(datetime.datetime, returned_simulator_version_dto.created_at)
    returned_simulator_version = SimulatorVersion(
        database_id=returned_simulator_version_dto.database_id,
        git_commit_hash=returned_simulator_version_dto.git_commit_hash,
        git_repo_url=returned_simulator_version_dto.git_repo_url,
        git_branch=returned_simulator_version_dto.git_branch,
        created_at=created_at,
    )
    assert simulation_service_mock_clone_and_build.submit_build_args == (returned_simulator_version,)

    # ensure the returned simulator version matches the expected values
    image_build_hpcrun = await database_service.get_hpcrun_by_slurmjobid(
        slurmjobid=simulation_service_mock_clone_and_build.expected_build_slurm_job_id
    )
    assert image_build_hpcrun is not None
    assert image_build_hpcrun.slurmjobid == simulation_service_mock_clone_and_build.expected_build_slurm_job_id
    assert image_build_hpcrun.ref_id == returned_simulator_version.database_id
    assert image_build_hpcrun.job_type == JobType.BUILD_IMAGE
    assert image_build_hpcrun.status == JobStatus.RUNNING
    assert image_build_hpcrun.start_time is not None
    assert image_build_hpcrun.end_time is None

    assert returned_simulator_version.git_commit_hash == expected_commit_hash
    assert returned_simulator_version.git_repo_url == expected_git_repo_url
    assert returned_simulator_version.git_branch == expected_git_branch
    assert returned_simulator_version.database_id == image_build_hpcrun.ref_id
    assert returned_simulator_version.created_at is not None

    # cleanup database entries
    await database_service.delete_hpcrun(hpcrun_id=image_build_hpcrun.database_id)
    await database_service.delete_simulator(simulator_id=returned_simulator_version.database_id)


def make_simulator(repo_url: str, branch: str) -> Simulator:
    return Simulator(
        git_commit_hash="1111223",
        git_repo_url=repo_url,
        git_branch=branch,
    )


@pytest.mark.parametrize(
    "repo_url,branch",
    [
        (RepoUrl.VECOLI_FORK_REPO_URL, "messages"),
        (RepoUrl.VECOLI_FORK_REPO_URL, "ccam-nextflow"),
        (RepoUrl.VECOLI_FORK_REPO_URL, "master"),
        (RepoUrl.VECOLI_PUBLIC_REPO_URL, "master"),
        (RepoUrl.VECOLI_PUBLIC_REPO_URL, "ptools_viz"),
    ],
)
def test_verify_simulator_payload_valid(repo_url: str, branch: str) -> None:
    simulator = make_simulator(repo_url, branch)

    # Should not raise
    verify_simulator_payload(simulator)


@pytest.mark.parametrize(
    "repo_url,branch,expected_branches",
    [
        (
            RepoUrl.VECOLI_FORK_REPO_URL,
            "dev",
            ["messages", "ccam-nextflow", "master"],
        ),
        (
            RepoUrl.VECOLI_PUBLIC_REPO_URL,
            "feature-x",
            ["master", "ptools_viz"],
        ),
    ],
)
def test_verify_simulator_payload_invalid_branch(repo_url: str, branch: str, expected_branches: list[str]) -> None:
    simulator = make_simulator(repo_url, branch)

    with pytest.raises(ValueError) as excinfo:
        verify_simulator_payload(simulator)

    msg = str(excinfo.value)
    assert branch in msg
    assert str(repo_url) in msg
    for b in expected_branches:
        assert b in msg


def test_verify_simulator_payload_unmatched_repo_url() -> None:
    """
    RepoUrl.VECOLI_PRIVATE_REPO_URL is not matched in the `match` statement,
    so verification should silently pass.
    """
    simulator = make_simulator(
        RepoUrl.VECOLI_PRIVATE_REPO_URL,
        "any-branch",
    )

    verify_simulator_payload(simulator)
