"""Sets up FastAPI app singleton"""

from functools import partial
import os 
import logging as log

import dotenv as dot
import fastapi
from fastapi.openapi.utils import get_openapi
from starlette.middleware.cors import CORSMiddleware
import typer
import uvicorn

from api.gateway.handlers import app_config
from api.gateway.app import app as community 


logger: log.Logger = log.getLogger(__name__)

dot.load_dotenv()

# config spec and env vars
APP_CONFIG = app_config.get_config(
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
# url roots
LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this


cli = typer.Typer()

@cli.command()
def start(api_name: str, max_timeout: int = 50, buffer: float = 5.0, host="0.0.0.0", port=8080):
    app = community
    uvicorn.run(app, host=host, port=port)


# e54d4431-5dab-474e-b71a-0db1fcb9e659
