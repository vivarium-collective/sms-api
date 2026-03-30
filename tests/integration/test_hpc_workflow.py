"""HPC Integration Tests - Full workflow from build to analysis.

These tests must run in order as each depends on the previous:
1. test_build_image - Clone repo and build singularity container
2. test_run_parca - Run parca to create dataset
3. test_run_simulation - Run simulation
4. test_run_analysis - Run analysis on simulation output

Run with: uv run pytest tests/integration/test_hpc_workflow.py -v

Prerequisites:
- SSH access to HPC (SLURM_SUBMIT_KEY_PATH configured)
- Write access to HPC paths (HPC_IMAGE_BASE_PATH, etc.)

Idempotency:
- Tests check for existing artifacts before running jobs
- Build is skipped if singularity image already exists
- Parca is skipped if dataset with matching config exists
- Simulation is skipped if simulation with matching config exists
- To force re-run, manually delete HPC artifacts
"""

import asyncio
import random
import string
import time

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.dependencies import get_ssh_session_service
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.hpc_utils import get_apptainer_image_file, get_correlation_id
from sms_api.simulation.models import (
    JobType,
    ParcaDatasetRequest,
    ParcaOptions,
    SimulationConfig,
    SimulationRequest,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationServiceHpc
from tests.fixtures.api_fixtures import SimulatorRepoInfo

TEST_EXPERIMENT_ID = "test_integration"

# Skip all tests if SSH not configured
pytestmark = pytest.mark.skipif(
    len(get_settings().slurm_submit_key_path) == 0,
    reason="slurm ssh key file not supplied",
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


async def check_image_exists(simulator: SimulatorVersion) -> bool:
    """Check if the singularity image already exists on HPC."""
    image_path = get_apptainer_image_file(simulator)
    async with get_ssh_session_service().session() as ssh:
        try:
            await ssh.run_command(f"test -f {image_path.remote_path}")
            return True
        except RuntimeError:
            # test -f returns exit code 1 when file doesn't exist
            return False


async def scan_hpc_for_parca_dir(commit_hash: str) -> str | None:
    """Scan HPC filesystem for existing parca directory matching commit hash.

    Returns the directory name if found, None otherwise.
    """
    settings = get_settings()
    parca_base = settings.hpc_parca_base_path.remote_path
    pattern = f"parca_{commit_hash}_*"

    async with get_ssh_session_service().session() as ssh:
        try:
            _retcode, stdout, _stderr = await ssh.run_command(f"ls -d {parca_base}/{pattern} 2>/dev/null | head -1")
            if stdout.strip():
                # Return just the directory name
                return stdout.strip().split("/")[-1]
        except RuntimeError:
            pass
    return None


async def scan_hpc_for_simulation_output(experiment_id: str) -> bool:
    """Check if simulation output exists for the given experiment_id.

    Checks simulation_outdir/{experiment_id}/variant_sim_data exists.
    Returns True if found, False otherwise.
    """
    settings = get_settings()
    sim_outdir = settings.simulation_outdir.remote_path
    variant_data_path = f"{sim_outdir}/{experiment_id}/variant_sim_data"

    async with get_ssh_session_service().session() as ssh:
        try:
            await ssh.run_command(f"test -d {variant_data_path}")
            return True
        except RuntimeError:
            # test -d returns exit code 1 when directory doesn't exist
            return False


async def get_existing_parca_dataset(database_service: DatabaseServiceSQL, simulator: SimulatorVersion) -> int | None:
    """Get existing parca dataset for this simulator if one exists."""
    parca_datasets = await database_service.list_parca_datasets()
    for parca in parca_datasets:
        if parca.parca_dataset_request.simulator_version.database_id == simulator.database_id:
            return parca.database_id
    return None


async def get_existing_simulation(
    database_service: DatabaseServiceSQL, simulator_id: int, experiment_id: str
) -> int | None:
    """Get existing simulation for this simulator and experiment if one exists."""
    simulations = await database_service.list_simulations()
    for sim in simulations:
        if sim.simulator_id == simulator_id and sim.config.experiment_id == experiment_id:
            return sim.database_id
    return None


async def get_or_create_parca_dataset(database_service: DatabaseServiceSQL, simulator: SimulatorVersion) -> int:
    """Get or create parca dataset for this simulator."""
    # Check if parca dataset already exists for this simulator
    parca_datasets = await database_service.list_parca_datasets()
    for parca in parca_datasets:
        if parca.parca_dataset_request.simulator_version.database_id == simulator.database_id:
            return parca.database_id

    # Create new parca dataset
    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=ParcaOptions())
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)
    return parca_dataset.database_id


@pytest.mark.asyncio
async def test_1_build_image(
    simulation_service_slurm: SimulationServiceHpc,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 1: Clone repository and build singularity container.

    Skips if image already exists on HPC.
    """
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    # Check if image already exists
    if await check_image_exists(simulator):
        image_path = get_apptainer_image_file(simulator)
        pytest.skip(f"Image already exists: {image_path.remote_path}")

    # Reuse SSH session for job submission and polling
    async with get_ssh_session_service().session() as ssh:
        job_id = await simulation_service_slurm.submit_build_image_job(simulator_version=simulator, ssh=ssh)
        assert job_id is not None

        start_time = time.time()
        slurm_job = None
        while start_time + 1800 > time.time():  # 30 minute timeout for build
            slurm_job = await simulation_service_slurm.get_slurm_job_status(slurmjobid=job_id, ssh=ssh)
            if slurm_job is not None and slurm_job.is_done():
                break
            await asyncio.sleep(10)

    assert slurm_job is not None, "Build job did not complete in time"
    assert slurm_job.is_done()
    assert slurm_job.job_id == job_id
    assert slurm_job.name.startswith(f"build-image-{simulator_repo_info.commit_hash}-")


@pytest.mark.asyncio
async def test_2_run_parca(
    simulation_service_slurm: SimulationServiceHpc,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 2: Run parca to create dataset.

    Skips if parca directory for this simulator already exists on HPC.
    """
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    # Check if parca directory already exists on HPC filesystem
    existing_parca_dir = await scan_hpc_for_parca_dir(simulator_repo_info.commit_hash)
    if existing_parca_dir is not None:
        pytest.skip(f"Parca directory already exists on HPC: {existing_parca_dir}")

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=ParcaOptions())
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    # Reuse SSH session for job submission and polling
    async with get_ssh_session_service().session() as ssh:
        job_id = await simulation_service_slurm.submit_parca_job(parca_dataset=parca_dataset, ssh=ssh)
        assert job_id is not None

        start_time = time.time()
        slurm_job = None
        while start_time + 1800 > time.time():  # 30 minute timeout for parca
            slurm_job = await simulation_service_slurm.get_slurm_job_status(slurmjobid=job_id, ssh=ssh)
            if slurm_job is not None and slurm_job.is_done():
                break
            await asyncio.sleep(10)

    assert slurm_job is not None, "Parca job did not complete in time"
    assert slurm_job.is_done()
    assert slurm_job.job_id == job_id
    assert slurm_job.name.startswith(f"parca-{simulator_repo_info.commit_hash}-")


@pytest.mark.asyncio
async def test_3_run_simulation(
    simulation_service_slurm: SimulationServiceHpc,
    database_service: DatabaseServiceSQL,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 3: Run simulation.

    Skips if simulation output (variant_sim_data) already exists on HPC.
    """
    simulator = await get_or_create_simulator(database_service, simulator_repo_info)

    # Check if simulation output already exists on HPC filesystem
    if await scan_hpc_for_simulation_output(TEST_EXPERIMENT_ID):
        pytest.skip(f"Simulation output already exists on HPC for experiment: {TEST_EXPERIMENT_ID}")

    # Get or create parca dataset (required for simulation)
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
    correlation_id = get_correlation_id(ecoli_simulation=simulation, random_string=random_string, simulator=simulator)

    # Reuse SSH session for job submission and polling
    async with get_ssh_session_service().session() as ssh:
        job_id = await simulation_service_slurm.submit_ecoli_simulation_job(
            ecoli_simulation=simulation, database_service=database_service, correlation_id=correlation_id, ssh=ssh
        )
        assert job_id is not None

        await database_service.insert_hpcrun(
            slurmjobid=job_id,
            job_type=JobType.SIMULATION,
            ref_id=simulation.database_id,
            correlation_id=correlation_id,
        )

        start_time = time.time()
        slurm_job = None
        while start_time + 1800 > time.time():  # 30 minute timeout for simulation
            slurm_job = await simulation_service_slurm.get_slurm_job_status(slurmjobid=job_id, ssh=ssh)
            if slurm_job is not None and slurm_job.is_done():
                break
            await asyncio.sleep(10)

    assert slurm_job is not None, "Simulation job did not complete in time"
    assert slurm_job.is_done()
    assert slurm_job.job_id == job_id
    assert slurm_job.name.startswith(f"sim-{simulator_repo_info.commit_hash}-")


@pytest.mark.asyncio
async def test_4_run_analysis(
    base_router: str,
    database_service: DatabaseServiceSQL,
    ssh_session_service: SSHSessionService,
    simulator_repo_info: SimulatorRepoInfo,
) -> None:
    """Step 4: Run analysis on simulation output.

    Runs analysis on the TEST_EXPERIMENT_ID simulation created in test_3.
    Skips if no simulation output exists for TEST_EXPERIMENT_ID.
    """
    # Check if simulation output exists for TEST_EXPERIMENT_ID
    if not await scan_hpc_for_simulation_output(TEST_EXPERIMENT_ID):
        pytest.skip(f"No simulation output found for experiment: {TEST_EXPERIMENT_ID}")

    # Create analysis request for TEST_EXPERIMENT_ID
    from sms_api.analysis.models import ExperimentAnalysisRequest, PtoolsAnalysisConfig, PtoolsAnalysisType

    analysis_request = ExperimentAnalysisRequest(
        experiment_id=TEST_EXPERIMENT_ID,
        multiseed=[
            PtoolsAnalysisConfig(
                name=PtoolsAnalysisType.REACTIONS,
                n_tp=5,
            )
        ],
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/analyses", json=analysis_request.model_dump())
        response.raise_for_status()
        data = response.json()

    assert data is not None
    assert isinstance(data, list)
