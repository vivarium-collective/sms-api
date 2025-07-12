from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from sms_api.dependencies import get_simulation_service, set_simulation_service
from sms_api.simulation.simulation_service import SimulationServiceHpc
from tests.fixtures.simulation_service_mocks import SimulationServiceMockCloneAndBuild


@pytest_asyncio.fixture(scope="function")
async def simulation_service_slurm() -> AsyncGenerator[SimulationServiceHpc, None]:
    simulation_service = SimulationServiceHpc()
    saved_simulation_service = get_simulation_service()
    set_simulation_service(simulation_service)

    yield simulation_service

    await simulation_service.close()
    set_simulation_service(saved_simulation_service)


@pytest.fixture
def expected_build_slurm_job_id() -> int:
    """
    Fixture to provide the expected Slurm job ID for build jobs.
    """
    return 999


@pytest.fixture(scope="function")
def simulation_service_mock_clone_and_build(
    expected_build_slurm_job_id: int,
) -> Generator[SimulationServiceMockCloneAndBuild, None, None]:
    """
    Fixture to provide a mock simulation service that clones a repository and submits a build job.
    """
    saved_simulation_service = get_simulation_service()
    simulation_service_mock_clone_and_build = SimulationServiceMockCloneAndBuild(
        expected_build_slurm_job_id=expected_build_slurm_job_id
    )
    set_simulation_service(simulation_service_mock_clone_and_build)

    yield simulation_service_mock_clone_and_build

    set_simulation_service(saved_simulation_service)
