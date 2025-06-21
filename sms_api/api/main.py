from enum import StrEnum
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import typing

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from starlette.middleware.cors import CORSMiddleware

from sms_api.dependencies import (
    get_postgres_engine,
    get_simulation_database_service,
    get_simulation_service,
    init_standalone,
    shutdown_standalone,
)
from sms_api.log_config import setup_logging
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    HpcRun,
    ParcaDataset,
    ParcaDatasetRequest,
    SimulatorVersion,
)
from sms_api.simulation.simulation_database import SimulationDatabaseService
from sms_api.simulation.simulation_service import SimulationService
from sms_api.simulation.tables_orm import JobType
from sms_api.version import __version__

logger = logging.getLogger(__name__)
setup_logging(logger)

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
APP_SERVERS: list[dict[str, str]] = [
    # {"url": "https://sms.cam.uchc.edu", "description": "Production server"},
    # {"url": "http://localhost:3001", "description": "Main Development server"},
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


# base sim (cached)
# antibiotic
# biomanufacturing
# batch variant endpoint
# design specific endpoints.
# downsampling ...
# biocyc id
# api to download the data
# marimo instead of Jupyter notebooks....(auth). ... also on gov cloud.
# endpoint to send sql like queries to parquet files back to client


@app.get("/")
def root() -> dict[str, str]:
    return {"docs": f"{app.docs_url}", "version": APP_VERSION}


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


@app.get(
    path="/get-run",
    response_model=HpcRun,
    operation_id="get-run",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_database_service), Depends(get_postgres_engine)]
)
async def get_run(hpc_run_id: str = Query(...)) -> HpcRun:
    pass 


class Services(StrEnum):
    SIMULATION="simulation"
    DATABASE="database"


def get_service(service_type: Services) -> SimulationDatabaseService | SimulationService:
    service = None
    if service_type == "database":
        service = get_simulation_database_service()
    elif service_type == "simulation":
        service = get_simulation_service()
    if service is None:
        logger.error(f"{service_type.value} service is not initialized")
        raise HTTPException(status_code=500, detail=f"{service_type.value} service is not initialized")
    else:
        return service
    

@app.get(
    path="/check-services",
    operation_id="check-services"
)
async def check_services():
    conf = {}
    service_types = [Services.SIMULATION, Services.DATABASE]
    for stype in service_types:
        try:
            service = get_service(stype)
            conf[stype.value] = "UP"
        except HTTPException as e:
            conf[stype.value] = str(e)
    return conf
    

@app.post(
    path="/simulator_version",
    response_model=SimulatorVersion,
    operation_id="insert-simulator-version",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_database_service), Depends(get_postgres_engine)],
    summary="Upload a new simulator (vEcoli) version."
)
async def insert_simulator_version(
    git_commit_hash: str = Query(..., description="First 7 characters of git commit hash"),
    git_repo_url: str = Query(default="https://github.com/CovertLab/vEcoli"),
    git_branch: str = Query(default="master"),
) -> SimulatorVersion:
    # TODO: after insert,
    # TODO: check hash length
    sim_db_service: SimulationDatabaseService | None = get_simulation_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")

    try:
        simulator_version = await sim_db_service.insert_simulator(
            git_commit_hash=git_commit_hash, git_repo_url=git_repo_url, git_branch=git_branch
        )
        await sim_service.clone_repository_if_needed(
            git_commit_hash=git_commit_hash, git_repo_url=git_repo_url, git_branch=git_branch
        )
        build_job_id = await sim_service.submit_build_image_job(simulator_version=simulator_version)
        _hpc_run = await sim_db_service.insert_hpcrun(job_type=JobType.BUILD_IMAGE, slurmjobid=build_job_id)
        # TODO: stick hpc run into simulator version record in DB
        return simulator_version
        # assert job_id is not None
        # start_time = time.time()
        # while start_time + 60 > time.time():
        #     slurm_job = await sim_service.get_slurm_job_status(slurmjobid=build_job_id)
        #     if slurm_job is not None and slurm_job.is_done():
        #         break
        #     await asyncio.sleep(5)
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
    operation_id="run_simulation",
    tags=["Simulations"],
    summary="Run a single vEcoli simulation with given parameter overrides",
)
async def run_simulation(sim_request: EcoliSimulationRequest) -> EcoliSimulation:
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104 binding to all interfaces
    logger.info("Server started")
