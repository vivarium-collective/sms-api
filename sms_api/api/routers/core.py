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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

# from sms_api.api.request_examples import examples
from sms_api.common.gateway.models import RouterConfig, ServerMode
from sms_api.dependencies import (
    get_database_service,
    get_db_engine,
    get_simulation_service,
)
from sms_api.simulation import core_handlers
from sms_api.simulation.hpc_utils import read_latest_commit
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    HpcRun,
    JobType,
    ParcaDataset,
    ParcaDatasetRequest,
    RegisteredSimulators,
    Simulator,
    SimulatorVersion,
    WorkerEvent,
)

logger = logging.getLogger(__name__)

LATEST_COMMIT = read_latest_commit()


def get_server_url(dev: bool = True) -> ServerMode:
    return ServerMode.DEV if dev else ServerMode.PROD


# -- app components -- #

# TODO: mount nfs driver


config = RouterConfig(router=APIRouter(), prefix="/core", dependencies=[])


@config.router.get(
    path="/simulator/latest",
    response_model=Simulator,
    operation_id="get-latest-simulator",
    tags=["EcoliSim"],
    dependencies=[Depends(get_database_service), Depends(get_db_engine)],
    summary="Get the latest simulator version",
)
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
    operation_id="get-simulator-versions",
    tags=["EcoliSim"],
    dependencies=[Depends(get_database_service), Depends(get_db_engine)],
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


@config.router.get(
    path="/simulator/status",
    response_model=HpcRun,
    operation_id="get-simulator-status",
    tags=["EcoliSim"],
    summary="Get simulator container build status by its ID",
)
async def get_simulator_status(simulator_id: int) -> HpcRun | None:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    try:
        simulation_hpcrun: HpcRun | None = await db_service.get_hpcrun_by_ref(
            ref_id=simulator_id, job_type=JobType.BUILD_IMAGE
        )
    except Exception as e:
        logger.exception(f"Error fetching simulation results for simulator container build with id: {simulator_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e

    if simulation_hpcrun is None:
        raise HTTPException(status_code=404, detail=f"Simulator container build with id {simulator_id} not found.")
    return simulation_hpcrun


@config.router.post(
    path="/simulator/upload",
    response_model=SimulatorVersion,
    operation_id="insert-simulator-version",
    tags=["EcoliSim"],
    dependencies=[Depends(get_database_service), Depends(get_db_engine)],
    summary="Upload a new simulator (vEcoli) version.",
)
async def insert_simulator_version(
    background_tasks: BackgroundTasks,
    simulator: Simulator,
) -> SimulatorVersion:
    # verify simulator request
    core_handlers.verify_simulator_payload(simulator)

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
            return await core_handlers.upload_simulator(
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
    tags=["EcoliSim"],
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
        return await core_handlers.run_parca(
            simulator=parca_request.simulator_version,
            simulation_service_slurm=sim_service,
            database_service=db_service,
            parca_config=parca_request.parca_config,
            background_tasks=background_tasks,
        )
    except Exception as e:
        logger.exception("Error running PARCA")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulation/parca/versions",
    response_model=list[ParcaDataset],
    operation_id="get-parca-versions",
    tags=["EcoliSim"],
    summary="Get list of parca calculations",
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
        return await core_handlers.get_parca_datasets(
            simulation_service_slurm=sim_service,
            database_service=db_service,
        )
    except Exception as e:
        logger.exception("Error running PARCA")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulation/parca/status",
    response_model=HpcRun,
    operation_id="get-parca-status",
    tags=["EcoliSim"],
    summary="Get parca calculation status by its ID",
)
async def get_parca_status(parca_id: int) -> HpcRun | None:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    try:
        simulation_hpcrun: HpcRun | None = await db_service.get_hpcrun_by_ref(ref_id=parca_id, job_type=JobType.PARCA)
    except Exception as e:
        logger.exception(f"Error fetching simulation results for parca id: {parca_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e

    if simulation_hpcrun is None:
        raise HTTPException(status_code=404, detail=f"Parca with id {parca_id} not found.")
    return simulation_hpcrun


@config.router.post(
    path="/simulation/run",
    operation_id="run-ecolisim",
    response_model=EcoliSimulation,
    tags=["EcoliSim"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="Run a vEcoli EcoliSim simulation",
)
async def run_simulation(sim_request: EcoliSimulationRequest) -> EcoliSimulation:
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")

    try:
        return await core_handlers.run_simulation(
            simulator=sim_request.simulator,
            parca_dataset_id=sim_request.parca_dataset_id,
            database_service=db_service,
            simulation_service_slurm=sim_service,
            variant_config=sim_request.variant_config,
        )
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulation/run/versions",
    response_model=list[EcoliSimulation],
    operation_id="get-simulation-versions",
    tags=["EcoliSim"],
    summary="Get list of vEcoli simulations",
)
async def get_simulation_versions() -> list[EcoliSimulation]:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    try:
        simulations: list[EcoliSimulation] = await db_service.list_simulations()
        return simulations
    except Exception as e:
        logger.exception("Error running PARCA")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulation/run/status",
    response_model=HpcRun,
    operation_id="get-simulation-status",
    tags=["EcoliSim"],
    dependencies=[Depends(get_database_service)],
    summary="Get the simulation status record by its ID",
)
async def get_simulation_status(
    simulation_id: int = Query(...), num_events: int | None = Query(default=None)
) -> HpcRun:
    db_service = get_database_service()
    if db_service is None:
        logger.error("SSH service is not initialized")
        raise HTTPException(status_code=500, detail="SSH service is not initialized")
    # experiment_dir = Path("/home/FCAM/svc_vivarium/test/sims/experiment_96bb7a2_id_1_20250620-181422")
    try:
        simulation_hpcrun: HpcRun | None = await db_service.get_hpcrun_by_ref(
            ref_id=simulation_id, job_type=JobType.SIMULATION
        )
    except Exception as e:
        logger.exception(f"Error fetching simulation results for simulation id: {simulation_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e

    if simulation_hpcrun is None:
        raise HTTPException(status_code=404, detail=f"Simulation with id {simulation_id} not found.")
    return simulation_hpcrun


@config.router.get(
    path="/simulation/run/events",
    response_model=list[WorkerEvent],
    operation_id="get-simulation-worker-events",
    tags=["EcoliSim"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="Get the worker events for a simulation by its ID",
)
async def get_simulation_worker_events(
    simulation_id: int = Query(...),
    num_events: int | None = Query(default=None),
    prev_sequence_number: int | None = Query(default=None),
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
        logger.info(f"Simulation HPC RUN: {simulation_hpcrun}")
        if simulation_hpcrun:
            worker_events = await db_service.list_worker_events(
                hpcrun_id=simulation_hpcrun.database_id,
                prev_sequence_number=prev_sequence_number,
            )
            return worker_events[:num_events] if num_events else worker_events
        else:
            return []
    except Exception as e:
        logger.exception(f"Error fetching simulation results for simulation id: {simulation_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e
