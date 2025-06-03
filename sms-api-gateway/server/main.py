import asyncio
import json
import os
import shutil
import tempfile
import traceback
from typing import Any
import uuid
import warnings
import copy 
import numpy as np
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
import websockets
from websockets.asyncio.server import ServerConnection as WebSocket
from common.managers.db import MongoManager
from data_model.api import BulkMoleculeData, ListenerData, WCMIntervalData, WCMIntervalResponse, WCMSimulationRequest
from server.dispatch import compile_simulation


SIMULATION_REQUESTS_COLLECTION = "run_simulation"
SIMULATION_RESPONSE_COLLECTION = "get_results"
MONGO_URI = "mongodb://localhost:27017/"
SOCKET_PORT = 8765


class RunsDb(object):
    _existing_runs: set[str] = set()
    _existing_results: list = []

    @property
    def existing_results(self):
        return self._existing_results
    
    @existing_results.setter 
    def existing_results(self, new):
        is_same = self._compare_results(new)
        print(f'Is same data: {is_same}')
        self._existing_results = new 
    
    def _compare_results(self, new: dict[str, str]):
        # this method serves to maintain as much concurrency as possible by comparing the
        # currently set runs to the ones being set (for safety)
        return self._existing_results == new
    
    async def add_run(self, response: dict):
        response.pop("_id", None)
        self._existing_results.append(json.dumps(response))
        print(f'Added response: {response}')
    
    async def get_run(self, simulation_id: str):
        matcher = filter(
            lambda v: simulation_id in v,
            self.existing_results
        )
        try:
            serialized_run = next(matcher)
            run = await self.hydrate_run(serialized_run)
            return run 
        except StopIteration:
            warnings.warn(f"No run exists for simulation id: {simulation_id}")
            return None
    
    async def hydrate_run(self, run: str):
        return json.loads(run)


def configure_mongo():
    MONGO_URI = "mongodb://localhost:27017/"
    client = AsyncMongoClient(MONGO_URI)
    db: AsyncDatabase = client.get_database("simulations")
    return client, db 


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
    sim.build_ecoli()

    results = {}

    # iterate over t to get interval_t data
    for i, t_i in enumerate(t):
        try:
            sim.total_time = t_i
            # initial_time = t[i - 1] if not i == 0 else 0.0
            # sim.initial_global_time = initial_time

            # configure report interval
            sim.emitter = "timeseries"
            sim.save = True
            sim.progress_bar = False
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


async def process_run(request, runs, db):
    """Mongo Processor for adding runs"""
    response = await process_simulation(**request)
    collection = db.get_collection("get_results")
    await collection.insert_one(response)
    await runs.add_run(response)


async def process_query(request, websocket: WebSocket):
    """Websocket processor for getting results"""
    run = await runs.get_run(**request)
    if run is None:
        collection = db.get_collection("get_results")
        r = await collection.find_one(request)
        if r is not None:
            r.pop("_id", None)
            run = r
    await websocket.send(json.dumps(run))
    # print(f"Response emitted!!\n{json.dumps(run)}")


async def process_payloads(websocket: WebSocket):
    global runs
    global db 
    async for request_payload in websocket:
        request = json.loads(request_payload)
        request.pop("_id", None)
        print(f"Got a request payload: {request}")

        # case: is a get results request
        if "simulation_id" in request and len(request) == 1:
            await process_query(request, websocket)
        else:
            # case: is a sim run request
            await process_run(request, runs, db)
        
        await asyncio.sleep(2.22)


async def process_queue(port=8765):
    async with websockets.serve(process_payloads, "localhost", port):
        print(f"WebSocket server running on ws://localhost:{port}")
        await asyncio.Future()
    

if __name__ == "__main__":
    asyncio.run(process_queue())


    
