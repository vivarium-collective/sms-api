"""
[x] base sim (cached)
- antibiotic
- biomanufacturing
- batch variant endpoint
- design specific endpoints.
- downsampling ...
- biocyc id
- api to download the data
- marimo instead of Jupyter notebooks....(auth). ... also on gov cloud.
- endpoint to send sql like queries to parquet files back to client
"""

import logging
import shutil
import tempfile
from pathlib import Path

import polars as pl
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse, ORJSONResponse

from sms_api.common.gateway.models import Namespace, RouterConfig, ServerMode
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.dependencies import (
    get_database_service,
    get_postgres_engine,
    get_simulation_service,
)
from sms_api.log_config import setup_logging
from sms_api.simulation.data_service import DataServiceHpc
from sms_api.simulation.handlers import (
    get_parca_datasets,
    run_parca,
    run_simulation,
    upload_simulator,
    verify_simulator_payload,
)
from sms_api.simulation.hpc_utils import read_latest_commit
from sms_api.simulation.models import (
    EcoliExperiment,
    EcoliSimulation,
    EcoliSimulationRequest,
    HpcRun,
    JobType,
    ParcaDataset,
    ParcaDatasetRequest,
    RegisteredSimulators,
    RequestedObservables,
    Simulator,
    SimulatorVersion,
    WorkerEvent,
)

logger = logging.getLogger(__name__)
setup_logging(logger)

LATEST_COMMIT = read_latest_commit()


def get_server_url(dev: bool = True) -> ServerMode:
    return ServerMode.DEV if dev else ServerMode.PROD


# -- app components -- #

# TODO: mount nfs driver


config = RouterConfig(router=APIRouter(), prefix="/core", dependencies=[])


@config.router.get("/simulator/latest", operation_id="latest-simulator-hash", tags=["Simulators"])
async def get_latest_simulator(
    git_repo_url: str = Query(default="https://github.com/vivarium-collective/vEcoli"),
    git_branch: str = Query(default="messages"),
) -> Simulator:
    hpc_service = get_simulation_service()
    if hpc_service is None:
        logger.error("HPC service is not initialized")
        raise HTTPException(status_code=500, detail="HPC service is not initialized")

    try:
        latest_commit = await hpc_service.get_latest_commit_hash(git_branch=git_branch, git_repo_url=git_repo_url)
        return Simulator(git_commit_hash=latest_commit, git_repo_url=git_repo_url, git_branch=git_branch)
    except Exception as e:
        logger.exception("Error getting the latest simulator commit.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulator/versions",
    response_model=RegisteredSimulators,
    operation_id="get-core-simulator-version",
    tags=["Simulators"],
    dependencies=[Depends(get_database_service), Depends(get_postgres_engine)],
    summary="get the list of available simulator versions",
)
async def get_simulator_versions() -> RegisteredSimulators:
    sim_db_service = get_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    try:
        simulators = await sim_db_service.list_simulators()
        return RegisteredSimulators(versions=simulators)
    except Exception as e:
        logger.exception("Error getting list of simulation versions")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulator/upload",
    response_model=SimulatorVersion,
    operation_id="insert-core-simulator-version",
    tags=["Simulators"],
    dependencies=[Depends(get_database_service), Depends(get_postgres_engine)],
    summary="Upload a new simulator (vEcoli) version.",
)
async def insert_simulator_version(
    background_tasks: BackgroundTasks,
    simulator: Simulator,
) -> SimulatorVersion:
    # verify simulator request
    verify_simulator_payload(simulator)

    # check parameterized service availabilities
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")

    existing_version = await db_service.get_simulator_by_commit(simulator.git_commit_hash)
    if existing_version is None:
        try:
            return await upload_simulator(
                commit_hash=simulator.git_commit_hash,
                git_repo_url=simulator.git_repo_url,
                git_branch=simulator.git_branch,
                simulation_service_slurm=sim_service,
                database_service=db_service,
                background_tasks=background_tasks,
            )
        except Exception as e:
            logger.exception("Error inserting simulator version.")
            raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        return existing_version


@config.router.post(
    path="/simulation/parca",
    response_model=ParcaDataset,
    operation_id="run-parca",
    tags=["Simulations"],
    summary="Run a parameter calculation",
)
async def run_parameter_calculator(
    background_tasks: BackgroundTasks, parca_request: ParcaDatasetRequest
) -> ParcaDataset:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")

    try:
        return await run_parca(
            simulator=parca_request.simulator_version,
            simulation_service_slurm=sim_service,
            database_service=db_service,
            parca_config=parca_request.parca_config,
            background_tasks=background_tasks,
        )
    except Exception as e:
        logger.exception("Error running PARCA")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulation/parca/versions",
    response_model=list[ParcaDataset],
    operation_id="get-parca-versions",
    tags=["Simulations"],
    summary="Run a parameter calculation",
)
async def get_parcas() -> list[ParcaDataset]:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")

    try:
        return await get_parca_datasets(
            simulation_service_slurm=sim_service,
            database_service=db_service,
        )
    except Exception as e:
        logger.exception("Error running PARCA")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulation/submit",
    response_model=EcoliSimulation,
    operation_id="submit-simulation",
    tags=["Simulations"],
    summary="Submit to the db a single vEcoli simulation with given parameter overrides.",
)
async def submit_simulation(sim_request: EcoliSimulationRequest) -> EcoliSimulation:
    sim_db_service = get_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    try:
        inserted_sim: EcoliSimulation = await sim_db_service.insert_simulation(sim_request)
        # don't wait to submit the job to HPC, just return the simulation object
        return inserted_sim
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulation/run",
    operation_id="run-simulation",
    response_model=EcoliExperiment,
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
)
async def run_vecoli_simulation(
    background_tasks: BackgroundTasks, sim_request: EcoliSimulationRequest
) -> EcoliExperiment:
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")

    try:
        return await run_simulation(
            simulator=sim_request.simulator,
            parca_dataset_id=sim_request.parca_dataset_id,
            database_service=db_service,
            simulation_service_slurm=sim_service,
            router_config=config,
            background_tasks=background_tasks,
        )
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulation/results/chunks",
    response_class=ORJSONResponse,
    operation_id="get-simulation-results",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_ssh_service)],
)
async def get_result_chunks(
    background_tasks: BackgroundTasks,
    observable_names: RequestedObservables,
    experiment_id: str = Query(default="experiment_96bb7a2_id_1_20250620-181422"),
    database_id: int = Query(description="Database Id returned from /submit-simulation"),
    git_commit_hash: str = Query(default=LATEST_COMMIT),
) -> ORJSONResponse:
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    ssh_service = get_ssh_service()
    if ssh_service is None:
        logger.error("SSH service is not initialized")
        raise HTTPException(status_code=500, detail="SSH service is not initialized")
    try:
        service = DataServiceHpc()

        local_dir, lazy_frame = await service.read_simulation_chunks(experiment_id, Namespace.TEST)
        background_tasks.add_task(shutil.rmtree, local_dir)
        selected_cols = observable_names.items if len(observable_names.items) else ["bulk", "^listeners__mass.*"]
        data = (
            lazy_frame.select(
                pl.col(selected_cols)  # regex pattern to match columns starting with this prefix
            )
            .collect()
            .to_dict()
        )
        return ORJSONResponse(content=data)
    except Exception as e:
        logger.exception(f"Error fetching simulation results for id: {database_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulation/results",
    response_class=FileResponse,
    operation_id="get-simulation-results-file",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_ssh_service)],
)
async def get_results(
    background_tasks: BackgroundTasks,
    experiment_id: str = Query(default="experiment_96bb7a2_id_1_20250620-181422"),
    database_id: int = Query(default_factory=int, description="Database Id of simulation"),
) -> FileResponse:
    try:
        service = DataServiceHpc()
        local_dir = await service.read_chunks(experiment_id, Namespace.TEST)
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            zip_path = Path(tmp.name)
            shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=local_dir)
            background_tasks.add_task(shutil.rmtree, local_dir)
        return FileResponse(path=zip_path, filename=f"{experiment_id}_chunks.zip", media_type="application/zip")
    except Exception as e:
        logger.exception(f"Error fetching simulation results for id: {database_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulation/status",
    response_model=WorkerEvent,
    operation_id="get-simulation-status",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
)
async def get_simulation_status(
    simulation_id: int = Query(...), num_events: int | None = Query(default=None)
) -> list[WorkerEvent]:
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    db_service = get_database_service()
    if db_service is None:
        logger.error("SSH service is not initialized")
        raise HTTPException(status_code=500, detail="SSH service is not initialized")
    # experiment_dir = Path("/home/FCAM/svc_vivarium/test/sims/experiment_96bb7a2_id_1_20250620-181422")
    try:
        simulation_hpcrun: HpcRun | None = await db_service.get_hpcrun_by_ref(
            ref_id=simulation_id, job_type=JobType.SIMULATION
        )
        if simulation_hpcrun:
            worker_events = await db_service.list_worker_events(hpcrun_id=simulation_hpcrun.database_id)
            return worker_events[:num_events] if num_events else worker_events
        else:
            return []
    except Exception as e:
        logger.exception(f"Error fetching simulation results for simulation id: {simulation_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e
