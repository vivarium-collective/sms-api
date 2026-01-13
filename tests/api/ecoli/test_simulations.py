"""Tests for simulation endpoints.

This module contains:
1. Database-level tests for simulation CRUD operations
2. Integration tests for the /simulations endpoint via HTTP API

Run with: uv run pytest tests/api/ecoli/test_simulations.py -v

Prerequisites for API tests:
- SSH access to HPC (SLURM_SUBMIT_KEY_PATH configured)
- Config template exists at {HPC_REPO_BASE_PATH}/{hash}/vEcoli/configs/api_simulation_default.json
"""

import asyncio
import time
import uuid
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api import request_examples
from sms_api.api.main import app
from sms_api.common.models import JobStatus
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.models import (
    ExperimentRequest,
    ParcaDatasetRequest,
    ParcaOptions,
    SimulationConfig,
    SimulationRequest,
)
from sms_api.simulation.simulation_service import SimulationServiceHpc
from tests.fixtures.api_fixtures import SimulatorRepoInfo

# Config file name expected in vEcoli/configs/
CONFIG_FILENAME = "api_simulation_default.json"

# Core router prefix (for simulator endpoints)
CORE_ROUTER = "/core/v1"


# =============================================================================
# Database-level tests (no SSH required)
# =============================================================================


@pytest.mark.asyncio
async def test_list_simulations(
    experiment_request: SimulationRequest,
    database_service: DatabaseServiceSQL,
) -> None:
    """Test listing simulations from the database."""
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
    """Test getting a single simulation from the database."""
    sim_i = await database_service.insert_simulation(experiment_request)

    fetched_i = await database_service.get_simulation(simulation_id=sim_i.database_id)
    assert fetched_i.model_dump() == sim_i.model_dump()  # type: ignore[union-attr]


# =============================================================================
# API integration tests (require SSH access)
# =============================================================================


async def _ensure_simulator_ready(
    client: AsyncClient,
    repo_info: SimulatorRepoInfo,
) -> int:
    """
    Ensure simulator is registered and built using REST endpoints.

    1. GET /simulator/versions to find existing simulator
    2. POST /simulator/upload if not found (triggers build job)
    3. Poll GET /simulator/status until build completes

    Returns the simulator database ID.
    """
    # Check if simulator already exists
    versions_response = await client.get(f"{CORE_ROUTER}/simulator/versions")
    versions_response.raise_for_status()
    versions_data = versions_response.json()

    simulator_id: int | None = None
    for sim in versions_data.get("versions", []):
        if (
            sim.get("git_commit_hash") == repo_info.commit_hash
            and sim.get("git_repo_url") == repo_info.url
            and sim.get("git_branch") == repo_info.branch
        ):
            simulator_id = int(sim["database_id"])
            print(f"  Found existing simulator: ID={simulator_id}")
            break

    # If not found, upload/create it
    if simulator_id is None:
        print(f"  Creating new simulator for {repo_info.commit_hash}...")
        upload_response = await client.post(
            f"{CORE_ROUTER}/simulator/upload",
            json={
                "git_commit_hash": repo_info.commit_hash,
                "git_repo_url": repo_info.url,
                "git_branch": repo_info.branch,
            },
        )
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        simulator_data = upload_response.json()
        simulator_id = int(simulator_data["database_id"])
        print(f"  Created simulator: ID={simulator_id}")

    # Poll build status until complete (build includes repo clone + image build)
    start_time = time.time()
    max_wait_seconds = 1800  # 30 minute timeout for build

    while time.time() - start_time < max_wait_seconds:
        try:
            status_response = await client.get(
                f"{CORE_ROUTER}/simulator/status",
                params={"simulator_id": simulator_id},
            )
            if status_response.status_code == 404:
                # No build job found - simulator was already built previously
                print("  Simulator already built (no pending build job)")
                break

            status_response.raise_for_status()
            status_data = status_response.json()
            build_status = status_data.get("status")

            elapsed = int(time.time() - start_time)
            if build_status in ["COMPLETED", "completed"]:
                print(f"  Build completed after {elapsed}s")
                break
            elif build_status in ["FAILED", "failed"]:
                pytest.fail(f"Simulator build failed: {status_data}")
            elif elapsed % 60 == 0 and elapsed > 0:
                print(f"  Build status: {build_status} ({elapsed}s elapsed)")

            await asyncio.sleep(10)
        except Exception as e:
            # If status check fails, assume simulator is ready (no active build)
            print(f"  Build status check: {e}, assuming ready")
            break
    else:
        pytest.fail(f"Simulator build did not complete within {max_wait_seconds}s")

    assert simulator_id is not None, "Simulator ID should be set"
    return simulator_id


@pytest.mark.integration
@pytest.mark.skipif(
    len(get_settings().slurm_submit_key_path) == 0,
    reason="slurm ssh key file not supplied",
)
@pytest.mark.asyncio
async def test_run_simulation_e2e(
    base_router: str,
    simulation_service_slurm: SimulationServiceHpc,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
    ssh_session_service: SSHSessionService,
) -> None:
    """
    E2E integration test for POST /api/v1/simulations endpoint.

    This test uses only REST endpoints:
    1. GET/POST /simulator/* to ensure simulator is ready
    2. POST /simulations with query parameters
    3. Poll GET /simulations/{id}/status until workflow completes

    Expected runtime: 30-60 minutes depending on cluster load.
    """
    job_uuid = uuid.uuid4().hex[:8]
    experiment_id = f"test_api_{job_uuid}"

    print("\n=== Test: run_simulation_e2e ===")
    print(f"  Experiment ID: {experiment_id}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Step 1: Ensure simulator is ready via REST endpoints
        print("\nStep 1: Ensuring simulator is ready...")
        simulator_id = await _ensure_simulator_ready(client, simulator_repo_info)
        print(f"  Using simulator ID: {simulator_id}")

        # Step 2: POST to /simulations
        print("\nStep 2: POST /simulations")
        print(f"  Config file: {CONFIG_FILENAME}")

        response = await client.post(
            f"{base_router}/simulations",
            params={
                "simulator_id": simulator_id,
                "experiment_id": experiment_id,
                "simulation_config_filename": CONFIG_FILENAME,
                "num_generations": 2,  # Override for faster test
                "num_seeds": 2,  # Override for faster test
                "description": "Integration test via /simulations endpoint",
            },
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        sim_response = response.json()
        assert "database_id" in sim_response, "Response should contain database_id"
        assert "job_id" in sim_response, "Response should contain job_id"
        assert sim_response["job_id"] is not None, "job_id should not be None"

        db_id = sim_response["database_id"]
        job_id = sim_response["job_id"]

        print(f"  Simulation DB ID: {db_id}")
        print(f"  SLURM Job ID: {job_id}")

        # Step 3: Poll for workflow completion
        print("\nStep 3: Polling for completion...")
        start_time = time.time()
        max_wait_seconds = 7200  # 2 hour timeout
        poll_interval = 30
        final_status = None

        while time.time() - start_time < max_wait_seconds:
            status_response = await client.get(f"{base_router}/simulations/{db_id}/status")
            assert status_response.status_code == 200, f"Status check failed: {status_response.text}"

            status_data = status_response.json()
            status = status_data.get("status")
            elapsed = int(time.time() - start_time)

            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                print(f"\n  Job {job_id} finished after {elapsed}s")
                print(f"  Status: {status}")
                final_status = status
                break
            elif elapsed % 60 == 0:
                print(f"  Job {job_id} status: {status} ({elapsed}s elapsed)")

            await asyncio.sleep(poll_interval)
        else:
            pytest.fail(f"Workflow job {job_id} did not complete within {max_wait_seconds}s")

    # Verify job completed successfully
    assert final_status == JobStatus.COMPLETED, f"Workflow should complete successfully. Status: {final_status}"

    print("\n=== Test completed successfully! ===")
    print(f"  Experiment ID: {experiment_id}")
    print(f"  Simulation DB ID: {db_id}")


@pytest.mark.skipif(
    len(get_settings().slurm_submit_key_path) == 0,
    reason="slurm ssh key file not supplied",
)
@pytest.mark.asyncio
async def test_get_simulation_data(
    base_router: str,
    database_service: DatabaseServiceSQL,
    ssh_session_service: SSHSessionService,
) -> None:
    """Test GET simulation data endpoint with a pre-existing simulation output directory.

    This test manually inserts a simulation into the database that references
    the existing simulation output at /projects/SMS/sms_api/alex/sims/sms_multigeneration,
    then calls the get_simulation_data endpoint to retrieve the outputs.
    """
    # Create a unique commit hash for the simulator
    unique_commit_hash = f"test_{uuid.uuid4().hex[:7]}"

    # Insert the simulator into the database
    simulator = await database_service.insert_simulator(
        git_commit_hash=unique_commit_hash,
        git_repo_url=request_examples.DEFAULT_SIMULATOR.git_repo_url,
        git_branch=request_examples.DEFAULT_SIMULATOR.git_branch,
    )

    # Insert a parca dataset for this simulator
    parca_request = ParcaDatasetRequest(
        simulator_version=simulator,
        parca_config=ParcaOptions(),
    )
    parca_dataset = await database_service.insert_parca_dataset(
        parca_dataset_request=parca_request,
    )

    # Create a SimulationConfig pointing to the existing sms_multigeneration output
    sim_config = SimulationConfig(
        experiment_id="sms_multigeneration",
        emitter="parquet",
        emitter_arg={"out_dir": "/projects/SMS/sms_api/alex/sims/sms_multigeneration"},
    )

    # Create the simulation request
    sim_request = SimulationRequest(
        simulator_id=simulator.database_id,
        parca_dataset_id=parca_dataset.database_id,
        config=sim_config,
    )

    # Insert the simulation into the database
    inserted_sim = await database_service.insert_simulation(sim_request=sim_request)
    db_id = inserted_sim.database_id

    # Call the get_simulation_data endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/simulations/{db_id}/data")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
