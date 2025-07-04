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
from pathlib import Path

import polars as pl
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse

from sms_api.common.gateway.gateway_utils import dispatch_build_job
from sms_api.common.gateway.models import Namespace, RouterConfig, ServerMode
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.dependencies import (
    get_database_service,
    get_postgres_engine,
    get_simulation_service,
)
from sms_api.log_config import setup_logging
from sms_api.simulation.data_service import DataServiceHpc
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import read_latest_commit
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    HpcRun,
    JobType,
    ParcaDataset,
    ParcaDatasetRequest,
    RegisteredSimulators,
    RequestedObservables,
    SimulatorVersion,
    WorkerEvent,
)
from sms_api.simulation.simulation_service import SimulationServiceHpc

logger = logging.getLogger(__name__)
setup_logging(logger)

LATEST_COMMIT = read_latest_commit()


def get_server_url(dev: bool = True) -> ServerMode:
    return ServerMode.DEV if dev else ServerMode.PROD


# -- app components -- #

# TODO: mount nfs driver


config = RouterConfig(router=APIRouter(), prefix="/core", dependencies=[])


@config.router.get("/simulator/latest", operation_id="latest-simulator-hash", tags=["Simulations"])
async def get_latest_simulator_hash(
    git_repo_url: str = Query(default="https://github.com/CovertLab/vEcoli"),
    git_branch: str = Query(default="master"),
) -> str:
    hpc_service = SimulationServiceHpc()
    if hpc_service is None:
        logger.error("HPC service is not initialized")
        raise HTTPException(status_code=500, detail="HPC service is not initialized")

    try:
        latest_commit = await hpc_service.get_latest_commit_hash(git_branch=git_branch, git_repo_url=git_repo_url)
        return latest_commit
    except Exception as e:
        logger.exception("Error getting the latest simulator commit.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulator/versions",
    response_model=RegisteredSimulators,
    operation_id="get-simulator-version",
    tags=["Simulations"],
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
    operation_id="insert-simulator-version",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service), Depends(get_postgres_engine)],
    summary="Upload a new simulator (vEcoli) version.",
)
async def insert_simulator_version(
    background_tasks: BackgroundTasks,
    git_commit_hash: str = Query(default="12bdd5e", description="First 7 characters of git commit hash"),
    git_repo_url: str = Query(default="https://github.com/CovertLab/vEcoli"),  # TODO: can this be arbitrarily aliased?
    git_branch: str = Query(default="master"),
) -> SimulatorVersion:
    if not git_repo_url == "https://github.com/CovertLab/vEcoli":
        raise HTTPException(status_code=404, detail="You may not upload a simulator from any other source.")

    # check parameterized service availabilities
    sim_db_service: DatabaseService | None = get_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    hpc_service = SimulationServiceHpc()
    if hpc_service is None:
        logger.error("HPC service is not initialized")
        raise HTTPException(status_code=500, detail="HPC service is not initialized")

    try:
        # clone latest commit/version
        await sim_service.clone_repository_if_needed(
            git_commit_hash=git_commit_hash, git_repo_url=git_repo_url, git_branch=git_branch
        )

        # insert new simulator record
        simulator_version: SimulatorVersion = await sim_db_service.insert_simulator(
            git_commit_hash=git_commit_hash, git_repo_url=git_repo_url, git_branch=git_branch
        )

        # either use background tasks or directly call _hpc_run = await dispatch_build_job(...)
        background_tasks.add_task(dispatch_build_job, sim_service, sim_db_service, simulator_version)
        return simulator_version
    except Exception as e:
        logger.exception("Error inserting simulator version.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/vecoli/parca",
    response_model=ParcaDataset,
    operation_id="run-parca",
    tags=["Simulations"],
    summary="Run a parameter calculation",
)
async def run_parca(parca_request: ParcaDatasetRequest) -> ParcaDataset:
    sim_db_service = get_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")

    try:
        parca_dataset: ParcaDataset = await sim_db_service.get_or_insert_parca_dataset(parca_request)
        parca_job_id = await sim_service.submit_parca_job(parca_dataset)
        _hpc_run = await sim_db_service.insert_hpcrun(
            job_type=JobType.PARCA, slurmjobid=parca_job_id, ref_id=parca_dataset.database_id
        )

        return parca_dataset
    except Exception as e:
        logger.exception("Error running PARCA")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/vecoli/submit",
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
    path="/vecoli/run",
    operation_id="run-simulation",
    response_model=EcoliSimulation,
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
)
async def run_vecoli_simulation(sim_request: EcoliSimulationRequest) -> EcoliSimulation:
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")

    try:
        simulation: EcoliSimulation = await db_service.insert_simulation(sim_request)
        slurm_jobid = await sim_service.submit_ecoli_simulation_job(
            ecoli_simulation=simulation, database_service=db_service
        )
        _hpc_run = await db_service.insert_hpcrun(
            job_type=JobType.PARCA, slurmjobid=slurm_jobid, ref_id=simulation.database_id
        )
        return simulation
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/vecoli/results",
    response_class=ORJSONResponse,
    operation_id="get-simulation-results",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_ssh_service)],
)
async def get_results(
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


# mount remote drives as persistent volume


@config.router.get(
    path="/vecoli/status",
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

    experiment_dir = Path("/home/FCAM/svc_vivarium/test/sims/experiment_96bb7a2_id_1_20250620-181422")
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
        logger.exception(f"Error fetching simulation results for test dir: {experiment_dir}.")
        raise HTTPException(status_code=500, detail=str(e)) from e
