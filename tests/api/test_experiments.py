import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import ExperimentRequest
from sms_api.simulation.simulation_service import SimulationServiceHpc


@pytest.mark.asyncio
async def test_run_fetch_simulation(
    base_router: str,
    experiment_request: ExperimentRequest,
    database_service: DatabaseService,
    simulation_service_slurm: SimulationServiceHpc,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/simulations", json=experiment_request.model_dump())
        response.raise_for_status()
        sim_response = response.json()
        db_id = sim_response["database_id"]

        fetch_response = await client.get(f"{base_router}/simulations/{db_id}")
        fetch_response.raise_for_status()
        assert fetch_response.json() == sim_response
