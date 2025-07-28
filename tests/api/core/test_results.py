import pytest

import sms_api
from sms_api.api.client import Client
from sms_api.api.client.api.simulations_v_ecoli.get_simulation_results import asyncio as get_results_sync
from sms_api.simulation.database_service import DatabaseServiceSQL
from tests.fixtures.simulation_service_mocks import SimulationServiceMockParca


@pytest.mark.asyncio
async def test_get_results(
    in_memory_api_client: Client,
) -> None:
    bulk_results = await get_results_sync(client=in_memory_api_client, body=["bulk"])
    print(bulk_results)