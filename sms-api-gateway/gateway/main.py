"""Sets up FastAPI app singleton"""

import asyncio
import importlib
import os 
import logging as log
from typing import Annotated
import json 

import dotenv as dot
import fastapi
from fastapi.responses import HTMLResponse
from starlette.middleware.cors import CORSMiddleware

# from gateway.core.router import routes, broadcast
from common import auth
from gateway.handlers.app_config import get_config


# TODO: add the rest of these routers to app.json:
# "antibiotics",
# "biomanufacturing",
# "inference",
# "sensitivity_analysis",
# "evolve"

logger: log.Logger = log.getLogger(__name__)
dot.load_dotenv()

ROOT = os.path.abspath(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)
APP_CONFIG = get_config(
    os.path.join(ROOT, "common", "configs", "app.json")
)
APP_VERSION = APP_CONFIG['version']
APP_ROUTERS = APP_CONFIG['routers']
GATEWAY_PORT = os.getenv("GATEWAY_PORT", "8080")
LOCAL_URL = f"http://localhost:{GATEWAY_PORT}"
PROD_URL = ""  # TODO: define this
APP_URL = LOCAL_URL


# FastAPI app
app = fastapi.FastAPI(
    title=APP_CONFIG['title'], 
    version=APP_VERSION, 
    dependencies=[fastapi.Depends(auth.get_user)]
)
app.add_middleware(
    CORSMiddleware,
    # allow_origins=APP_CONFIG['origins'],  # 
    # allow_credentials=True,
    # allow_methods=APP_CONFIG['methods'],
    # allow_headers=APP_CONFIG['headers']
    allow_origins=["*"],  # TODO: specify this for uchc and change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/", tags=["Core"])
async def check_health(request: fastapi.Request):
    return {"GUI": LOCAL_URL + "/docs", "status": "RUNNING"}
        

# @app.get("/api/v1/test/authentication", operation_id="test-authentication", tags=["Core"])
# async def test_authentication(user: dict = fastapi.Depends(auth.get_user)):
#     return user


# add routers: TODO: specify this to be served instead by the reverse-proxy
for api_name in APP_ROUTERS:
    api = importlib.import_module(f'gateway.{api_name}.router')
    app.include_router(
        api.config.router, 
        prefix=api.config.prefix, 
        dependencies=api.config.dependencies  # type: ignore
    )

