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

# APP_SERVERS: list[dict[str, str]] = [
#     {"url": ServerMode.PROD, "description": "Production server"},
#     {"url": ServerMode.DEV, "description": "Main Development server"},
#     {"url": ServerMode.PORT_FORWARD_DEV, "description": "Local port-forward"},
# ]
APP_SERVERS = None
APP_ROUTERS = ["core", "antibiotic"]
assets_dir = Path(get_settings().assets_dir)
ACTIVE_URL = ServerMode.detect(assets_dir / "dev" / "config" / ".dev_env")


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


# -- set ui templates and marimo notebook apps -- #

client_dir = Path(get_settings().app_dir) or Path("app")
ui_dir = client_dir / "ui"
templates_dir = client_dir / "templates"

server = marimo.create_asgi_app()
app_names: list[str] = []

for filename in sorted(os.listdir(ui_dir)):
    if filename.endswith(".py"):
        app_name = format_marimo_appname(os.path.splitext(filename)[0])
        app_path = os.path.join(ui_dir, filename)
        server = server.with_app(path=f"/{app_name}", root=app_path)
        app_names.append(app_name)

templates = Jinja2Templates(directory=templates_dir)


# -- app-level endpoints -- #


@app.get("/")
async def home(request: Request) -> templating._TemplateResponse:
    return templates.TemplateResponse(
        request, "home.html", {"request": request, "app_names": app_names, "marimo_path_prefix": "/ws"}
    )


@app.get("/health")
async def check_health() -> dict[str, str]:
    return {"docs": f"{ACTIVE_URL}{app.docs_url}", "version": APP_VERSION}


@app.get("/version")
async def get_version() -> str:
    return APP_VERSION


# -- mount marimo apps to FastAPI root -- #

app.mount("/ws", server.build())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="auto")  # noqa: S104 binding to all interfaces
    logger.info("API Gateway Server started")
