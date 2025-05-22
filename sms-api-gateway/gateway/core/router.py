"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""

import ast
import asyncio
import base64
import datetime
from dataclasses import dataclass, asdict
import gzip
import json
import shutil
import tempfile as tmp
import os
import time
import traceback 

import dotenv as de
import numpy as np
import process_bigraph  # type: ignore
import simdjson  # type: ignore
import anyio
from fastapi import APIRouter, Query
import fastapi
from broadcaster import Broadcast, Event
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates

from data_model.gateway import RouterConfig
from common import auth
from gateway.handlers.app_config import root_prefix
# from gateway.handlers.vivarium import VivariumFactory, new_id
from gateway.dispatch import dispatch_simulation
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
    # dependencies=[fastapi.Depends(auth.get_user)]
)
broadcast = Broadcast(f"memory://localhost:{BROADCAST_PORT}")
templates = Jinja2Templates("resources/client_templates")


async def validate_socket(websocket: fastapi.WebSocket):
    """Evaluate the validity of the given websocket request's header and API key therein."""
    try:
        await auth.validate_socket(websocket)  # Validate API key manually
    except fastapi.HTTPException as e:
        traceback.print_exc()
        await websocket.close(code=fastapi.status.WS_1008_POLICY_VIOLATION)
        return 
    await websocket.accept()


@config.router.websocket("/run-simulation")
async def run_simulation(
    websocket: fastapi.WebSocket, 
    experiment_id: str, 
    duration: int,
    time_step: float = 1.0,
    framesize: float | None = None,
    overwrite: bool = False
):
    await validate_socket(websocket)
    print(f'Running with duration: {duration}')
    time.sleep(5)
    # tempdir = tmp.mkdtemp()
    tempdir = "mount"
    datadir = f'{tempdir}/{experiment_id}'
    if os.path.exists(datadir) and overwrite:
        shutil.rmtree(datadir)
    if not os.path.exists(datadir) or overwrite:
        os.makedirs(datadir)
    
    async def run_dispatch():
        # Run blocking sim in a thread to avoid blocking the event loop
        print(f'Run dispatch')
        await asyncio.to_thread(
            dispatch_simulation, 
            experiment_id=experiment_id, 
            datadir=datadir, 
            duration=duration,
            time_step=time_step,
            framesize=framesize
        )

    # async def collect_results():
    #     sent = set()
    #     t = np.arange(1, duration, framesize or time_step)
    #     while True:
    #         for i_t in t:
    #             filepath = os.path.join(datadir, f"vivecoli_t{i_t}.json")
    #             print(f'Found filepath: {filepath}')
    #             if i_t not in sent and os.path.exists(filepath):
    #                 with open(filepath) as f:
    #                     data = json.load(f)
    #                 message = {
    #                     experiment_id: data
    #                 }
    #                 await queue.put(message)
    #                 sent.add(i_t)
    #         if len(sent) == duration:
    #             break
    #         await asyncio.sleep(0.2)
        
    async def collect_results():
        sent = set()
        t = np.arange(1, duration, framesize or time_step)
        try:
            for i_t in t:
                filepath = os.path.join(datadir, f"vivecoli_t{i_t}.json")
                print(f'Found filepath: {filepath}')
                if os.path.exists(filepath):
                    print(f'Collect results {i_t}')
                    with open(filepath) as f:
                        data = json.load(f)
                    message = {
                        experiment_id: {
                            "interval_id": str(i_t),
                            "results": data
                        }
                    }
                    # print(f'Made message: {message}')

                    await websocket.send_json(message)
                    await asyncio.sleep(1)
        except fastapi.WebSocketDisconnect:
            print("WS Disconnected")
            traceback.print_exc()

    # async def send_messages():
    #     while True:
    #         message = await queue.get()
    #         await websocket.send_json(message)
    #         queue.task_done()
    # await asyncio.gather(
    #     run_dispatch(),
    #     collect_results(),
    #     send_messages()
    # )
    try:
        dispatch_task = asyncio.create_task(run_dispatch())
        collection_task = asyncio.create_task(collect_results())
        await asyncio.gather(dispatch_task, collection_task)
    finally:
        # shutil.rmtree(tempdir)
        print('Done')


def compress_message(data: dict) -> str:
    compressed = gzip.compress(json.dumps(data).encode())
    return base64.b64encode(compressed).decode()


@config.router.websocket("/_run-simulation")
async def _run_simulation(
    websocket: fastapi.WebSocket, 
    experiment_id: str = Query(...),
    duration: float = Query(default=11.0),
    time_step: float = Query(default=0.1),
    name: str = Query(default="single")
):
    # first validate connection
    await validate_socket(websocket)

    # tempdir to be iteratively written to
    tempdir = tmp.mkdtemp()
    datadir = f'{tempdir}/{experiment_id}'

    try:
        for i in range(int(duration)):
            # dispatch_sim(datadir)
            result = i**i
            message = {
                experiment_id: {
                    "interval_id": i,
                    "result": result
                }
            }
            # await websocket.send_json(message)
            await websocket.send_text(compress_message(message))
            await asyncio.sleep(1)  # simulate interval delay
    # return SimulationRun(
    #     id=sim_id,  # ensure users can use this to retrieve the data later
    #     last_updated=str(datetime.datetime.now())
    # )
    except fastapi.WebSocketDisconnect:
        print("WebSocket disconnected")
    shutil.rmtree(tempdir)



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