import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.models import ExperimentRequest, SimulationRequest
from sms_api.simulation.simulation_service import SimulationServiceHpc


@pytest.mark.asyncio
async def test_list_simulations(
    experiment_request: SimulationRequest, database_service: DatabaseServiceSQL, ssh_session_service: SSHSessionService
) -> None:
    n = 3
    inserted_sims = []
    for _ in range(n):
        sim_i = await database_service.insert_simulation(sim_request=experiment_request)
        inserted_sims.append(sim_i.model_dump())
    all_sims = await database_service.list_simulations()
    assert len(inserted_sims) == n
    assert len(inserted_sims) == len(all_sims)


@pytest.mark.asyncio
async def test_get_simulation(database_service: DatabaseServiceSQL, experiment_request: SimulationRequest) -> None:
    sim_i = await database_service.insert_simulation(experiment_request)

    fetched_i = await database_service.get_simulation(simulation_id=sim_i.database_id)
    assert fetched_i.model_dump() == sim_i.model_dump()  # type: ignore[union-attr]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_simulation_status(
    base_router: str,
    workflow_request_payload: SimulationRequest,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        sim_response = await client.post(f"{base_router}/simulations", json=workflow_request_payload.model_dump())
        sim_response.raise_for_status()
        sim_response = sim_response.json()

        await asyncio.sleep(3)

        status_response = await client.get(f"{base_router}/simulations/{sim_response['database_id']}/status")
        status_response.raise_for_status()
        status_response = status_response.json()
        assert list(status_response.keys()) == ["id", "status"]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_simulation_log(
    base_router: str,
    experiment_request: ExperimentRequest,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        sim_response = await client.post(f"{base_router}/simulations", json=experiment_request.model_dump())
        sim_response.raise_for_status()
        sim_response = sim_response.json()

        await asyncio.sleep(3)

        status_response = await client.post(f"{base_router}/simulations/{sim_response['database_id']}/log")
        status_response.raise_for_status()

        assert isinstance(status_response.text, str)


@pytest.mark.skipif(
    len(get_settings().slurm_submit_key_path) == 0,
    reason="slurm ssh key file not supplied",
)
@pytest.mark.asyncio
async def test_run_simulation_e2e(
    base_router: str,
    workflow_request_payload: SimulationRequest,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    """E2E test: POST /api/v1/simulations to launch a simulation workflow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/simulations", json=workflow_request_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        sim_response = response.json()

        # Verify response contains expected Simulation fields
        assert "database_id" in sim_response
        assert "simulator_id" in sim_response
        assert "parca_dataset_id" in sim_response
        assert "config" in sim_response
        assert sim_response["config"]["experiment_id"] == workflow_request_payload.config.experiment_id


@pytest.mark.skipif(
    len(get_settings().slurm_submit_key_path) == 0,
    reason="slurm ssh key file not supplied",
)
@pytest.mark.asyncio
async def test_run_and_get_simulation_e2e(
    base_router: str,
    workflow_request_payload: SimulationRequest,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    """E2E test: POST then GET simulation to verify persistence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create simulation
        post_response = await client.post(f"{base_router}/simulations", json=workflow_request_payload)
        assert post_response.status_code == 200

        created_sim = post_response.json()
        db_id = created_sim["database_id"]

        # Fetch the created simulation
        get_response = await client.get(f"{base_router}/simulations/{db_id}")
        assert get_response.status_code == 200

        fetched_sim = get_response.json()
        assert fetched_sim["database_id"] == db_id
        assert fetched_sim["config"]["experiment_id"] == workflow_request_payload.config.experiment_id
