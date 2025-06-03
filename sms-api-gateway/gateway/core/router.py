"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""

import ast
import asyncio
import base64
from collections import defaultdict
import datetime
from dataclasses import dataclass, asdict, field
import enum
import gzip
import json
import shutil
import tempfile as tmp
import os
import time
import traceback
from typing import Iterable
import uuid 
import gridfs
import gridfs.asynchronous
import gridfs.synchronous
from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.database import AsyncDatabase
from tqdm.notebook import tqdm

import pydantic as pyd
from pydantic import BaseModel, ConfigDict, Field
from pymongo.results import InsertOneResult
import dotenv as de
import numpy as np
import websockets
from common.connectors.db import MongoConnector
from common.managers.db import MongoManager
from data_model.api import BulkMoleculeData, ListenerData, WCMIntervalData, WCMIntervalResponse, WCMSimulationRequest
from data_model.base import BaseClass
from data_model.jobs import SimulationRunStatuses
from data_model.requests import SimulationRequest
import process_bigraph  # type: ignore
import simdjson  # type: ignore
import anyio
from fastapi import APIRouter, Query, WebSocket
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
from data_model.jobs import SimulationRun
from data_model.vivarium import VivariumDocument


logger = log.get_logger(__file__)

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

MONGO_URI = "mongodb://localhost:27017/"
db_manager = MongoManager(MONGO_URI)


def compress_message(data: dict) -> str:
    compressed = gzip.compress(json.dumps(data).encode())
    return base64.b64encode(compressed).decode()


def new_experiment_id():
    return str(uuid.uuid4())


def get_save_times(start, end, framesize, t):
    frames = np.arange(start, end, framesize)
    hist = np.histogram(frames, bins=t, range=None, density=None, weights=None)
    h = list(zip(hist[1], hist[0]))
    save_times = []
    for i, v in h:
        if v > 0:
            save_times.append(i.tolist())
    return save_times


# TODO: report fluxes listeners for escher
async def interval_generator(
    request: fastapi.Request,
    experiment_id: str,
    total_time: float,
    time_step: float,
    start_time: float = 1.0,
    buffer: float = 0.11,
    framesize: float | None = None
):
    # yield a formalized request confirmation to client TODO: possibly emit something here
    request_payload = {}
    for k, v in request.query_params:
        val = v
        if v.isdigit():
            val = float(v)
        request_payload[k] = val
            
    req = WCMSimulationRequest(**request_payload)
    yield format_event(req.json()) 

    # set up simulation params
    tempdir = tmp.mkdtemp(dir="data")
    datadir = f'{tempdir}/{experiment_id}'
    t = np.arange(start_time, total_time, time_step)
    save_times = get_save_times(start_time, total_time, framesize, t) if framesize else None
    
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

            # configure report interval
            if save_times is not None:
                if t[i] in save_times:
                    report_idx = save_times.index(t[i])
                    sim.save_times = [save_times[report_idx]]
            else:
                sim.save_times = [t_i]

            # build/populate sim
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

            response_i = WCMIntervalResponse(**{
                "experiment_id": experiment_id,
                "duration": sim.total_time, 
                "interval_id": str(t_i), 
                "results": WCMIntervalData(
                    bulk=bulk_results_i, 
                    listeners=listener_results_i
                )
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


@config.router.get("/stream-simulation", tags=["Core"], description="Submit a simulation run and return a streaming response.")
async def stream_simulation(
    request: fastapi.Request,
    experiment_id: str = Query(default=new_experiment_id()),
    total_time: float = Query(default=3.0),
    time_step: float = Query(default=0.1),
    start_time: float = Query(default=1.0),
    framesize: float = Query(default=1.0)
):
    return StreamingResponse(
        interval_generator(
            request=request,
            experiment_id=experiment_id,
            total_time=total_time,
            time_step=time_step,
            start_time=start_time,
            framesize=framesize
        ), 
        media_type="text/event-stream"
    )


def configure_mongo():
    MONGO_URI = "mongodb://localhost:27017/"
    client = AsyncMongoClient(MONGO_URI)
    db: AsyncDatabase = client.get_database("simulations")
    return client, db 


async def subscribe_to_socket(socket_port: int = 8765):
    async with websockets.connect(f"ws://localhost:{socket_port}") as websocket:
        response = await websocket.recv()
        print(f"Received from server: {response}")
        return response
    

async def publish_request(request: SimulationRequest, socket_port: int = 8765): 
    async with websockets.connect(f"ws://localhost:{socket_port}") as websocket:
        msg = f"{request}"
        await websocket.send(msg)
        print('Emitted new request!')


client, db = configure_mongo()

# @config.router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket, request: SimulationRequest):
#     # connect to server
#     await websocket.accept()
#     # data = await websocket.receive_text()
#     await websocket.send_text(f"Message text was: {request}")
#     print('message sent!')


@config.router.post("/run-simulation", tags=["Core"])
async def run_simulation(simulation_request: SimulationRequest):
    # format request payload
    simulation_id = f"{simulation_request.experiment_id}-{str(uuid.uuid4())}"
    payload = {"simulation_id": simulation_id, **simulation_request.model_dump()}
    simulation_run = SimulationRun(
        simulation_id=simulation_id, 
        status=SimulationRunStatuses.submitted,
        request=simulation_request
    )

    # write request to db
    collection_name = "run_simulation"
    collection = db.get_collection(collection_name)
    await collection.insert_one(simulation_run.model_dump())

    # emit new request to socket port
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send(json.dumps(payload))
        logger.info(f'Sent message for {simulation_request.experiment_id}')
   
    # return formalized request
    return SimulationRun(
        simulation_id=simulation_id, 
        status=SimulationRunStatuses.submitted,
        request=simulation_request
    )


# TODO: have the ecoli interval results call encryption.db.write for each interval
# TODO: have this method call encryption.db.read for interval data
@config.router.get(
    '/get/results', 
    operation_id='get-results', 
    tags=["Core"]
)
async def get_results(simulation_id: str = Query(...)):
    n_iter = 0
    job = None
    while n_iter < 10:
        async with websockets.connect("ws://localhost:8765") as websocket:
            await websocket.send(json.dumps({'simulation_id': simulation_id}))
            logger.info(f'Sent get request message for {simulation_id}')
            response = await websocket.recv()
            job = json.loads(response)
            logger.info(f'Got a response: {job}')

            if job is None:
                await asyncio.sleep(2.0)
                n_iter += 1
                continue
            else:
                break
    if job:
        return SimulationRun(simulation_id=job["simulation_id"], status=job["status"], results=job.get("results")) 
    else:
        raise fastapi.HTTPException(status_code=404, detail=f"{simulation_id} not found")


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


def test_get_save_times():
    start = 0.1111
    end = 11.11
    fs = 0.1
    step = 0.000001
    t = np.arange(start, end, step)
    return get_save_times(start, end, fs, t)


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