"""This module assumes prior authentication/config and is generalized as much as possible."""
import json
import os
import shutil
import subprocess
import traceback
import tempfile as tmp
from typing import Callable

import fastapi
import numpy as np

from data_model.api import BulkMoleculeData, ListenerData, WCMIntervalData, WCMIntervalResponse, WCMSimulationRequest


__all__ = [
    "t",
    "run_vivarium",
    "get_results",
    "get_latest",
    "run_simulation",
    "interval_generator"
]


def absolute_path(p: str) -> str:
    """Return the abspath of the given p if file exists.
    """
    if os.path.exists(p):
        return os.path.abspath(p)
    else:
        raise FileNotFoundError(f'{p} either does not exist or is mis-declared.')


def run_simulation(config_path: str):
    """
    :param config_path: (str) Absolute path of the given simulation configuration .json file. MUST be an absolute path.
    """
    cmd = [
        "uv", "run",
        "--env-file", "/Users/alexanderpatrie/Desktop/repos/ecoli/vEcoli/.env",
        "--project", "/Users/alexanderpatrie/Desktop/repos/ecoli/vEcoli",
        "runscripts/workflow.py",
        "--config", "ecoli/composites/ecoli_configs/test_installation.json"
    ]

    return subprocess.run(cmd, check=True)


def t(duration: int, dt: float) -> list[float]:
    return np.arange(1, duration, dt).tolist()


def run_vivarium(dur: float, viv):
    if 'emitter' not in viv.get_state().keys():
        viv.add_emitter()
    return viv.run(dur)


def get_results(viv) -> list[dict]:
    return viv.get_results()  # type: ignore


def get_latest(viv) -> dict:
    # return viv.make_document()
    results = get_results(viv)
    if len(results):
        return results[-1]
    else:
        raise ValueError("There are no results available.")
    

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
    compile_simulation: Callable,
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

