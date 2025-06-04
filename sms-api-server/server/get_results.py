import asyncio
import base64
import gzip
import json
import os
import pickle
import shutil
import tempfile
import traceback
from typing import Any, Callable
import uuid
import warnings
import copy 

import dotenv as de
import numpy as np
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
import websockets
from websockets.asyncio.server import ServerConnection as WebSocket

from common import log
from common.managers.db import MongoManager
from data_model.api import BulkMoleculeData, ListenerData, WCMIntervalData, WCMIntervalResponse, WCMSimulationRequest
from server.dispatch import compile_simulation
from server.handlers.db import configure_mongo
from server.handlers.runs import RunsDb


logger = log.get_logger(__file__)
de.load_dotenv()

SIMULATION_REQUESTS_COLLECTION = "run_simulation"
SIMULATION_RESPONSE_COLLECTION = "get_results"
MONGO_URI = "mongodb://localhost:27017/"
SOCKET_PORT = 8765

runs = RunsDb()
client, db = configure_mongo()


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


def compress_message(data: dict) -> str:
    compressed = gzip.compress(json.dumps(data).encode())
    return base64.b64encode(compressed).decode()


def decompress_message(encoded_data: str) -> dict:
    compressed = base64.b64decode(encoded_data)
    decompressed = gzip.decompress(compressed).decode()
    return json.loads(decompressed)


async def socket_connector(handler: Callable, url: str | None = None, socket_port: int = 8765, *args, **kwargs):
    async with websockets.connect(url or f"ws://localhost:{socket_port}") as websocket:
        return handler(*args, **kwargs)


async def process_results_query(request, websocket: WebSocket):
    """Websocket processor for getting results"""
    collection = db.get_collection("get_results")
    run = await collection.find_one(request)
    if run:
        run.pop("_id", None)
        packet = compress_message(run)
        await websocket.send(packet)
        # print(f"Response emitted!!\n{json.dumps(run)}")
    else:
        await websocket.send(
            compress_message(
                {"error": {"message": f"Could not find that job.", "request": request}}))


async def processor(websocket: WebSocket):
    global runs
    global db 
    async for request_payload in websocket:
        request = json.loads(request_payload)
        request.pop("_id", None)
        print(f"Got a request payload: {request}")
        await process_results_query(request, websocket)
        await asyncio.sleep(2.22)


async def get_results_queue(port=8766):
    async with websockets.serve(processor, "localhost", port):
        print(f"WebSocket server running on ws://localhost:{port}")
        await asyncio.Future()
    

if __name__ == "__main__":
    asyncio.run(get_results_queue())


    
