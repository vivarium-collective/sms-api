"""Sets up FastAPI app singleton"""

import importlib
import os 
import logging as log
from typing import Annotated
import json 

import dotenv as dot
import fastapi
from fastapi import Cookie, Depends, FastAPI, Query, WebSocket, WebSocketDisconnect, WebSocketException, status, APIRouter
from fastapi.responses import HTMLResponse
from starlette.middleware.cors import CORSMiddleware
import anyio
from broadcaster import Broadcast
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates

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


async def homepage(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context)


async def chatroom_ws(websocket):
    await websocket.accept()

    async with anyio.create_task_group() as task_group:
        # run until first is complete
        async def run_chatroom_ws_receiver() -> None:
            await chatroom_ws_receiver(websocket=websocket)
            task_group.cancel_scope.cancel()

        task_group.start_soon(run_chatroom_ws_receiver)
        await chatroom_ws_sender(websocket)


async def chatroom_ws_receiver(websocket):
    async for message in websocket.iter_text():
        await broadcast.publish(channel="chatroom", message=message)
        print(f'Got user input:')


async def chatroom_ws_sender(websocket):
    async with broadcast.subscribe(channel="chatroom") as subscriber:
        async for event in subscriber:
            await websocket.send_text(event.message)


# FastAPI app
broadcast = Broadcast("redis://localhost:6379")
templates = Jinja2Templates("templates")
routes = [
    Route("/", homepage),
    WebSocketRoute("/", chatroom_ws, name='chatroom_ws'),
]

app = fastapi.FastAPI(routes=routes, title=APP_CONFIG['title'], version=APP_VERSION, on_startup=[broadcast.connect], on_shutdown=[broadcast.disconnect])
app.add_middleware(
    CORSMiddleware,
    # allow_origins=APP_CONFIG['origins'],  # TODO: specify this for uchc
    # allow_credentials=True,
    # allow_methods=APP_CONFIG['methods'],
    # allow_headers=APP_CONFIG['headers']
    allow_origins=["*"],  # change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

