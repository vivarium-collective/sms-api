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

# TODO: mount nfs driver for local dev
# TODO: add more routers, ie; antibiotics, etc

"""

import importlib
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from sms_api.common.gateway.models import ServerMode
from sms_api.dependencies import (
    init_standalone,
    shutdown_standalone,
)
from sms_api.log_config import setup_logging
from sms_api.simulation.hpc_utils import read_latest_commit
from sms_api.version import __version__

logger = logging.getLogger(__name__)
setup_logging(logger)


def get_server_url(dev: bool = True) -> ServerMode:
    return ServerMode.DEV if dev else ServerMode.PROD


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
    "http://localhost:8000",
    "http://localhost:3001",
    "https://sms.cam.uchc.edu",
]

APP_SERVERS: list[dict[str, str]] = [
    {"url": ServerMode.PROD, "description": "Production server"},
    {"url": ServerMode.DEV, "description": "Main Development server"},
    {"url": "http://localhost:8888", "description": "Local port-forward"},
]
APP_ROUTERS = ["core", "antibiotic"]
ACTIVE_URL = ServerMode.detect(Path("assets/dev/config/.dev_env"))


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    # configure and start standalone services (data, sim, db, etc)
    dev_mode = os.getenv("DEV_MODE", "0")
    start_standalone = partial(init_standalone)
    if bool(int(dev_mode)):
        logger.warning("Development Mode is currently engaged!!!", stacklevel=1)
        start_standalone.keywords["enable_ssl"] = True
    await start_standalone()
    yield
    await shutdown_standalone()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, servers=APP_SERVERS, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=APP_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
for api_name in APP_ROUTERS:
    try:
        api = importlib.import_module(f"sms_api.api.routers.{api_name}")
        app.include_router(
            api.config.router,
            prefix=api.config.prefix,
            dependencies=api.config.dependencies,
        )
    except Exception:
        logger.exception(f"Could not register the following api: {api_name}")


# -- app-level endpoints -- #


@app.get("/")
async def root() -> dict[str, str]:
    return {"docs": f"{ACTIVE_URL}{app.docs_url}", "version": APP_VERSION}


@app.get("/version")
async def get_version() -> str:
    return APP_VERSION


@app.get("/endpoints")
async def get_paths(bg_tasks: BackgroundTasks):
    try:
        bg_tasks.add_task(logger.info, await root())
        return {"endpoints": [f"{ACTIVE_URL}{route.path}" for route in app.routes if "doc" not in route.path]}
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=404)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="auto")  # noqa: S104 binding to all interfaces
    logger.info("API Gateway Server started")
