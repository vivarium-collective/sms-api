"""AWS Batch Integration Tests - Full workflow from build to simulation.

These tests must run in order as each depends on the previous:
1. test_1_build_image - Submit Docker image build job to Batch
2. test_2_run_parca - Submit parca parameter calculator job
3. test_3_run_simulation - Submit simulation job
4. test_4_post_simulations_endpoint - POST /api/v1/simulations via Batch backend

Run with: uv run pytest tests/integration/test_batch_workflow.py -v -s

Prerequisites:
- AWS credentials configured (via environment or credential chain)
- BATCH_JOB_QUEUE set in settings

Idempotency:
- Tests check the database for existing records before submitting jobs
- To force re-run, clear the relevant DB records
"""

import asyncio
import json
import random
import string
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.hpc.job_service import JobStatusInfo
from sms_api.common.models import JobStatus
from sms_api.config import get_settings
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

TEST_EXPERIMENT_ID = "test_batch_integration"

# Skip all tests if Batch job queue is not configured
pytestmark = pytest.mark.skipif(
    len(get_settings().batch_job_queue) == 0,
    reason="BATCH_JOB_QUEUE not configured",
)


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


async def get_existing_parca_dataset(database_service: DatabaseServiceSQL, simulator: SimulatorVersion) -> int | None:
    """Get existing parca dataset for this simulator if one exists."""
    parca_datasets = await database_service.list_parca_datasets()
    for parca in parca_datasets:
        if parca.parca_dataset_request.simulator_version.database_id == simulator.database_id:
            return parca.database_id
    return None


async def get_or_create_parca_dataset(database_service: DatabaseServiceSQL, simulator: SimulatorVersion) -> int:
    """Get or create parca dataset for this simulator."""
    existing = await get_existing_parca_dataset(database_service, simulator)
    if existing is not None:
        return existing

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=ParcaOptions())
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)
    return parca_dataset.database_id


async def get_existing_simulation(
    database_service: DatabaseServiceSQL, simulator_id: int, experiment_id: str
) -> int | None:
    """Get existing simulation for this simulator and experiment if one exists."""
    simulations = await database_service.list_simulations()
    for sim in simulations:
        if sim.simulator_id == simulator_id and sim.config.experiment_id == experiment_id:
            return sim.database_id
    return None


async def poll_batch_job(
    simulation_service: SimulationServiceBatch,
    job_id: str,
    timeout_seconds: int = 1800,
    poll_interval: int = 15,
) -> JobStatusInfo:
    """Poll a Batch job until it reaches a terminal state or times out."""
    start_time = time.time()
    status: JobStatusInfo | None = None
    while start_time + timeout_seconds > time.time():
        status = await simulation_service.get_job_status(job_id)
        if status is not None and status.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            break
        await asyncio.sleep(poll_interval)

    assert status is not None, f"Job {job_id} did not complete within {timeout_seconds}s"
    return status


@pytest.mark.asyncio
async def test_1_build_image(
    simulation_service_batch: SimulationServiceBatch,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 1: Submit Docker image build job to AWS Batch.

    Skips if a build HPC run record already exists for this simulator.
    """
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    existing_run = await database_service.get_hpcrun_by_ref(ref_id=simulator.database_id, job_type=JobType.BUILD_IMAGE)
    if existing_run is not None:
        pytest.skip(f"Build HPC run already exists for simulator {simulator.database_id}")

    job_id = await simulation_service_batch.submit_build_image_job(simulator_version=simulator)
    assert job_id is not None

    await database_service.insert_hpcrun(
        external_job_id=job_id,
        job_backend="batch",
        job_type=JobType.BUILD_IMAGE,
        ref_id=simulator.database_id,
        correlation_id=f"build-{simulator.git_commit_hash}",
    )

    status = await poll_batch_job(simulation_service_batch, job_id)
    assert status.status == JobStatus.COMPLETED, f"Build job failed: {status.error_message}"


@pytest.mark.asyncio
async def test_2_run_parca(
    simulation_service_batch: SimulationServiceBatch,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 2: Submit parca parameter calculator job to AWS Batch.

    Skips if a parca HPC run record already exists for this simulator.
    """
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    existing_parca_id = await get_existing_parca_dataset(database_service, simulator)
    if existing_parca_id is not None:
        existing_run = await database_service.get_hpcrun_by_ref(ref_id=existing_parca_id, job_type=JobType.PARCA)
        if existing_run is not None:
            pytest.skip(f"Parca HPC run already exists for dataset {existing_parca_id}")

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=ParcaOptions())
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    job_id = await simulation_service_batch.submit_parca_job(parca_dataset=parca_dataset)
    assert job_id is not None

    await database_service.insert_hpcrun(
        external_job_id=job_id,
        job_backend="batch",
        job_type=JobType.PARCA,
        ref_id=parca_dataset.database_id,
        correlation_id=f"parca-{simulator.git_commit_hash}-{parca_dataset.database_id}",
    )

    status = await poll_batch_job(simulation_service_batch, job_id)
    assert status.status == JobStatus.COMPLETED, f"Parca job failed: {status.error_message}"


@pytest.mark.asyncio
async def test_3_run_simulation(
    simulation_service_batch: SimulationServiceBatch,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 3: Submit simulation job to AWS Batch.

    Skips if a simulation HPC run record already exists for this experiment.
    """
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    existing_sim_id = await get_existing_simulation(database_service, simulator.database_id, TEST_EXPERIMENT_ID)
    if existing_sim_id is not None:
        existing_run = await database_service.get_hpcrun_by_ref(ref_id=existing_sim_id, job_type=JobType.SIMULATION)
        if existing_run is not None:
            pytest.skip(f"Simulation HPC run already exists for sim {existing_sim_id}")

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

    job_id = await simulation_service_batch.submit_ecoli_simulation_job(
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

    status = await poll_batch_job(simulation_service_batch, job_id)
    assert status.status == JobStatus.COMPLETED, f"Simulation job failed: {status.error_message}"


# =============================================================================
# POST /api/v1/simulations endpoint test (Batch backend)
# =============================================================================

# Gateway router prefix
API_ROUTER = "/api/v1"

# Minimal config template matching what the handler reads from HPC via SSH.
# Placeholders are replaced by run_simulation_workflow() before parsing.
CONFIG_TEMPLATE = json.dumps({
    "experiment_id": "EXPERIMENT_ID_PLACEHOLDER",
    "generations": 1,
    "n_init_sims": 1,
    "parca_options": {"cpus": 1},
    "analysis_options": {},
    "sim_data_path": "HPC_SIM_BASE_PATH_PLACEHOLDER/default/kb/simData.cPickle",
})


@asynccontextmanager
async def _api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_4_post_simulations_endpoint(
    simulation_service_batch: SimulationServiceBatch,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Test the POST /api/v1/simulations endpoint using the Batch backend.

    The handler reads a config template from the HPC filesystem via SSH.
    Since Batch deployments don't use SSH, we mock that call and patch
    ``get_job_backend`` to return ``"batch"``.  Everything else — DB writes,
    Batch job submission, and status polling — is exercised for real.
    """
    # 1. Insert simulator directly into the DB (avoids upload_simulator which submits a build job)
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    job_uuid = uuid.uuid4().hex[:8]
    experiment_id = f"batch-e2e-{job_uuid}"

    # 2. Mock the SSH config-file read and patch the job backend to "batch".
    #    The handler calls:
    #      async with get_ssh_session_service().session() as ssh:
    #          returncode, stdout, stderr = await ssh.run_command(f"cat {remote_config_path}")
    #    We replace get_ssh_session_service so it returns a context manager
    #    whose session's run_command returns our template.
    mock_ssh = AsyncMock()
    mock_ssh.run_command.return_value = (0, CONFIG_TEMPLATE, "")

    @asynccontextmanager
    async def _mock_session():  # type: ignore[no-untyped-def]
        yield mock_ssh

    mock_ssh_service = AsyncMock()
    mock_ssh_service.session = _mock_session

    with (
        patch("sms_api.common.handlers.simulations.get_ssh_session_service", return_value=mock_ssh_service),
        patch("sms_api.common.handlers.simulations.get_job_backend", return_value="batch"),
    ):
        async with _api_client() as client:
            # 3. POST /simulations
            response = await client.post(
                f"{API_ROUTER}/simulations",
                params={
                    "simulator_id": simulator.database_id,
                    "experiment_id": experiment_id,
                    "simulation_config_filename": "api_simulation_default.json",
                    "num_generations": 1,
                    "num_seeds": 1,
                    "description": "Batch integration test via endpoint",
                    "run_parca": False,
                },
            )
            assert response.status_code == 200, f"POST /simulations failed ({response.status_code}): {response.text}"

            sim_data = response.json()
            assert "database_id" in sim_data
            db_id = sim_data["database_id"]

            # Batch job IDs are UUIDs, so job_id on the Simulation model will be None
            # (the model stores int | None and Batch UUIDs aren't ints).
            # The HPC run record holds the real Batch job ID.

    # 4. Verify the HPC run was recorded with backend="batch"
    hpc_run = await database_service.get_hpcrun_by_ref(ref_id=db_id, job_type=JobType.SIMULATION)
    assert hpc_run is not None, "HPC run record should exist after POST /simulations"
    batch_job_id = hpc_run.external_job_id
    assert batch_job_id, "external_job_id should be set on the HPC run record"

    # 5. Poll Batch job via the status endpoint (exercises get_simulation_status → get_job_status)
    with patch("sms_api.common.handlers.simulations.get_job_backend", return_value="batch"):
        async with _api_client() as client:
            start_time = time.time()
            max_wait = 1800  # 30 min
            poll_interval = 15
            final_status: str | None = None

            while time.time() - start_time < max_wait:
                status_resp = await client.get(f"{API_ROUTER}/simulations/{db_id}/status")
                assert status_resp.status_code == 200, f"Status check failed: {status_resp.text}"

                status_data = status_resp.json()
                status = status_data.get("status")
                elapsed = int(time.time() - start_time)

                if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    final_status = status
                    break

                if elapsed % 60 == 0 and elapsed > 0:
                    print(f"  Batch job {batch_job_id} status: {status} ({elapsed}s elapsed)")

                await asyncio.sleep(poll_interval)
            else:
                pytest.fail(f"Batch job {batch_job_id} did not complete within {max_wait}s")

    assert final_status == JobStatus.COMPLETED, f"Batch simulation should complete successfully. Got: {final_status}"
