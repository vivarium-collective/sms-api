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
import pickle
import shutil
import tempfile as tmp
import os
import time
import traceback
from typing import Callable, Iterable
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
from gateway.handlers.db import configure_mongo
from gateway.handlers.simulation import interval_generator
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

from data_model.jobs import SimulationRun
from data_model.vivarium import VivariumDocument


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
client, db = configure_mongo()


def compress_message(data: dict) -> str:
    compressed = gzip.compress(json.dumps(data).encode())
    return base64.b64encode(compressed).decode()


def decompress_message(encoded_data: str) -> dict:
    compressed = base64.b64decode(encoded_data)
    decompressed = gzip.decompress(compressed).decode()
    return json.loads(decompressed)


def new_experiment_id():
    return str(uuid.uuid4())


async def socket_connector(handler: Callable, url: str | None = None, socket_port: int = 8765, *args, **kwargs):
    async with websockets.connect(url or f"ws://localhost:{socket_port}") as websocket:
        return handler(*args, **kwargs)


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
        logger.info(f'Sent request for: {simulation_request.experiment_id}')
   
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
        url = get_socket_url(GET_RESULTS_SOCKET)
        async with websockets.connect(url) as websocket:
            await websocket.send(json.dumps({'simulation_id': simulation_id}))
            logger.info(f'Sent get request message for {simulation_id}')
            response = await websocket.recv(decode=True)
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

