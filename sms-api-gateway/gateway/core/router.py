"""Endpoint definitions for the CoreAPI. NOTE: Users of this API must be first authenticated."""

import asyncio
import base64
from dataclasses import dataclass, asdict, field
import gzip
import json
import os
from typing import Callable, Generator
import uuid 

import dotenv as de
import nats
from nats.aio.client import Client as NATS
from nats.aio.subscription import Subscription
from nats.aio.msg import Msg
import redis
import websockets
import simdjson  # type: ignore
from fastapi import APIRouter, Query
import fastapi
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from asyncio import sleep

from common.managers.db import MongoManager
from data_model.api import BulkMoleculeData, ListenerData, WCMIntervalData, WCMIntervalResponse, WCMSimulationRequest
from data_model.base import BaseClass
from data_model.jobs import SimulationRunStatuses
from data_model.requests import SimulationRequest
from gateway.handlers.db import configure_mongo
from gateway.handlers.simulation import interval_generator
from data_model.gateway import RouterConfig
from common import auth, log, users
from gateway.core.client import client
from gateway.handlers.app_config import root_prefix
from data_model.jobs import SimulationRun


logger = log.get_logger(__file__)

de.load_dotenv()


class UrlPrefixes:
    local = "http://localhost"
    prod = "https://"  # TODO: complete this
    socket = "ws://localhost"
    mongo = "mongodb://localhost"


INTERACTION_MODE = os.getenv("MODE", "dev")

HTTP_PREFIX = UrlPrefixes.local if INTERACTION_MODE == "dev" else UrlPrefixes.prod 
PORT = 8080
URL_ROOT = f"{HTTP_PREFIX}:{PORT}"

SOCKET_PREFIX = UrlPrefixes.socket
RUN_SIMULATION_SOCKET = 8765
GET_RESULTS_SOCKET = 8766

def get_socket_url(socket_port: int):
    return f"{SOCKET_PREFIX}:{socket_port}"

RUN_SIMULATION_REDIS_PORT = 6379
GET_RESULTS_REDIS_PORT = 6380

MONGO_PREFIX = UrlPrefixes.mongo
MONGO_PORT = 27017
MONGO_URI = f"{MONGO_PREFIX}:{MONGO_PORT}"

MAJOR_VERSION = 1

config = RouterConfig(
    router=APIRouter(), 
    prefix=root_prefix(MAJOR_VERSION) + "/core",
    dependencies=[fastapi.Depends(users.fetch_user)]
)

db_manager = MongoManager(MONGO_URI)
mongo_client, mongo_db = configure_mongo()
simulation_broker = redis.Redis(host='localhost', port=RUN_SIMULATION_REDIS_PORT, decode_responses=True)
results_broker = redis.Redis(host='localhost', port=GET_RESULTS_REDIS_PORT, decode_responses=True)


async def get_broker(server=None) -> NATS:
    nc = await nats.connect()
    return nc


async def subscriber(nc: NATS, channel_id: str):
    sub = await nc.subscribe(channel_id)
    msg: Msg = await sub.next_msg()
    yield msg 


async def publish(nc: NATS, channel_id: str, data: dict) -> None:
    await nc.publish(channel_id, bytes(json.dumps(data).encode()))
    return 


class Message(dict):
    def __new__(cls, *args, **kwargs):
        return cls.__new__(cls, *args, **kwargs)


async def send_message(r: redis.Redis, dataname: str, data: dict):
    return r.hset(dataname, mapping=data)


async def recieve_message(r: redis.Redis, dataname: str) -> Message:
    return Message(**r.hgetall(dataname))
    

def compress_message(data: dict) -> str:
    import json 
    import gzip 
    import base64
    compressed = gzip.compress(json.dumps(data).encode())
    return base64.b64encode(compressed).decode()


def decompress_message(encoded_data: str) -> dict:
    import json 
    import gzip 
    import base64
    compressed = base64.b64decode(encoded_data)
    decompressed = gzip.decompress(compressed).decode()
    return json.loads(decompressed)


def new_experiment_id():
    return str(uuid.uuid4())


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
    collection = mongo_db.get_collection(collection_name)
    await collection.insert_one(simulation_run.model_dump())

    # emit new request to socket port
    await send_message(simulation_broker, simulation_id, simulation_run.model_dump())
    # async with websockets.connect("ws://localhost:8765") as websocket:
    #     await websocket.send(json.dumps(payload))
    #     logger.info(f'Sent request for: {simulation_request.experiment_id}')
   
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

    # option A: retrieve the data via a websocket 
    while n_iter < 10:
        await send_message(results_broker, simulation_id, {'simulation_id': simulation_id})
        response = await recieve_message(results_broker, simulation_id)
        logger.info(f'Sent get request message for {simulation_id}')
        job = decompress_message(response)
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


# NOTE: not yet used; to be implemented later
# @config.router.get("/stream-simulation", tags=["Core"], description="Submit a simulation run and return a streaming response.")
# async def stream_simulation(
#     request: fastapi.Request,
#     experiment_id: str = Query(default=new_experiment_id()),
#     total_time: float = Query(default=3.0),
#     time_step: float = Query(default=0.1),
#     start_time: float = Query(default=1.0),
#     framesize: float = Query(default=1.0)
# ):
#     compile_simulation = lambda: NotImplementedError("TODO: finish this!")
#     return StreamingResponse(
#         interval_generator(
#             request=request,
#             experiment_id=experiment_id,
#             total_time=total_time,
#             time_step=time_step,
#             start_time=start_time,
#             framesize=framesize,
#             compile_simulation=compile_simulation
#         ), 
#         media_type="text/event-stream"
#     )

