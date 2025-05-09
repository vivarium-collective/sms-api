"""Sets up FastAPI app singleton"""

from functools import partial
import os 
import logging as log

import dotenv as dot
import fastapi
from fastapi.openapi.utils import get_openapi
from starlette.middleware.cors import CORSMiddleware

from api.gateway.handlers import app_config
from api.gateway.community.router import config


logger: log.Logger = log.getLogger(__name__)

dot.load_dotenv()

# config spec and env vars
APP_CONFIG = app_config.get_config(
    "/Users/alexanderpatrie/Desktop/repos/v2Ecoli/api/shared/configs/app_config.json"
)
APP_VERSION = APP_CONFIG['version']
GATEWAY_PORT = os.getenv("GATEWAY_PORT", "8080")

# endpoint routers

# url roots
LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this


# FastAPI app
app = fastapi.FastAPI(title=APP_CONFIG['title'], version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=APP_CONFIG['origins'],  # TODO: specify this for uchc
    allow_credentials=True,
    allow_methods=APP_CONFIG['methods'],
    allow_headers=["*"]
)

# add routers: TODO: specify this to be served instead by the reverse-proxy
# config.include(app)
app.include_router(
    config.router, 
    prefix=config.prefix, 
    dependencies=config.dependencies  # type: ignore
)


@app.get("/", tags=["Root"])
async def api_root():
    return {"GUI": LOCAL_URL + "/docs"}



# e54d4431-5dab-474e-b71a-0db1fcb9e659
