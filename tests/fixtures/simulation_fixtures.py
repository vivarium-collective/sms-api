from collections.abc import AsyncGenerator

import pytest_asyncio

from sms_api.dependencies import get_simulation_service, set_simulation_service
from sms_api.simulation.simulation_service import SimulationServiceHpc
from tests.fixtures.simulation_service_mock import SimulationServiceMock


@pytest_asyncio.fixture(scope="function")
async def simulation_service_mock() -> AsyncGenerator[SimulationServiceMock, None]:
    simulation_service = SimulationServiceMock()
    saved_simulation_service = get_simulation_service()
    set_simulation_service(simulation_service)

    yield simulation_service

    await simulation_service.close()
    set_simulation_service(saved_simulation_service)


@pytest_asyncio.fixture(scope="function")
async def simulation_service_slurm() -> AsyncGenerator[SimulationServiceHpc, None]:
    simulation_service = SimulationServiceHpc()
    saved_simulation_service = get_simulation_service()
    set_simulation_service(simulation_service)

    yield simulation_service

    await simulation_service.close()
    set_simulation_service(saved_simulation_service)
