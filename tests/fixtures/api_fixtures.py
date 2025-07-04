from collections.abc import AsyncGenerator

import pytest_asyncio
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.api.routers import core
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.simulation_service import SimulationServiceHpc


@pytest_asyncio.fixture(scope="function")
async def local_base_url() -> str:
    return "http://testserver"


@pytest_asyncio.fixture(scope="function")
async def fastapi_app(
    database_service: DatabaseService, simulation_service_slurm: SimulationServiceHpc
) -> AsyncGenerator[FastAPI, None]:
    # app.dependency_overrides[get_database_service] = lambda: database_service
    # app.dependency_overrides[get_simulation_service] = lambda: simulation_service_slurm
    yield app


@pytest_asyncio.fixture(scope="function")
async def core_router(
    database_service: DatabaseService, simulation_service_slurm: SimulationServiceHpc
) -> AsyncGenerator[APIRouter, None]:
    yield core.config.router


@pytest_asyncio.fixture
async def app_client(fastapi_app: FastAPI, local_base_url: str) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url=local_base_url) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def latest_commit_hash(simulation_service_slurm: SimulationServiceHpc) -> AsyncGenerator[str, None]:
    yield await simulation_service_slurm.get_latest_commit_hash()
