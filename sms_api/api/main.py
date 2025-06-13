import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import dotenv
import uvicorn
from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from sms_api.dependencies import (
    get_simulation_database_service,
    init_standalone,
    shutdown_standalone,
)
from sms_api.log_config import setup_logging
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    ParcaDataset,
    ParcaDatasetRequest,
    SimulatorVersion,
)
from sms_api.version import __version__

logger = logging.getLogger(__name__)
setup_logging(logger)

# -- load dev env -- #
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
DEV_ENV_PATH = os.path.join(REPO_ROOT, "assets", "dev", "config", ".dev_env")
dotenv.load_dotenv(DEV_ENV_PATH)  # NOTE: create an env config at this filepath if dev

# -- constraints -- #
APP_VERSION = __version__
APP_TITLE = "sms-api"
APP_ORIGINS = [
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
    {"url": "https://sms.cam.uchc.edu", "description": "Production server"},
    {"url": "http://localhost:3001", "description": "Main Development server"},
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


@app.get("/")
def root() -> dict[str, str]:
    return {"docs": "https://biosim.biosimulations.org/docs", "version": APP_VERSION}


@app.get("/version")
def get_version() -> str:
    return APP_VERSION


@app.get(
    path="/simulator_version",
    response_model=SimulatorVersion,
    operation_id="simulate",
    tags=["Simulations"],
    summary="Run a parameter calculationsingle vEcoli simulation with given parameter overrides",
)
async def get_simulator_versions() -> list[SimulatorVersion]:
    db_service = get_simulation_database_service()
    if db_service is None:
        raise Exception("Simulation database service is not initialized")
    return await db_service.list_simulators()


@app.post(
    path="/vecoli_parca",
    response_model=ParcaDataset,
    operation_id="calculate_parameters",
    tags=["Simulations"],
    summary="Run a parameter calculation",
)
async def run_parca(parca_request: ParcaDatasetRequest) -> ParcaDataset:
    db_service = get_simulation_database_service()
    if db_service is None:
        raise Exception("Simulation database service is not initialized")
    parca_dataset: ParcaDataset = await db_service.get_or_insert_parca_dataset(parca_request)
    return parca_dataset


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
        raise Exception("Simulation database service is not initialized")
    inserted_sim: EcoliSimulation = await sim_db_service.insert_simulation(sim_request)

    # don't wait to submit the job to SLURM, just return the simulation object
    return inserted_sim


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104 binding to all interfaces
    logger.info("Server started")
