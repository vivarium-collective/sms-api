import logging
import os
import shutil
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import StrEnum
from pathlib import Path

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query

# import pyarrow.parquet as pq
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

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
from sms_api.simulation.hpc_utils import (
    format_experiment_path,
    get_experiment_dirname,
)
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
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
    git_commit_hash: str | None = Query(default=None, description="First 7 characters of git commit hash"),
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
    path="/submit_simulation",
    response_model=EcoliSimulation,
    operation_id="submit_simulation",
    tags=["Simulations"],
    summary="Submit a single vEcoli simulation with given parameter overrides.",
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
        hpc_sim_service = SimulationServiceHpc()
        if sim_request.simulator.git_commit_hash is None:
            sim_request.simulator.git_commit_hash = await hpc_sim_service.get_latest_commit_hash()

        inserted_sim: EcoliSimulation = await submit_simulation(sim_request=sim_request)

        await hpc_sim_service.submit_ecoli_simulation_job(
            ecoli_simulation=inserted_sim, simulation_database_service=sim_db_service
        )

        # await asyncio.sleep(2.0)
        # hpc_run = await sim_db_service.get_hpcrun_by_slurmjobid(slurmjobid=slurm_job_id)
        # if hpc_run is not None:
        #     inserted_sim.hpc_run = hpc_run

        return inserted_sim
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


class ResultsPath(BaseModel):
    remote: str


@app.get(
    path="/get-results-path",
    # response_model=HpcRun,
    operation_id="get-results-path",
    tags=["Simulations"],
    # dependencies=[Depends(get_simulation_database_service), Depends(get_postgres_engine)],
)
async def get_results_path(build_job_id: int, git_commit_hash: str) -> ResultsPath:
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    ssh_service = get_ssh_service()
    if ssh_service is None:
        logger.error("SSH service is not initialized")
        raise HTTPException(status_code=500, detail="SSH service is not initialized")
    try:
        # slurm_job = None
        # start_time = time.time()
        # while start_time + 60 > time.time():
        #     slurm_job = await sim_service.get_slurm_job_status(slurmjobid=build_job_id)
        #     # case: results are readable
        #     if slurm_job is not None and slurm_job.is_done():
        #         break
        #     await asyncio.sleep(5)

        hpc_settings = get_settings()
        experiment_dirname = get_experiment_dirname(build_job_id, git_commit_hash)
        remote_dir_root = format_experiment_path(hpc_settings, experiment_dirname)
        remote_dirpath = get_single_simulation_chunks_dirpath(remote_dir_root)

        local_dirpath = os.path.join(tempfile.mkdtemp(), experiment_dirname)
        shutil.rmtree(local_dirpath)
        return ResultsPath(**{"remote": remote_dirpath})
    except Exception as e:
        logger.exception(f"Error fetching simulation results for job id: {build_job_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e


def get_single_simulation_chunks_dirpath(remote_dir_root: Path) -> str:
    experiment_dirname = str(remote_dir_root).split("/")[-1]
    return os.path.join(
        remote_dir_root,
        "history",
        f"'experiment_id={experiment_dirname}",
        "'variant=0'",
        "'lineage_seed=0'",
        "'generation=1'",
        "'agent_id=0'",
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


# async def read_chunk(chunk_id: int):
#     fp = f"{chunk_id}.pq"
#     return pq.read_table(fp)


# @app.get(
#     path="/get-run",
#     # response_model=HpcRun,
#     operation_id="get-run",
#     tags=["Simulations"],
#     dependencies=[Depends(get_simulation_database_service), Depends(get_postgres_engine)],
# )
# async def get_results(hpc_run_id: str = Query(...)):
#     try:
#         results = {}
#
#         # 1. get ssh service
#         ssh_svc: SSHService = get_ssh_service()
#
#         # 2. create slurm service with ssh svc
#
#         # 3. parse parent output dir filepath using run id
#
#         # 4. scp_download with slurm svc the appropriate pq file from #3
#
#         # 5.
#         results = {}
#         outdir = get_outdir_from_hpc(ssh_svc, hpc_run_id)
#         chunk_paths = os.listdir(outdir)
#         for fname in chunk_paths:
#             remote_chunk_path = Path(os.path.join(outdir, fname))
#             local_chunk_path = Path(os.path.join(tempfile.mkdtemp(), fname))
#             await ssh_svc.scp_download(local_file=local_path, remote_path=remote_chunk_path)
#             df = pq.read_table(local_chunk_path).to_pandas()
#             results[fname.split(".")[0]] = df.to_dict()
#
#         return results
#     except HTTPException as e:
#         logger.exception("Error running PARCA")
#         raise HTTPException(status_code=500, detail=str(e)) from e


# @app.get(path="/check-services", operation_id="check-services", response_model=ServiceStatuses)
# async def check_services():
#     conf = {}
#     for stype in ServiceTypes.all():
#         try:
#             _service = get_service(stype)
#             status = ServiceStatuses.UP
#         except HTTPException as e:
#             status = ServiceStatuses.down(str(e))
#         conf[stype.value] = status
#     return ServiceStatuses(**conf)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104 binding to all interfaces
    logger.info("API Gateway Server started")
