"""
- base sim (cached)
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

import io
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import StrEnum
from pathlib import Path

import pandas as pd
import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

# import pyarrow.parquet as pq
from starlette.middleware.cors import CORSMiddleware

from sms_api.common.hpc.sim_utils import get_single_simulation_chunks_dirpath, read_latest_commit
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import get_settings
from sms_api.dependencies import (
    get_postgres_engine,
    get_simulation_database_service,
    get_simulation_service,  # as _get_simulation_service,
    init_standalone,
    shutdown_standalone,
)
from sms_api.log_config import setup_logging
from sms_api.simulation.database_service import SimulationDatabaseService
from sms_api.simulation.dispatch import run_simulation
from sms_api.simulation.hpc_utils import format_experiment_path, get_experiment_dirname
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    EcoliSimulationRun,
    ParcaDataset,
    ParcaDatasetRequest,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationServiceHpc
from sms_api.simulation.tables_orm import JobType
from sms_api.version import __version__

logger = logging.getLogger(__name__)
setup_logging(logger)


class ServerModes(StrEnum):
    DEV = "http://localhost:3001"
    PROD = "https://sms.cam.uchc.edu"


def get_server_url(dev: bool = True) -> ServerModes:
    return ServerModes.DEV if dev else ServerModes.PROD


# -- constraints -- #
APP_VERSION = __version__
APP_TITLE = "sms-api"
APP_ORIGINS = [
    "http://0.0.0.0:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:4200",
    "http://127.0.0.1:4201",
    "http://127.0.0.1:4202",
    "http://localhost:4200",
    "http://localhost:4201",
    "http://localhost:4202",
    "http://localhost:8000",
    "http://localhost:3001",
]
SERVER_URL = get_server_url(dev=True)

APP_SERVERS: list[dict[str, str]] = [
    # {"url": PROD_SERVER_URL, "description": "Production server"},
    # {"url": DEV_SERVER_URL, "description": "Main Development server"},
]

# -- app components -- #

router = APIRouter()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    await init_standalone()
    yield
    await shutdown_standalone()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, servers=APP_SERVERS, lifespan=lifespan)

# add origins
app.add_middleware(
    CORSMiddleware, allow_origins=APP_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# -- endpoint logic -- #


class ServiceTypes(StrEnum):
    SIMULATION = "simulation"
    DATABASE = "database"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.SIMULATION, cls.DATABASE]


class ServiceStatuses(StrEnum):
    UP = "running"
    DOWN = "not running"

    @classmethod
    def down(cls, reason: str) -> str:
        return f"{cls.DOWN}: {reason}"


# def check_service(service_type: ServiceTypes):
#     def decorator(service_getter):
#         def wrapper(*args, **kwargs):
#             service = service_getter()
#             if service is None:
#                 service_type = kwargs['service_type']
#                 logger.error(f"{service_type} service is not initialized")
#                 raise HTTPException(status_code=500, detail=f"{service_type} service is not initialized")
#             return service
#         return wrapper
#     return decorator
#
#
# @check_service(service_type=ServiceTypes.DATABASE)
# async def get_database_service():
#     return get_simulation_database_service()
#
#
# @check_service(service_type=ServiceTypes.SIMULATION)
# async def get_simulation_service():
#     return _get_simulation_service()


@app.get("/")
def root() -> dict[str, str]:
    return {"docs": f"{SERVER_URL}{app.docs_url}", "version": APP_VERSION}


@app.get("/version")
def get_version() -> str:
    return APP_VERSION


@app.get(
    path="/simulator_version",
    response_model=list[SimulatorVersion],
    operation_id="get-simulator-version",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_database_service), Depends(get_postgres_engine)],
    summary="get the list of available simulator versions",
)
async def get_simulator_versions() -> list[SimulatorVersion]:
    sim_db_service = get_simulation_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    try:
        return await sim_db_service.list_simulators()
    except Exception as e:
        logger.exception("Error getting list of simulation versions")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    path="/simulator_version",
    response_model=SimulatorVersion,
    operation_id="insert-simulator-version",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_database_service), Depends(get_postgres_engine)],
    summary="Upload a new simulator (vEcoli) version.",
)
async def insert_simulator_version(
    git_commit_hash: str = Query(
        default_factory=read_latest_commit, description="First 7 characters of git commit hash"
    ),
    git_repo_url: str = Query(default="https://github.com/CovertLab/vEcoli"),
    git_branch: str = Query(default="master"),
) -> SimulatorVersion:
    # check parameterized service availabilities
    sim_db_service: SimulationDatabaseService | None = get_simulation_database_service()
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

    # use commit hash or latest hash
    commit_hash = git_commit_hash or await hpc_service.get_latest_commit_hash()

    try:
        simulator_version = await sim_db_service.insert_simulator(
            git_commit_hash=commit_hash, git_repo_url=git_repo_url, git_branch=git_branch
        )
        await sim_service.clone_repository_if_needed(
            git_commit_hash=commit_hash, git_repo_url=git_repo_url, git_branch=git_branch
        )
        build_job_id = await sim_service.submit_build_image_job(simulator_version=simulator_version)
        _hpc_run = await sim_db_service.insert_hpcrun(job_type=JobType.BUILD_IMAGE, slurmjobid=build_job_id)
        # TODO: stick hpc run into simulator version record in DB
        return simulator_version
    except Exception as e:
        logger.exception("Error inserting simulator version.")
        raise HTTPException(status_code=500, detail=str(e)) from e


# new endpoint for slurm_job = await sim_service.get_slurm_job_status(slurmjobid=build_job_id)


@app.post(
    path="/vecoli_parca",
    response_model=ParcaDataset,
    operation_id="calculate_parameters",
    tags=["Simulations"],
    summary="Run a parameter calculation",
)
async def run_parca(parca_request: ParcaDatasetRequest) -> ParcaDataset:
    sim_db_service = get_simulation_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    try:
        parca_dataset: ParcaDataset = await sim_db_service.get_or_insert_parca_dataset(parca_request)
        return parca_dataset
    except Exception as e:
        logger.exception("Error running PARCA")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    path="/vecoli_simulation",
    response_model=EcoliSimulation,
    operation_id="submit-simulation",
    tags=["Simulations"],
    summary="Submit to the db a single vEcoli simulation with given parameter overrides.",
)
async def submit_simulation(sim_request: EcoliSimulationRequest) -> EcoliSimulation:
    sim_db_service = get_simulation_database_service()
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


@app.post(
    path="/run-simulation",
    response_model=EcoliSimulationRun,
    operation_id="run-simulation",
    tags=["Simulations"],
    summary="Run a single vEcoli simulation with given parameter overrides",
)
async def run_wcm_simulation(sim_request: EcoliSimulationRequest) -> EcoliSimulationRun:
    sim_db_service = get_simulation_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")

    hpc_sim_service = SimulationServiceHpc()
    if sim_request.simulator.git_commit_hash is None:
        sim_request.simulator.git_commit_hash = await hpc_sim_service.get_latest_commit_hash()

    try:
        inserted_sim, sim_job_id = await run_simulation(hpc_sim_service, sim_db_service)
        return EcoliSimulationRun(job_id=sim_job_id, simulation=inserted_sim)
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get(
    path="/get-results",
    # response_model=HpcRun,
    operation_id="get-results",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_ssh_service)],
)
async def get_results(
    database_id: int = Query(description="Database Id returned from /submit-simulation"),
    git_commit_hash: str = Query(default=read_latest_commit()),
) -> None:
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    ssh_service = get_ssh_service()
    if ssh_service is None:
        logger.error("SSH service is not initialized")
        raise HTTPException(status_code=500, detail="SSH service is not initialized")
    try:
        hpc_service = SimulationServiceHpc()
        latest_commit = await hpc_service.get_latest_commit_hash()
        if latest_commit != git_commit_hash:
            git_commit_hash = latest_commit
        pass
    except Exception as e:
        logger.exception(f"Error fetching simulation results for id: {database_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def generate_chunk_stream(simulator: SimulatorVersion, database_id: int, chunk_id: int) -> StreamingResponse:
    experiment_dirname = get_experiment_dirname(database_id, simulator.git_commit_hash)
    experiment_dir_root = format_experiment_path(get_settings(), experiment_dirname)
    remote_dirpath: Path = get_single_simulation_chunks_dirpath(
        experiment_dir_root
    )  # eg: experiment_dirname/'experiment=....', etc
    stream = io.StringIO()
    df = pd.read_parquet(f"{remote_dirpath}/{chunk_id}.pq")
    stream.write(df.to_json())
    stream.seek(0)  # Reset cursor to start
    return StreamingResponse(
        stream, media_type="application/json", headers={"Content-Disposition": "attachment; filename=data.json"}
    )


# @app.post(
#     path="/vecoli_simulation",
#     response_model=EcoliSimulation,
#     operation_id="run_simulation",
#     tags=["Simulations"],
#     summary="Run a single vEcoli simulation with given parameter overrides",
# )
# async def run_simulation(sim_request: EcoliSimulationRequest) -> EcoliSimulation:
#     sim_db_service = get_simulation_database_service()
#     if sim_db_service is None:
#         logger.error("Simulation database service is not initialized")
#         raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
#
#     try:
#         inserted_sim: EcoliSimulation = await sim_db_service.insert_simulation(sim_request)
#         # don't wait to submit the job to HPC, just return the simulation object
#         return inserted_sim
#     except Exception as e:
#         logger.exception("Error running vEcoli simulation")
#         raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104 binding to all interfaces
    logger.info("API Gateway Server started")
