"""Sets up FastAPI app singleton"""

from functools import partial
import os 
import logging as log

import dotenv as dot
import fastapi
from fastapi.openapi.utils import get_openapi
from starlette.middleware.cors import CORSMiddleware

from api.data_model.gateway import RouterConfig
from api.gateway.handlers import app_config as config 
from api.gateway import auth 
from api.gateway.routers import community, evolve


logger: log.Logger = log.getLogger(__name__)

dot.load_dotenv()

# config spec and env vars
APP_CONFIG = config.get_config(
    os.path.join(
        os.path.dirname(
            os.path.dirname(__file__)
        ),
        'shared',
        'configs',
        'app_config.json'
    )
)
APP_VERSION = APP_CONFIG['version']
GATEWAY_PORT = os.getenv("GATEWAY_PORT", "8080")

# endpoint routers
ROOT_PREFIX = f"/api/{APP_VERSION}"
ROUTER_CONFIGS = [
    RouterConfig(
        router=community.router, 
        prefix=ROOT_PREFIX + "/community",
        dependencies=[fastapi.Depends(auth.get_user)]
    ),
    RouterConfig(
        router=evolve.router, 
        prefix=ROOT_PREFIX + "/evolve",
        dependencies=[fastapi.Depends(auth.get_user)]
    ),
]

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
for router in ROUTER_CONFIGS:
    app.include_router(
        router.router, 
        prefix=router.prefix, 
        dependencies=router.dependencies  # type: ignore
    )  


@app.get("/", tags=["Root"])
async def api_root():
    return {"GUI": LOCAL_URL + "/docs"}


# e54d4431-5dab-474e-b71a-0db1fcb9e659
