"""AWS Batch Integration Tests (Mock Mode) - Full end-user e2e workflow.

Mirrors test_batch_workflow.py but uses MockAwsBatchService instead of real AWS.
Always runs — no AWS credentials or BATCH_JOB_QUEUE required.

Exercises the complete end-user workflow through the gateway API endpoints:
1. POST /simulations       — submit a simulation
2. GET  /simulations/{id}  — retrieve the simulation record
3. GET  /simulations/{id}/status — poll job status until completion
4. GET  /simulations       — list all simulations (verify ours appears)
5. POST /simulations/{id}/data   — download simulation output data (tar.gz)

Everything is real (FastAPI routing, handler logic, SimulationServiceBatch
orchestration, DatabaseServiceSQL with Postgres testcontainer) except:
- AwsBatchService boto3 calls (mocked via MockAwsBatchService)
- SSH calls for config reads and data retrieval (mocked)

Run with: uv run pytest tests/integration/test_batch_workflow_mock.py -v -s

Prerequisites:
- Docker running (for Postgres testcontainer)
"""

import json
import random
import string
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.models import JobStatus
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.models import (
    JobType,
    ParcaDatasetRequest,
    ParcaOptions,
    SimulationConfig,
    SimulationRequest,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service_batch import SimulationServiceBatch
from tests.fixtures.api_fixtures import SimulatorRepoInfo
from tests.fixtures.simulation_service_mocks import MockAwsBatchService

TEST_EXPERIMENT_ID = "test_batch_mock_integration"

API_ROUTER = "/api/v1"

CONFIG_TEMPLATE = json.dumps({
    "experiment_id": "EXPERIMENT_ID_PLACEHOLDER",
    "generations": 1,
    "n_init_sims": 1,
    "parca_options": {"cpus": 1},
    "analysis_options": {},
    "sim_data_path": "HPC_SIM_BASE_PATH_PLACEHOLDER/default/kb/simData.cPickle",
})

# Fake output files that the mocked SSH "find" command returns.
# These simulate what would exist on HPC after a completed simulation.
FAKE_OUTPUT_FILES = [
    "mass_fraction_summary.tsv",
    "growth_rate.tsv",
    "rnap_counts.csv",
]


# =============================================================================
# Helpers
# =============================================================================


async def get_or_create_simulator(
    database_service: DatabaseServiceSQL, repo_info: SimulatorRepoInfo
) -> SimulatorVersion:
    """Get or create simulator entry in database."""
    for _simulator in await database_service.list_simulators():
        if (
            _simulator.git_commit_hash == repo_info.commit_hash
            and _simulator.git_repo_url == repo_info.url
            and _simulator.git_branch == repo_info.branch
        ):
            return _simulator

    return await database_service.insert_simulator(
        git_commit_hash=repo_info.commit_hash, git_repo_url=repo_info.url, git_branch=repo_info.branch
    )


async def get_or_create_parca_dataset(database_service: DatabaseServiceSQL, simulator: SimulatorVersion) -> int:
    """Get or create parca dataset for this simulator."""
    parca_datasets = await database_service.list_parca_datasets()
    for parca in parca_datasets:
        if parca.parca_dataset_request.simulator_version.database_id == simulator.database_id:
            return parca.database_id

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=ParcaOptions())
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)
    return parca_dataset.database_id


@asynccontextmanager
async def _api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def _build_mock_ssh_service(
    run_command_side_effect: Any | None = None,
) -> tuple[AsyncMock, AsyncMock]:
    """Create a mock SSH service with configurable run_command behavior.

    Args:
        run_command_side_effect: If provided, used as side_effect for run_command.
            If None, returns (0, CONFIG_TEMPLATE, "") for all calls.
    """
    mock_ssh = AsyncMock()
    if run_command_side_effect is not None:
        mock_ssh.run_command.side_effect = run_command_side_effect
    else:
        mock_ssh.run_command.return_value = (0, CONFIG_TEMPLATE, "")
    mock_ssh.scp_download = AsyncMock()

    @asynccontextmanager
    async def _mock_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_ssh

    mock_ssh_service = AsyncMock()
    mock_ssh_service.session = _mock_session
    return mock_ssh_service, mock_ssh


# =============================================================================
# Service-level tests (steps 1-3): exercise SimulationServiceBatch directly
# =============================================================================


@pytest.mark.asyncio
async def test_1_build_image(
    simulation_service_batch_mock: SimulationServiceBatch,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 1: Submit Docker image build job to mocked AWS Batch."""
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    job_id = await simulation_service_batch_mock.submit_build_image_job(simulator_version=simulator)
    assert job_id is not None

    await database_service.insert_hpcrun(
        external_job_id=job_id,
        job_backend="batch",
        job_type=JobType.BUILD_IMAGE,
        ref_id=simulator.database_id,
        correlation_id=f"build-{simulator.git_commit_hash}",
    )

    status = await simulation_service_batch_mock.get_job_status(job_id)
    assert status is not None
    assert status.status == JobStatus.COMPLETED

    mock_batch: MockAwsBatchService = simulation_service_batch_mock._batch_service  # type: ignore[assignment]
    assert len(mock_batch.submitted_jobs) == 1
    assert mock_batch.submitted_jobs[0]["job_name"] == f"build-image-{simulator.git_commit_hash}"


@pytest.mark.asyncio
async def test_2_run_parca(
    simulation_service_batch_mock: SimulationServiceBatch,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 2: Submit parca parameter calculator job to mocked AWS Batch."""
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=ParcaOptions())
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    job_id = await simulation_service_batch_mock.submit_parca_job(parca_dataset=parca_dataset)
    assert job_id is not None

    await database_service.insert_hpcrun(
        external_job_id=job_id,
        job_backend="batch",
        job_type=JobType.PARCA,
        ref_id=parca_dataset.database_id,
        correlation_id=f"parca-{simulator.git_commit_hash}-{parca_dataset.database_id}",
    )

    status = await simulation_service_batch_mock.get_job_status(job_id)
    assert status is not None
    assert status.status == JobStatus.COMPLETED

    mock_batch: MockAwsBatchService = simulation_service_batch_mock._batch_service  # type: ignore[assignment]
    assert len(mock_batch.submitted_jobs) == 1
    assert mock_batch.submitted_jobs[0]["job_name"].startswith("parca-")


@pytest.mark.asyncio
async def test_3_run_simulation(
    simulation_service_batch_mock: SimulationServiceBatch,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 3: Submit simulation job to mocked AWS Batch."""
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)
    parca_dataset_id = await get_or_create_parca_dataset(database_service, simulator)

    simulation_request = SimulationRequest(
        experiment_id=TEST_EXPERIMENT_ID,
        simulation_config_filename="api_simulation_default_with_profile.json",
        simulator_id=simulator.database_id,
        parca_dataset_id=parca_dataset_id,
        config=SimulationConfig(experiment_id=TEST_EXPERIMENT_ID),
    )
    simulation = await database_service.insert_simulation(sim_request=simulation_request)

    random_string = "".join(random.choices(string.hexdigits, k=7))
    correlation_id = f"batch-sim-{simulator.git_commit_hash}-{random_string}"

    job_id = await simulation_service_batch_mock.submit_ecoli_simulation_job(
        ecoli_simulation=simulation, database_service=database_service, correlation_id=correlation_id
    )
    assert job_id is not None

    await database_service.insert_hpcrun(
        external_job_id=job_id,
        job_backend="batch",
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id=correlation_id,
    )

    status = await simulation_service_batch_mock.get_job_status(job_id)
    assert status is not None
    assert status.status == JobStatus.COMPLETED

    mock_batch: MockAwsBatchService = simulation_service_batch_mock._batch_service  # type: ignore[assignment]
    assert len(mock_batch.submitted_jobs) == 1
    submitted = mock_batch.submitted_jobs[0]
    assert submitted["job_name"].startswith("sim-")
    env_vars = {e["name"]: e["value"] for e in submitted["container_overrides"]["environment"]}
    assert env_vars["EXPERIMENT_ID"] == TEST_EXPERIMENT_ID
    assert env_vars["SIMULATION_ID"] == str(simulation.database_id)
    assert env_vars["CORRELATION_ID"] == correlation_id


# =============================================================================
# Full end-user e2e workflow via gateway API endpoints
# =============================================================================


@pytest.mark.asyncio
async def test_4_full_e2e_workflow(
    simulation_service_batch_mock: SimulationServiceBatch,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
    tmp_path: Path,
) -> None:
    """Full end-user e2e workflow exercising every gateway simulation endpoint.

    Walks through the complete lifecycle an end-user would follow:
    1. POST /simulations       — submit simulation
    2. GET  /simulations/{id}  — retrieve simulation record
    3. GET  /simulations/{id}/status — check job status
    4. GET  /simulations       — list all simulations
    5. POST /simulations/{id}/data   — download output data as tar.gz
    """
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    job_uuid = uuid.uuid4().hex[:8]
    experiment_id = f"batch-mock-e2e-{job_uuid}"

    mock_ssh_service, mock_ssh = _build_mock_ssh_service()

    # ---- Step 1: POST /simulations (submit) ----
    with (
        patch("sms_api.common.handlers.simulations.get_ssh_session_service", return_value=mock_ssh_service),
        patch("sms_api.common.handlers.simulations.get_job_backend", return_value="batch"),
    ):
        async with _api_client() as client:
            response = await client.post(
                f"{API_ROUTER}/simulations",
                params={
                    "simulator_id": simulator.database_id,
                    "experiment_id": experiment_id,
                    "simulation_config_filename": "api_simulation_default.json",
                    "num_generations": 1,
                    "num_seeds": 1,
                    "description": "Full e2e mock integration test",
                    "run_parca": False,
                },
            )
            assert response.status_code == 200, f"POST /simulations failed ({response.status_code}): {response.text}"

            sim_data = response.json()
            assert "database_id" in sim_data
            assert "config" in sim_data
            db_id = sim_data["database_id"]
            actual_experiment_id = sim_data["config"]["experiment_id"]

    # Verify HPC run was recorded with backend="batch"
    hpc_run = await database_service.get_hpcrun_by_ref(ref_id=db_id, job_type=JobType.SIMULATION)
    assert hpc_run is not None, "HPC run record should exist after POST /simulations"
    assert hpc_run.external_job_id, "external_job_id should be set"
    assert hpc_run.job_backend == "batch"

    # Verify mock captured correct submission
    mock_batch: MockAwsBatchService = simulation_service_batch_mock._batch_service  # type: ignore[assignment]
    assert len(mock_batch.submitted_jobs) == 1
    submitted = mock_batch.submitted_jobs[0]
    env_vars = {e["name"]: e["value"] for e in submitted["container_overrides"]["environment"]}
    assert env_vars["SIMULATION_ID"] == str(db_id)

    # ---- Step 2: GET /simulations/{id} (retrieve record) ----
    async with _api_client() as client:
        response = await client.get(f"{API_ROUTER}/simulations/{db_id}")
        assert response.status_code == 200, f"GET /simulations/{db_id} failed: {response.text}"

        sim_record = response.json()
        assert sim_record["database_id"] == db_id
        assert sim_record["simulator_id"] == simulator.database_id
        assert sim_record["config"]["experiment_id"] == actual_experiment_id
        assert sim_record["config"]["generations"] == 1
        assert sim_record["config"]["n_init_sims"] == 1

    # ---- Step 3: GET /simulations/{id}/status (poll status) ----
    with patch("sms_api.common.handlers.simulations.get_job_backend", return_value="batch"):
        async with _api_client() as client:
            status_resp = await client.get(f"{API_ROUTER}/simulations/{db_id}/status")
            assert status_resp.status_code == 200, f"GET /simulations/{db_id}/status failed: {status_resp.text}"

            status_data = status_resp.json()
            assert status_data["id"] == db_id
            assert status_data["status"] == JobStatus.COMPLETED

    # ---- Step 4: GET /simulations (list all) ----
    async with _api_client() as client:
        response = await client.get(f"{API_ROUTER}/simulations")
        assert response.status_code == 200, f"GET /simulations failed: {response.text}"

        simulations = response.json()
        assert isinstance(simulations, list)
        assert len(simulations) >= 1
        our_sim = next((s for s in simulations if s["database_id"] == db_id), None)
        assert our_sim is not None, f"Simulation {db_id} should appear in list"
        assert our_sim["config"]["experiment_id"] == actual_experiment_id

    # ---- Step 5: POST /simulations/{id}/data (download outputs) ----
    # The data endpoint uses SSH to:
    #   a) `find` remote output files (get_available_omics_output_paths)
    #   b) `scp_download` each file (download_analysis_output)
    # We mock both: find returns fake paths, scp_download writes local files.

    # Build the fake find output using the same base path the handler will use
    from sms_api.config import get_settings as _get_settings

    hpc_sim_base = str(_get_settings().hpc_sim_base_path)
    analysis_dir = f"{hpc_sim_base}/{actual_experiment_id}/analyses"
    find_output = "\n".join(f"{analysis_dir}/{fname}" for fname in FAKE_OUTPUT_FILES)

    def _ssh_run_command_side_effect(command: str):  # type: ignore[no-untyped-def]
        """Route SSH commands: find returns file listing, cat returns config."""
        if command.startswith("find "):
            return (0, find_output, "")
        return (0, CONFIG_TEMPLATE, "")

    async def _scp_download_side_effect(local_file, remote_path):  # type: ignore[no-untyped-def]
        """Create fake local files when scp_download is called."""
        local = Path(local_file) if not isinstance(local_file, Path) else local_file
        local.parent.mkdir(parents=True, exist_ok=True)
        fname = local.name
        local.write_text(f"# Mock output data for {fname}\ncol1\tcol2\n1.0\t2.0\n")

    mock_ssh_service_data, mock_ssh_data = _build_mock_ssh_service(
        run_command_side_effect=_ssh_run_command_side_effect,
    )
    mock_ssh_data.scp_download.side_effect = _scp_download_side_effect

    # Point the cache dir to tmp_path so we don't pollute the repo
    with (
        patch("sms_api.common.handlers.simulations.get_ssh_session_service", return_value=mock_ssh_service_data),
        patch("sms_api.common.handlers.simulations.get_settings") as mock_get_settings,
    ):
        real_settings = __import__("sms_api.config", fromlist=["get_settings"]).get_settings()
        mock_settings = AsyncMock(wraps=real_settings)
        mock_settings.cache_dir = str(tmp_path / "cache")
        mock_settings.hpc_sim_base_path = real_settings.hpc_sim_base_path
        mock_get_settings.return_value = mock_settings

        async with _api_client() as client:
            data_resp = await client.post(
                f"{API_ROUTER}/simulations/{db_id}/data",
                params={"response_type": "streaming"},
            )
            assert data_resp.status_code == 200, f"POST /simulations/{db_id}/data failed: {data_resp.text}"
            assert data_resp.headers["content-type"] == "application/gzip"

            # Verify we got actual tar.gz content
            content = data_resp.content
            # gzip magic bytes
            assert content[:2] == b"\x1f\x8b", "Response should be gzip-compressed"
            assert len(content) > 0

    # Verify scp_download was called for each output file
    assert mock_ssh_data.scp_download.call_count == len(FAKE_OUTPUT_FILES)
