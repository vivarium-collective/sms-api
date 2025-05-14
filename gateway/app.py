"""Sets up FastAPI app singleton"""

import importlib
import os 
import logging as log

import dotenv as dot
import fastapi
from fastapi.openapi.utils import get_openapi
from starlette.middleware.cors import CORSMiddleware

from common import auth
from gateway.handlers.app_config import get_config
from gateway.core.router import config as community
from gateway.evolve.router import config as evolve 


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

LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
APP_URL = LOCAL_URL


# FastAPI app
app = fastapi.FastAPI(title=APP_CONFIG['title'], version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=APP_CONFIG['origins'],  # TODO: specify this for uchc
    allow_credentials=True,
    allow_methods=APP_CONFIG['methods'],
    allow_headers=APP_CONFIG['headers']
)


@app.get("/", tags=["Core"])
async def check_health():
    return {"GUI": LOCAL_URL + "/docs", "status": "RUNNING"}


@app.get("/api/v1/test/authentication", operation_id="test-authentication", tags=["Core"])
async def test_authentication(user: dict = fastapi.Depends(auth.get_user)):
    return user


# add routers: TODO: specify this to be served instead by the reverse-proxy
for api_name in APP_ROUTERS:
    api = importlib.import_module(f'gateway.{api_name}.router')
    app.include_router(
        api.config.router, 
        prefix=api.config.prefix, 
        dependencies=api.config.dependencies  # type: ignore
    )




