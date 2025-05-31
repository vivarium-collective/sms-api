"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""

import ast
import asyncio
import base64
import datetime
from dataclasses import dataclass, asdict, field
import gzip
import json
import shutil
import tempfile as tmp
import os
import time
import traceback
import uuid 
from tqdm.notebook import tqdm

import pydantic as pyd
from pydantic import BaseModel, ConfigDict
import dotenv as de
import numpy as np
from data_model.base import BaseClass
import process_bigraph  # type: ignore
import simdjson  # type: ignore
import anyio
from fastapi import APIRouter, Query
import fastapi
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json, uvicorn
from asyncio import sleep

from data_model.gateway import RouterConfig
from common import auth, log, users
from gateway.core.client import client
from gateway.handlers.app_config import root_prefix
# from gateway.handlers.vivarium import VivariumFactory, new_id
from gateway.dispatch import dispatch_simulation, compile_simulation
from data_model.simulation import SimulationRun
from data_model.vivarium import VivariumDocument


de.load_dotenv()

LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
MAJOR_VERSION = 1
SOCKET_URL = "ws://0.0.0.0:8080/run/single"
BROADCAST_PORT = "8080"

config = RouterConfig(
    router=APIRouter(), 
    prefix=root_prefix(MAJOR_VERSION) + "/core",
    dependencies=[fastapi.Depends(users.fetch_user)]
)
# broadcast = Broadcast(f"memory://localhost:{BROADCAST_PORT}")
# templates = Jinja2Templates("resources/client_templates")


# @config.router.get("/client", tags=["Core"])
# async def render_client():
#     return HTMLResponse(client)


def compress_message(data: dict) -> str:
    compressed = gzip.compress(json.dumps(data).encode())
    return base64.b64encode(compressed).decode()


def new_experiment_id():
    return str(uuid.uuid4())


class Base(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)


@dataclass
class ISimulationRequest(BaseClass):
    experiment_id: str | None = None
    last_update: str | None = None 
    cookie: str = "session_user"

    def __post_init__(self):
        if self.last_update is None:
            self.refresh_timestamp()

    def refresh_timestamp(self):
        self.last_update = self.timestamp()


# -- requests -- # 
@dataclass
class WCMSimulationRequest(ISimulationRequest):
    total_time: float = 10.0 
    time_step: float = 1.0 
    start_time: float = 0.1111


# -- responses -- # 
@dataclass 
class BulkMoleculeData(BaseClass):
    id: str 
    count: int 
    submasses: list[str]


@dataclass
class ListenerData(BaseClass):
    fba_results: dict = field(default_factory=dict)
    atp: dict = field(default_factory=dict)
    equilibrium_listener: dict = field(default_factory=dict)


@dataclass
class WCMIntervalData(BaseClass):
    bulk: list[BulkMoleculeData]
    listeners: ListenerData
    # TODO: add more!


@dataclass
class WCMIntervalResponse(BaseClass):
    experiment_id: str 
    interval_id: str
    results: WCMIntervalData


# TODO: report fluxes listeners for escher
async def interval_generator(
    request: fastapi.Request,
    experiment_id: str,
    total_time: float,
    time_step: float,
    start_time: float = 1.0,
    buffer: float = 0.11
):
    # yield a formalized request confirmation to client TODO: possibly emit something here
    pld = {}
    for k, v in request.query_params:
        val = v
        if v.isdigit():
            val = float(v)
        pld[k] = val
            
    req = WCMSimulationRequest(**pld)
    yield f"event: intervalUpdate\ndata: {req.json()}\n\n" 

    # set up simulation params
    tempdir = tmp.mkdtemp(dir="data")
    datadir = f'{tempdir}/{experiment_id}'
    t = np.arange(start_time, total_time, time_step)
    sim = compile_simulation(experiment_id=experiment_id, datadir=datadir, build=False)
    sim.time_step = time_step

    # iterate over t to get interval_t data
    for i, t_i in enumerate(t):
        if await request.is_disconnected():
            print(f'Client disconnected. Stopping simulation at {t_i}')
            break 
        try:
            sim.total_time = t_i
            initial_time = t[i - 1] if not i == 0 else 0.0
            sim.initial_global_time = initial_time
            sim.save_times = [t_i]
            sim.build_ecoli()

            # runs for just t_i
            sim.run()

            # read out interval (TODO: this wont be needed w/composite)
            filepath = os.path.join(datadir, f"vivecoli_t{t_i}.json")
            with open(filepath, 'r') as f:
                result_i = json.load(f)["agents"]["0"]

            # TODO: gradually extract more data
            # extract bulk
            bulk_results_i = []
            for mol in result_i["bulk"]:
                mol_id, mol_count = list(map(
                    lambda _: mol.pop(0),
                    list(range(2))
                ))
                bulk_mol = BulkMoleculeData(id=mol_id, count=mol_count, submasses=mol)
                bulk_results_i.append(bulk_mol)
            
            # extract listener data
            listener_data = result_i["listeners"]
            extracted_listeners = ["fba_results", "atp", "equilibrium_listener"]
            listener_results_i = ListenerData(
                **dict(zip(
                    extracted_listeners,
                    list(map(
                        lambda name: listener_data[name],
                        extracted_listeners
                    ))
                ))
            )


            # TODO: make datamodel for interval response
            results_i = WCMIntervalData(bulk=bulk_results_i, listeners=listener_results_i)
            response_i = WCMIntervalResponse(**{
                "experiment_id": experiment_id,
                "duration": sim.total_time, 
                "interval_id": str(t_i), 
                "results": results_i
            })
            payload_i: str = response_i.json()
            yield format_event(payload_i)
            await sleep(buffer)
        except:
            print(f'ERROR --->\nInterval ID: {t_i}')
            traceback.print_exc()

    print(f'Removing dir: {tempdir}')
    shutil.rmtree(tempdir)


def format_event(payload_i: str):
    return f"event: intervalUpdate\ndata: {payload_i}\n\n"


@config.router.get("/run-simulation", tags=["Core"])
async def run_simulation(
    request: fastapi.Request,
    experiment_id: str = Query(default=new_experiment_id()),
    total_time: float = Query(default=3.0),
    time_step: float = Query(default=0.1),
    start_time: float = Query(default=1.0)
):
    return StreamingResponse(
        interval_generator(
            request=request,
            experiment_id=experiment_id,
            total_time=total_time,
            time_step=time_step,
            start_time=start_time
        ), 
        media_type="text/event-stream"
    )


# TODO: have the ecoli interval results call encryption.db.write for each interval
# TODO: have this method call encryption.db.read for interval data
@config.router.get(
    '/get/results', 
    operation_id='get-results', 
    tags=["Core"]
)
async def get_results(simulation_id: str):
    # for now, data does not need to be encrypted as this api will only be 
    #  available if properly authenticated with an API Key.
    # viv = read(EncodedKey(key), vivarium_id)
    pass


# -- static data -- #

@config.router.get('/get/processes', tags=["Core"])
async def get_registered_processes() -> list[str]:
    # TODO: implement this for ecoli_core
    from genEcoli import ecoli_core
    return list(ecoli_core.process_registry.registry.keys())


@config.router.get('/get/types', tags=["Core"])
async def get_registered_types() -> list[str]:
    # TODO: implement this for ecoli_core
    from genEcoli import ecoli_core
    return list(ecoli_core.types().keys())


@config.router.get('/get/document', tags=["Core"])
async def get_core_document():
    fp = '/Users/alexanderpatrie/Desktop/repos/ecoli/genEcoli/model/state.json'
    with open(fp, 'r') as f:
        doc = simdjson.load(f)
    return doc


# -- secure ws chat-like -- #

# async def homepage(request):
#     template = "index.html"
#     context = {"request": request}
#     return templates.TemplateResponse(template, context)
# 
# data = {
#         "experiment": "trial_1",
#         "parameters": {
#             "temperature": 37.5,
#             "reagents": ["A", "B", "C"]
#         },
#         "results": {
#             "success": True,
#             "metrics": {"accuracy": 0.95, "time": 123}
#         }
#     }
# 
# 
# @dataclass
# class SocketEvent:
#     action: str 
#     user: str 
#     message: str 
# 
# 
# async def receive_request(websocket):
#     """Gets request payload/params from client"""
#     # TODO: here we can, in parallel, return msg to client and then run the simulation
#     async for message in websocket.iter_text():
#         payload = json.loads(message)
#         payload['message'] = json.dumps(data)
#         msg = json.dumps(payload)
#         await broadcast.publish(channel="chatroom", message=message)
# 
# 
# async def emit_response(websocket):
#     """Emits data"""
#     async with broadcast.subscribe(channel="chatroom") as subscriber:
#         async for event in subscriber:
#             msg: str = event.message
#             request = json.loads(
#                 json.loads(msg)['message']
#             )
#             print(f'Incoming event: {request}')
#             # TODO: here, process simulation request dict, then serialize it
#             response: str = msg
#             print(f'Outgoing event: {response}, {type(response)}')
#             assert isinstance(response, str)
#             await websocket.send_text(response)
#             print(f'Send data: SEND TEXT COMPLETE')
#             
# 
# async def simulation_ws(websocket):
#     await websocket.accept()
# 
#     async with anyio.create_task_group() as task_group:
#         # FUNC A: run until first is complete
#         async def run_simulation_ws_receiver() -> None:
#             await receive_request(websocket=websocket)
#             task_group.cancel_scope.cancel()
# 
#         task_group.start_soon(run_simulation_ws_receiver)
#         await emit_response(websocket)
# routes = [
#     Route("/run/single", homepage),
#     WebSocketRoute(path="/run/single", endpoint=simulation_ws, name='simulation_ws'),
# ]