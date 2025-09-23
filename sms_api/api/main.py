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

import importlib
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

import marimo
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from starlette import templating
from starlette.middleware.cors import CORSMiddleware

from sms_api.common.gateway.models import ServerMode
from sms_api.common.gateway.utils import format_marimo_appname
from sms_api.config import get_settings
from sms_api.dependencies import (
    get_job_scheduler,
    init_standalone,
    shutdown_standalone,
)
from sms_api.version import __version__

logger = logging.getLogger(__name__)


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
APP_ROUTERS = [
    "ecoli",
    "antibiotics",
    "biofactory",
    # "configs",  # config upload/download/get only
    "inference",
    "variants",
    # "experiments",  # SLURM submitted, vEcoli/Nextflow-based workflows (main)
    # "wcm",  # first iteration of complete nextflow-based requests
    # "core",  # original EcoliSim modular router (TODO: revamp this: it can be nicely used!)
]
ENV = get_settings()
assets_dir = Path(ENV.assets_dir)
ACTIVE_URL = ServerMode.detect(assets_dir / "dev" / "config" / ".dev_env")
UI_NAMES = [
    "analyze",
    "antibiotic",
    "biofactory",
    "configure",
    "experiment",
    # "wcm",
    # "inference",
    # "single_cell",
]


# -- app configuration: lifespan and middleware -- #


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    # configure and start standalone services (data, sim, db, etc)
    dev_mode = os.getenv("DEV_MODE", "0")
    start_standalone = partial(init_standalone)
    if bool(int(dev_mode)):
        logger.warning("Development Mode is currently engaged!!!", stacklevel=1)
        start_standalone.keywords["enable_ssl"] = True
    await start_standalone()

    # --- JobScheduler setup ---
    job_scheduler = get_job_scheduler()
    if not job_scheduler:
        raise RuntimeError("JobScheduler is not initialized. Please check your configuration.")
    await job_scheduler.subscribe()
    await job_scheduler.start_polling(interval_seconds=5)  # configurable interval

    try:
        yield
    finally:
        await job_scheduler.close()
    await shutdown_standalone()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan, redoc_url="/documentation")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # TODO: change origins back to allowed
)
for api_name in APP_ROUTERS:
    try:
        api = importlib.import_module(f"sms_api.api.routers.{api_name}")
        app.include_router(
            api.config.router,
            prefix=api.config.prefix,
            dependencies=api.config.dependencies,
        )
    except ImportError:
        logger.exception(f"Could not register the following api: {api_name}")


# -- set ui templates and marimo notebook apps -- #

client_dir = Path(ENV.app_dir) or Path("app")
ui_dir = client_dir / "ui"
templates_dir = client_dir / "templates"
server = marimo.create_asgi_app()

app_filenames = [f"{modname}.py" for modname in UI_NAMES]
for filename in sorted(os.listdir(ui_dir)):
    if filename in app_filenames:
        if "analyze" in filename:
            app_name = "Analyze"
            desc = "Run Simulation Analyses"
        elif "experiment" in filename:
            app_name = "Experiment"
            desc = "Run a Simulation Experiment"
        else:
            app_name = format_marimo_appname(os.path.splitext(filename)[0])
            desc = "Click Me!"
        app_path = os.path.join(ui_dir, filename)
        server = server.with_app(path=f"/{app_name}", root=app_path)

templates = Jinja2Templates(directory=templates_dir)


# -- main-level endpoints -- #


@app.get("/", tags=["SMS API"])
async def home(request: Request) -> templating._TemplateResponse:
    app_info = [
        ("Analyze", "Run Simulation Analyses"),
        ("Antibiotic", "Explore new possibilities"),
        ("Biofactory", "Create new strains"),
        ("Configure", "Customize and configure experiments"),
        ("Experiment", "Run a Simulation Experiment"),
    ]
    return templates.TemplateResponse(
        request, "home.html", {"request": request, "app_names": app_info, "marimo_path_prefix": "/ws"}
    )


@app.get("/health", tags=["SMS API"])
async def check_health() -> dict[str, str]:
    return {"docs": f"{ACTIVE_URL}{app.docs_url}", "version": APP_VERSION}


@app.get("/version", tags=["SMS API"])
async def get_version() -> str:
    return APP_VERSION


# -- mount marimo apps to FastAPI root -- #

app.mount("/ws", server.build())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="auto")  # noqa: S104 binding to all interfaces
    logger.info("API Gateway Server started")
