import pytest
from fastapi import BackgroundTasks

from sms_api.simulation.core_handlers import upload_simulator
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.models import JobStatus, JobType
from tests.fixtures.simulation_service_mocks import SimulationServiceMockCloneAndBuild


@pytest.mark.asyncio
async def test_upload_simulator_handler(
    database_service: DatabaseServiceSQL, simulation_service_mock_clone_and_build: SimulationServiceMockCloneAndBuild
) -> None:
    """
    Test the upload_simulator handler to ensure it correctly clones a repository and submits a build job.
    the simulation_service_slurm fixture is used to mock the SimulationService.
    the database_service is not mocked, but it is assumed to be a real instance connected to a test database.
    """
    expected_commit_hash = "abc1234"
    expected_git_repo_url = "https://github.com/vivarium-collective/vEcoli"
    expected_git_branch = "messages"

    background_tasks = BackgroundTasks()
    returned_simulator_version = await upload_simulator(
        commit_hash=expected_commit_hash,
        git_repo_url=expected_git_repo_url,
        git_branch=expected_git_branch,
        simulation_service_slurm=simulation_service_mock_clone_and_build,
        database_service=database_service,
        background_tasks=background_tasks,
    )
    await background_tasks()

    # verify that background tasks were executed
    assert simulation_service_mock_clone_and_build.clone_repo_args == (
        expected_commit_hash,
        expected_git_repo_url,
        expected_git_branch,
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
