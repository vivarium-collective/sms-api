from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.dependencies import get_database_service, set_database_service
from sms_api.simulation.models import Simulation, SimulationConfig
from sms_api.simulation.observable_reader import ObservableInfo, StoreIndex

BASE = "/api/v1"


class _FakeDB:
    def __init__(self, sim: Simulation | None) -> None:
        self._sim = sim

    async def get_simulation(self, simulation_id: int) -> Simulation | None:
        return self._sim


def _sim(experiment_id: str = "exp-abc") -> Simulation:
    # Construct a minimal valid Simulation with all required fields.
    return Simulation(
        database_id=49,
        simulator_id=1,
        parca_dataset_id=1,
        experiment_id=experiment_id,
        simulation_config_filename="api_simulation_default.json",
        config=SimulationConfig(experiment_id=experiment_id),
    )


@asynccontextmanager
async def _client() -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.asyncio
async def test_observables_index_ok(monkeypatch) -> None:
    saved = get_database_service()
    set_database_service(_FakeDB(_sim()))
    monkeypatch.setattr(
        "sms_api.api.routers.sms.list_observables",
        lambda uri: StoreIndex(store="zarr", observables=[ObservableInfo("mass", ["time"], [3])]),
    )
    try:
        async with _client() as c:
            r = await c.get(f"{BASE}/simulations/49/observables/index")
        assert r.status_code == 200
        body = r.json()
        assert body["experiment_id"] == "exp-abc"
        assert body["store"] == "zarr"
        assert body["observables"][0]["name"] == "mass"
    finally:
        set_database_service(saved)


@pytest.mark.asyncio
async def test_observables_index_404_when_missing(monkeypatch) -> None:
    saved = get_database_service()
    set_database_service(_FakeDB(None))
    try:
        async with _client() as c:
            r = await c.get(f"{BASE}/simulations/999/observables/index")
        assert r.status_code == 404
    finally:
        set_database_service(saved)
