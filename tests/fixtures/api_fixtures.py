import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport

from sms_api.api.client import Client
from sms_api.api.main import app
from sms_api.config import REPO_ROOT, get_settings
from sms_api.data.models import AnalysisRequest

# from sms_api.data.biocyc_service import BiocycService
from sms_api.latest_commit import write_latest_commit

# @pytest_asyncio.fixture(scope="function")
# async def biocyc_service() -> BiocycService:
#     return BiocycService()


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


@pytest_asyncio.fixture(scope="session")
async def workspace_image_hash() -> str:
    return "079c43c"


@pytest_asyncio.fixture(scope="session")
async def analysis_config_path() -> Path:
    return Path(REPO_ROOT) / "assets" / "sms_multigen_analysis.json"


def unique_id() -> str:
    return str(uuid.uuid4())


@pytest_asyncio.fixture(scope="session")
async def analysis_request() -> AnalysisRequest:
    return AnalysisRequest(**{
        "experiment_id": "sms_multigeneration",
        "analysis_name": f"sms_pytest_{unique_id()}",
        "single": {},
        "multidaughter": {},
        "multigeneration": {
            "replication": {},
            "ribosome_components": {},
            "ribosome_crowding": {},
            "ribosome_production": {},
            "ribosome_usage": {},
            "rna_decay_03_high": {},
        },
        "multiseed": {"protein_counts_validation": {}, "ribosome_spacing": {}, "subgenerational_expression_table": {}},
        "multivariant": {
            "average_monomer_counts": {},
            "cell_mass": {},
            "doubling_time_hist": {"skip_n_gens": 1},
            "doubling_time_line": {},
        },
        "multiexperiment": {},
    })
