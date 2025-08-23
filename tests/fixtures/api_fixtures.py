import os
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport

from sms_api.api.client import Client
from sms_api.api.main import app
from sms_api.config import get_settings
from sms_api.data.biocyc_service import BiocycService
from sms_api.latest_commit import write_latest_commit


@pytest_asyncio.fixture(scope="function")
async def biocyc_service() -> BiocycService:
    return BiocycService()


@pytest_asyncio.fixture(scope="function")
async def local_base_url() -> str:
    return "http://testserver"


@pytest_asyncio.fixture(scope="function")
async def fastapi_app() -> FastAPI:
    # app.dependency_overrides[get_database_service] = lambda: database_service
    # app.dependency_overrides[get_simulation_service] = lambda: simulation_service_slurm
    return app


@pytest_asyncio.fixture(scope="session")
async def latest_commit_hash() -> str:
    assets_dir = Path(get_settings().assets_dir)
    latest_commit_path = assets_dir / "simulation" / "model" / "latest_commit.txt"
    if not os.path.exists(latest_commit_path):
        await write_latest_commit()
    with open(latest_commit_path) as fp:
        latest_commit = fp.read()
    return latest_commit.strip()


@pytest_asyncio.fixture(scope="function")
async def in_memory_api_client() -> AsyncGenerator[Client, None]:
    transport = ASGITransport(app=app)
    async_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = Client(base_url="http://testserver", raise_on_unexpected_status=True)
    client.set_async_httpx_client(async_client)
    yield client
    await async_client.aclose()
