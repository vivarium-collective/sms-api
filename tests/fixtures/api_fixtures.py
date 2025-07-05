import os
from pathlib import Path

import pytest_asyncio
from fastapi import FastAPI

from sms_api.api.main import app
from sms_api.latest_commit import write_latest_commit


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
    latest_commit_path = Path("assets/latest_commit.txt")
    if not os.path.exists(latest_commit_path):
        await write_latest_commit()
    with open(latest_commit_path) as fp:
        latest_commit = fp.read()
    return latest_commit
