import datetime
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from random import randint
from typing import NamedTuple

import httpx
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport

from sms_api.analysis.models import (
    AnalysisConfig,
    AnalysisDomain,
    ExperimentAnalysisRequest,
)
from sms_api.api import request_examples
from sms_api.api import request_examples as examples
from sms_api.api.client import Client
from sms_api.api.main import app
from sms_api.common.gateway.utils import generate_analysis_request
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.messaging.messaging_service_redis import MessagingServiceRedis
from sms_api.common.utils import get_uuid
from sms_api.config import REPO_ROOT, get_settings
from sms_api.dependencies import get_job_scheduler, set_job_scheduler

# from sms_api.data.biocyc_service import BiocycService
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.job_scheduler import JobScheduler
from sms_api.simulation.models import (
    ParcaDatasetRequest,
    ParcaOptions,
    Simulation,
    SimulationConfig,
    SimulationRequest,
    Simulator,
)
from sms_api.simulation.simulation_service import SimulationServiceHpc

ENV = get_settings()

# Default simulator repository configuration for tests
SIMULATOR_URL = "https://github.com/vivarium-collective/vEcoli"
SIMULATOR_BRANCH = "api-support"
SIMULATOR_COMMIT = "88c009d"


class SimulatorRepoInfo(NamedTuple):
    """Container for simulator repository information.

    Can be unpacked as tuple: url, branch, hash = repo_info
    """

    url: str
    branch: str
    commit_hash: str


@pytest_asyncio.fixture(scope="session")
async def simulator_repo_info() -> SimulatorRepoInfo:
    """Fixture providing the default simulator repository info for integration tests."""
    return SimulatorRepoInfo(
        url=SIMULATOR_URL,
        branch=SIMULATOR_BRANCH,
        commit_hash=SIMULATOR_COMMIT,
    )


@pytest_asyncio.fixture(scope="function")
async def local_base_url() -> str:
    return "http://testserver"


@pytest_asyncio.fixture(scope="function")
async def fastapi_app() -> FastAPI:
    return app


@pytest_asyncio.fixture(scope="session")
async def latest_commit_hash(simulator_repo_info: SimulatorRepoInfo) -> str:
    """Returns the commit hash from simulator_repo_info fixture."""
    return simulator_repo_info.commit_hash


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
    return Path(REPO_ROOT) / "tests" / "fixtures" / "configs" / "sms_multigen_analysis.json"


@pytest_asyncio.fixture(scope="session")
async def analysis_request() -> ExperimentAnalysisRequest:
    # return ptools_analysis
    return examples.analysis_multiseed_multigen


@pytest_asyncio.fixture(scope="function")
async def experiment_request(database_service: DatabaseServiceSQL) -> SimulationRequest:
    """Create a SimulationRequest with valid simulator_id and parca_dataset_id in the database."""
    import uuid

    # Use a unique commit hash for each test to avoid conflicts
    unique_commit_hash = f"test_{uuid.uuid4().hex[:7]}"

    # First insert the simulator
    simulator = await database_service.insert_simulator(
        git_commit_hash=unique_commit_hash,
        git_repo_url=examples.DEFAULT_SIMULATOR.git_repo_url,
        git_branch=examples.DEFAULT_SIMULATOR.git_branch,
    )

    # Then insert a parca dataset for this simulator
    parca_request = ParcaDatasetRequest(
        simulator_version=simulator,
        parca_config=ParcaOptions(),
    )
    parca_dataset = await database_service.insert_parca_dataset(
        parca_dataset_request=parca_request,
    )

    # Return a SimulationRequest with the valid IDs
    exp_id = f"test-{uuid.uuid4()!s}"
    return SimulationRequest(
        simulation_config_filename="api_simulation_default_with_profile.json",
        simulator_id=simulator.database_id,
        parca_dataset_id=parca_dataset.database_id,
        experiment_id=f"{exp_id}",
        config=SimulationConfig(
            experiment_id=f"{exp_id}",
            analysis_options=examples.analysis_options_omics(n_tp=7),
        ),
    )


@pytest_asyncio.fixture(scope="session")
async def parca_options() -> ParcaOptions:
    return ParcaOptions()


@pytest_asyncio.fixture(scope="session")
async def simulation_config(parca_options: ParcaOptions) -> SimulationConfig:
    return SimulationConfig(
        experiment_id="pytest_fixture_config",
        #     sim_data_path="/pytest/kb/simData.cPickle",
        #     suffix_time=False,
        #     parca_options=parca_options,
        #     generations=randint(1, 1000),
        #     max_duration=10800,
        #     initial_global_time=0,
        #     time_step=1,
        #     single_daughters=True,
        #     emitter="parquet",
        #     emitter_arg={"outdir": "/pytest/api_outputs"},
    )


@pytest_asyncio.fixture(scope="session")
async def ecoli_simulation(parca_options: ParcaOptions) -> Simulation:
    pytest_fixture = "pytest_fixture"
    return Simulation(
        database_id=-1,
        simulator_id=1,
        parca_dataset_id=1,
        experiment_id=pytest_fixture,
        simulation_config_filename="api_simulation_default_with_profile.json",
        config=SimulationConfig(
            experiment_id=pytest_fixture,
            # sim_data_path="/pytest/kb/simData.cPickle",
            # suffix_time=False,
            # parca_options=parca_options,
            # generations=randint(1, 1000),
            # max_duration=10800,
            # initial_global_time=0,
            # time_step=1,
            # single_daughters=True,
            # emitter="parquet",
            # emitter_arg={"outdir": "/pytest/api_outputs"},
        ),
        last_updated=str(datetime.datetime.now()),
        job_id=randint(10000, 1000000),
    )


@pytest_asyncio.fixture(scope="session")
async def base_router() -> str:
    return "/api/v1"


@pytest_asyncio.fixture(scope="session")
async def ptools_analysis_request() -> ExperimentAnalysisRequest:
    return examples.analysis_ptools


@pytest_asyncio.fixture(scope="session")
async def analysis_request_config(ptools_analysis_request: ExperimentAnalysisRequest) -> AnalysisConfig:
    uid: str = get_uuid(scope="test_analysis")
    return ptools_analysis_request.to_config(analysis_name=uid, env=ENV)


@pytest_asyncio.fixture(scope="function")
async def analysis_request_ptools() -> ExperimentAnalysisRequest:
    return request_examples.analysis_ptools


@pytest_asyncio.fixture(scope="function")
async def analysis_request_base() -> ExperimentAnalysisRequest:
    return generate_analysis_request(
        experiment_id="publication_multiseed_multigen-a7ae0b4e093e20e6_1762830572273",
        requested_configs=[AnalysisDomain.MULTIGENERATION, AnalysisDomain.MULTISEED],
    )


@pytest_asyncio.fixture(scope="function")
async def workflow_config() -> SimulationConfig:
    return SimulationConfig(
        experiment_id="pytest_fixture",
        generations=randint(1, 5),
        # n_init_sims=randint(1, 5)
    )


@pytest_asyncio.fixture
async def workflow_request_payload(
    simulation_config: SimulationConfig, simulation_service_slurm: SimulationServiceHpc
) -> SimulationRequest:
    """Minimal simulation request payload for testing."""
    latest_hash = await simulation_service_slurm.get_latest_commit_hash(
        git_repo_url=SIMULATOR_URL, git_branch=SIMULATOR_BRANCH
    )
    return SimulationRequest(
        simulator=Simulator(git_commit_hash=latest_hash, git_repo_url=SIMULATOR_URL, git_branch=SIMULATOR_BRANCH),
        config=simulation_config,
        experiment_id=f"test-{uuid.uuid4()!s}",
        simulation_config_filename="api_simulation_default_with_profile.json",
    )


@pytest_asyncio.fixture(scope="function")
async def job_scheduler(database_service: DatabaseServiceSQL) -> AsyncGenerator[JobScheduler, None]:
    """Fixture that starts the JobScheduler for integration tests.

    The JobScheduler polls SLURM for job status updates and updates the database.
    This fixture starts the polling loop and stops it when the test completes.
    """
    # Save existing job scheduler if any
    saved_scheduler = get_job_scheduler()

    # Create messaging service (mock - we don't need Redis for status polling)
    messaging_service = MessagingServiceRedis()

    # Create and configure the JobScheduler
    slurm_service = SlurmService()
    scheduler = JobScheduler(
        messaging_service=messaging_service,
        database_service=database_service,
        slurm_service=slurm_service,
    )
    set_job_scheduler(scheduler)

    # Start polling with a short interval for tests
    await scheduler.start_polling(interval_seconds=5)

    yield scheduler

    # Cleanup
    await scheduler.stop_polling()
    set_job_scheduler(saved_scheduler)
