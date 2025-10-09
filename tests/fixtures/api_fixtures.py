import datetime
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from random import randint

import httpx
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport

from sms_api.api.client import Client
from sms_api.api.main import app
from sms_api.api.request_examples import base_simulation, ptools_analysis
from sms_api.config import REPO_ROOT, get_settings
from sms_api.data.models import ExperimentAnalysisRequest

# from sms_api.data.biocyc_service import BiocycService
from sms_api.latest_commit import write_latest_commit
from sms_api.simulation.hpc_utils import get_slurmjob_name
from sms_api.simulation.models import (
    EcoliSimulationDTO,
    ExperimentMetadata,
    ExperimentRequest,
    SimulationConfig,
)

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


@pytest_asyncio.fixture(scope="session")
async def analysis_request() -> ExperimentAnalysisRequest:
    return ptools_analysis


@pytest_asyncio.fixture(scope="session")
async def experiment_request() -> ExperimentRequest:
    return base_simulation


@pytest_asyncio.fixture(scope="session")
async def simulation_config() -> SimulationConfig:
    return SimulationConfig(
        experiment_id="pytest_fixture_config",
        sim_data_path="/pytest/kb/simData.cPickle",
        suffix_time=False,
        parca_options={"cpus": 3},
        generations=randint(1, 1000),  # noqa: S311
        max_duration=10800,
        initial_global_time=0,
        time_step=1,
        single_daughters=True,
        emitter="parquet",
        emitter_arg={"outdir": "/pytest/api_outputs"},
    )


@pytest_asyncio.fixture(scope="session")
async def ecoli_simulation() -> EcoliSimulationDTO:
    pytest_fixture = "pytest_fixture"
    db_id = -1
    return EcoliSimulationDTO(
        database_id=-1,
        name=pytest_fixture,
        config=SimulationConfig(
            experiment_id=pytest_fixture,
            sim_data_path="/pytest/kb/simData.cPickle",
            suffix_time=False,
            parca_options={"cpus": 3},
            generations=randint(1, 1000),  # noqa: S311
            max_duration=10800,
            initial_global_time=0,
            time_step=1,
            single_daughters=True,
            emitter="parquet",
            emitter_arg={"outdir": "/pytest/api_outputs"},
        ),
        metadata=ExperimentMetadata(root={"requester": f"{pytest_fixture}:{db_id}", "context": "pytest"}),
        last_updated=str(datetime.datetime.now()),
        job_name=get_slurmjob_name(experiment_id=pytest_fixture),
        job_id=randint(10000, 1000000),  # noqa: S311
    )


@pytest_asyncio.fixture(scope="session")
async def base_router() -> str:
    return "/v1/ecoli"
