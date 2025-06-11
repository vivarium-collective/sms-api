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
import redis
import websockets
from websockets.asyncio.server import ServerConnection as WebSocket

from common import log
from common.managers.db import MongoManager
from data_model.api import BulkMoleculeData, ListenerData, WCMIntervalData, WCMIntervalResponse, WCMSimulationRequest
from controller.dispatch import compile_simulation
from controller.handlers.db import configure_mongo
from controller.handlers.runs import RunsDb


logger = log.get_logger(__file__)
de.load_dotenv()

SIMULATION_REQUESTS_COLLECTION = "run_simulation"
SIMULATION_RESPONSE_COLLECTION = "get_results"
MONGO_URI = "mongodb://localhost:27017/"
SOCKET_PORT = 8765
REDIS_PORT = 6379

runs = RunsDb()
broker = redis.Redis(host='localhost', port=REDIS_PORT, decode_responses=True)
mongo_client, mongo_db = configure_mongo()


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


async def process_simulation(
    experiment_id: str | None = None,
    total_time: float | None = None,
    time_step: float | None = None,
    start_time: float = 1.0,
    buffer: float = 0.11,
    framesize: float | None = None,
    **request_payload
):
    # yield a formalized request confirmation to client TODO: possibly emit something here
    req = WCMSimulationRequest(**request_payload)

    # set up simulation params
    tempdir = tempfile.mkdtemp(dir="data")
    datadir = f'{tempdir}/{experiment_id}'
    t = np.arange(req.start_time, 3.0, req.time_step)
    framesize = req.time_step
    save_times = get_save_times(req.start_time, req.total_time, framesize, t) if framesize else None
    
    sim = compile_simulation(experiment_id=experiment_id, datadir=datadir, build=False)
    sim.time_step = time_step
    sim.initial_global_time = 0.0
    sim.emitter = "timeseries"
    sim.save = True
    sim.progress_bar = False
    sim.build_ecoli()

    results = {}

    # iterate over t to get interval_t data
    for i, t_i in enumerate(t):
        try:
            sim.total_time = t_i

            # configure report interval
            # if save_times is not None:
            #     if t[i] in save_times:
            #         report_idx = save_times.index(t[i])
            #         sim.save_times = [save_times[report_idx]]
            # else:
            #     sim.save_times = [t_i]
            sim.save_times = [t_i.tolist()]

            # build/populate sim
            sim.build_ecoli()
            print(f'Running with sim params:\ntotal time: {sim.total_time}\nsave times: {sim.save_times}\ntimestep: {sim.time_step}')
            # runs for just t_i
            sim.run()

            # read out interval (TODO: this wont be needed w/composite)
            filepath = os.path.join(datadir, f"vivecoli_t{t_i}.json")
            with open(filepath, 'r') as f:
                result_i = json.load(f)["agents"]["0"]

            # TODO: gradually extract more data
            # extract bulk
            bulk_results_i: list[dict[str, str | int | float]] = []
            for mol in result_i["bulk"]:
                mol_id, mol_count = list(map(
                    lambda _: mol.pop(0),
                    list(range(2))
                ))
                bulk_mol = {"id": mol_id, "count": mol_count, "submasses": mol}  # BulkMoleculeData(id=mol_id, count=mol_count, submasses=mol)
                bulk_results_i.append(bulk_mol)
            
            # extract listener data
            listener_data = result_i["listeners"]
            extracted_listeners = ["fba_results", "atp", "equilibrium_listener"]
            listener_results_i = dict(zip(
                extracted_listeners,
                list(map(
                    lambda name: listener_data[name],
                    extracted_listeners
                ))
            ))

            interval_id = str(t_i)
            response_i = {
                "experiment_id": experiment_id, 
                "interval_id": interval_id, 
                "data": {
                    "bulk": bulk_results_i,
                    "listeners": listener_results_i
                }
            }
            results[interval_id] = response_i
            await asyncio.sleep(buffer)
        except:
            print(f'ERROR --->\nInterval ID: {t_i}')
            traceback.print_exc()

    print(f'Removing dir: {tempdir}')
    shutil.rmtree(tempdir)

    return {"simulation_id": req.simulation_id, "results": results}


async def write_run(response, runs, db):
    """Mongo Processor for adding runs"""
    collection = db.get_collection("get_results")
    await collection.insert_one(response)
    await runs.add_run(response)


async def processor(websocket: WebSocket):
    global runs
    global db 
    async for request_payload in websocket:
        request = json.loads(request_payload)
        request.pop("_id", None)
        print(f"Got a request payload: {request}")
        response = await process_simulation(**request)
        await write_run(response, runs, mongo_db)
        await asyncio.sleep(2.22)


async def queue(port=8765):
    async with websockets.serve(processor, "localhost", port):
        print(f"WebSocket server running on ws://localhost:{port}")
        await asyncio.Future()
    

if __name__ == "__main__":
    asyncio.run(queue())


    
