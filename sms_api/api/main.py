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
import json
import logging
import os
import shutil
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

import pandas as pd
import polars as pl
import uvicorn
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, ORJSONResponse, StreamingResponse
from starlette.middleware.cors import CORSMiddleware

from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.dependencies import (
    get_database_service,
    get_postgres_engine,
    get_simulation_service,
    init_standalone,
    shutdown_standalone,
)
from sms_api.log_config import setup_logging
from sms_api.simulation.data_service import DataServiceHpc
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import format_experiment_path, get_experiment_dirname, read_latest_commit
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    HpcRun,
    Namespaces,
    ParcaDataset,
    ParcaDatasetRequest,
    ServerModes,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationServiceHpc
from sms_api.simulation.tables_orm import JobType
from sms_api.version import __version__

logger = logging.getLogger(__name__)
setup_logging(logger)


def get_server_url(dev: bool = True) -> ServerModes:
    return ServerModes.DEV if dev else ServerModes.PROD


# -- constraints -- #
LATEST_COMMIT = read_latest_commit()
APP_VERSION = __version__
APP_TITLE = "sms-api"
APP_ORIGINS = [
    "http://0.0.0.0:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8888",
    "http://127.0.0.1:4200",
    "http://127.0.0.1:4201",
    "http://127.0.0.1:4202",
    "http://localhost:4200",
    "http://localhost:4201",
    "http://localhost:4202",
    "http://localhost:8888",
    "http://localhost:3001",
]
SERVER_URL = get_server_url(dev=True)

APP_SERVERS: list[dict[str, str]] = [
    {"url": ServerModes.PROD, "description": "Production server"},
    {"url": ServerModes.DEV, "description": "Main Development server"},
]

# -- app components -- #

# TODO: mount nfs driver
# TODO:
router = APIRouter()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    dev_mode_warning = None
    dev_mode = os.getenv("DEV_MODE", "0")
    start_standalone = partial(init_standalone)
    if bool(int(dev_mode)):
        dev_mode_warning = "Development Mode is currently engaged!!!"
        start_standalone.keywords["enable_ssl"] = False
    await start_standalone()
    if dev_mode_warning:
        logger.warning("Development Mode is currently engaged!!!", stacklevel=1)
    yield
    await shutdown_standalone()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, servers=APP_SERVERS, lifespan=lifespan)

# add origins
app.add_middleware(
    CORSMiddleware, allow_origins=APP_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# -- endpoint logic -- #


@app.get("/")
async def root() -> dict[str, str]:
    return {"docs": f"{SERVER_URL}{app.docs_url}", "version": APP_VERSION}


@app.get("/version")
async def get_version() -> str:
    return APP_VERSION


@app.get("/latest-simulator-hash", operation_id="latest-simulator-hash", tags=["Simulations"])
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


@app.get(
    path="/simulator_version",
    response_model=list[SimulatorVersion],
    operation_id="get-simulator-version",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service), Depends(get_postgres_engine)],
    summary="get the list of available simulator versions",
)
async def get_simulator_versions() -> list[SimulatorVersion]:
    sim_db_service = get_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    try:
        return await sim_db_service.list_simulators()
    except Exception as e:
        logger.exception("Error getting list of simulation versions")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    path="/insert-simulator-version",
    response_model=SimulatorVersion,
    operation_id="insert-simulator-version",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service), Depends(get_postgres_engine)],
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

        # dispatch new build job to hpc/worker
        build_job_id = await sim_service.submit_build_image_job(simulator_version=simulator_version)

        # create reciept and record of build job in the db
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
        # now, use sim service to run the parca job(submit)
        # then return
        return parca_dataset

    except Exception as e:
        logger.exception("Error running PARCA")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    path="/submit-simulation",
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


@app.post(
    path="/run-simulation",
    response_model=EcoliSimulation,
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
)
async def run_vecoli_simulation(sim_request: EcoliSimulationRequest):
    try:
        simulation_service_slurm = get_simulation_service()
        database_service = get_database_service()
        simulation = await submit_simulation(sim_request=sim_request)
        sim_job_id = await simulation_service_slurm.submit_ecoli_simulation_job(
            ecoli_simulation=simulation, simulation_database_service=database_service
        )
        assert sim_job_id is not None
        return simulation
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    path="/get-results",
    response_class=ORJSONResponse,
    operation_id="get-results",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_ssh_service)],
)
async def get_results(
    background_tasks: BackgroundTasks,
    observable_names: list[str] = Query(..., default_factory=list),
    experiment_id: str = Query(default="experiment_96bb7a2_id_1_20250620-181422"),
    database_id: int = Query(description="Database Id returned from /submit-simulation"),
    git_commit_hash: str = Query(default=LATEST_COMMIT),
):
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

        local_dir, lazy_frame = await service.read_simulation_chunks(experiment_id, Namespaces.TEST)
        background_tasks.add_task(shutil.rmtree, local_dir)
        data = (
            lazy_frame.select(
                pl.col(["bulk", "^listeners__mass.*"])  # regex pattern to match columns starting with this prefix
            )
            .collect()
            .to_dict()
        )
        return ORJSONResponse(content=data)
    except Exception as e:
        logger.exception(f"Error fetching simulation results for id: {database_id}.")
        raise HTTPException(status_code=500, detail=str(e)) from e


# mount remote drives as persistent volume


@app.get(
    path="/get-simulation-status",
    response_model=HpcRun,
    operation_id="get-simulation-status",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
)
async def get_simulation_status(
    simulation_id: int = Query(...),
):
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
        simulation: EcoliSimulation = await db_service.get_simulation(simulation_id=simulation_id)
        slurm_job_sim = await sim_service.get_slurm_job_status(slurmjobid=sim_job_id)
        # poll for job status
        start_time = time.time()
        while start_time + 60 > time.time():
            if slurm_job_sim is not None and slurm_job_sim.is_done():
                break
            await asyncio.sleep(5)

        # stream = io.StringIO()
        # stream.write(df.write_json())
        # stream.seek(0)  # Reset cursor to start
        # return StreamingResponse(
        #     stream, media_type="application/json", headers={"Content-Disposition": "attachment; filename=data.json"}
        # )
        end = time.time()
        exec_duration = end - start
        logger.info(f"Duration: {exec_duration}")

        # return StreamingResponse(io.StringIO(df.write_ndjson()), media_type="application/x-ndjson")
        return JSONResponse(content=json.loads(df.write_json()))
    except Exception as e:
        logger.exception(f"Error fetching simulation results for test dir: {experiment_dir}.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/read-chunk")
async def read_chunk(pq_path: str = Query("assets/tests/test_history/1200.pq")):
    df = pl.scan_parquet(pq_path).collect(engine="streaming")
    return StreamingResponse(io.StringIO(df.write_ndjson()), media_type="application/x-ndjson")


async def generate_chunk_stream(git_commit_hash: str, database_id: int, chunk_id: int) -> StreamingResponse:
    experiment_dirname = get_experiment_dirname(database_id, git_commit_hash)
    experiment_dir_root = format_experiment_path(experiment_dirname)
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104 binding to all interfaces
    logger.info("API Gateway Server started")
