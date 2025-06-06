"""Sets up FastAPI app singleton"""

import importlib
import logging
import os

import dotenv as dot
import fastapi

# from gateway.core.router import routes, broadcast
from common import auth, log, users
from gateway.handlers.app_config import get_config
from starlette.middleware.cors import CORSMiddleware

# TODO: add the rest of these routers to app.json:
# "antibiotics",
# "biomanufacturing",
# "inference",
# "sensitivity_analysis",
# "evolve"

logger: logging.Logger = log.get_logger(__file__)
dot.load_dotenv()

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
APP_CONFIG = get_config(os.path.join(ROOT, "common", "configs", "app.json"))
APP_VERSION = APP_CONFIG["version"]
APP_ROUTERS = APP_CONFIG["routers"]
GATEWAY_PORT = os.getenv("GATEWAY_PORT", "8080")
LOCAL_URL = f"http://localhost:{GATEWAY_PORT}"
PROD_URL = ""  # TODO: define this
APP_URL = LOCAL_URL
APP_TITLE = APP_CONFIG["title"]

app = fastapi.FastAPI(title=APP_TITLE, version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=APP_CONFIG["origins"],  # TODO: specify this for uchc and change to specific origins in production
    allow_credentials=True,
    allow_methods=APP_CONFIG["methods"],
    allow_headers=APP_CONFIG["headers"],
)


# -- root-level methods(auth, health, etc) -- #


@app.get("/", tags=["Core"])
async def check_health():
    return {"GUI": LOCAL_URL + "/docs", "status": "RUNNING"}


# @app.post("/t")
# async def t(request: fastapi.Request, b: dict = fastapi.Body(), x: int = fastapi.Query(default=22)):
#     return [request.query_params, await request.form(), await request.body()]


@app.post("/login")
def login(
    response: fastapi.Response,
    username: str = fastapi.Form(default="test-user"),
    password: str = fastapi.Form(default="test"),
):
    try:
        user = auth.validate_user(username, password)
        response.set_cookie(key="session_user", value=user.name, httponly=True)
        return {"message": f"Welcome, {user.name}"}
    except fastapi.HTTPException as e:
        logger.error(f"AUTHENTICATION >> Could not authenticate user: {username}.\nDetails:\n{e}")
        # return fastapi.responses.JSONResponse(status_code=401, content={"detail": "Invalid credentials"})
        raise e


@app.post("/logout")
def logout(response: fastapi.Response):
    response.delete_cookie(key="session_user")
    return {"message": "Logged out"}


@app.get("/api/v1/test-authentication", operation_id="test-authentication", tags=["Core"])
async def test_authentication(user: dict = fastapi.Depends(users.fetch_user)):
    return user


# -- router-specific (actual API(s)) endpoints -- #

for api_name in APP_ROUTERS:
    api = importlib.import_module(f"gateway.{api_name}.router")
    app.include_router(
        api.config.router,
        prefix=api.config.prefix,
        dependencies=api.config.dependencies,  # type: ignore
    )
