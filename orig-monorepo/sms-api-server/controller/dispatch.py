import copy
import json
import os
import sys

import numpy as npy
from ecoli.experiments.ecoli_master_sim import EcoliSim

DEFAULT_ECOLISIM_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../resources/config/default.json")
DEFAULT_DURATION = 1111
DEFAULT_INTERVAL = 1.0


def compile_simulation(
    config_fp: str | None = None,
    experiment_id: str | None = None,
    duration: float | None = None,
    time_step: float | None = None,
    framesize: float | None = None,
    datadir: str | None = None,
    build: bool = True,
):
    # load config file TODO: replace with pbg doc!
    composite_config_fp = config_fp or DEFAULT_ECOLISIM_CONFIG_PATH
    with open(composite_config_fp) as f:
        config = copy.deepcopy(json.load(f))
    if experiment_id is not None:
        config["experiment_id"] = experiment_id

    # override save dir
    if datadir is not None:
        if not os.path.exists(datadir):
            os.makedirs(datadir, exist_ok=True)

        config["daughter_outdir"] = datadir

    # configure times and savetimes
    dur = duration or config.get("total_time", DEFAULT_DURATION)
    timestep = time_step or config.get("time_step", DEFAULT_INTERVAL)
    t = npy.arange(1, dur, framesize or timestep)
    config["total_time"] = dur
    config["time_step"] = timestep
    # config['save_times'] = t.tolist()
    config["save"] = True

    sim = EcoliSim(config, datadir)
    if build:
        sim.build_ecoli()
    return sim


def dispatch_simulation(sim: EcoliSim):
    return sim.run()


if __name__ == "__main__":
    experiment_id = sys.argv[1]
    duration = 111.0
    time_step = 0.1
    framesize = time_step
    sim = compile_simulation(experiment_id=experiment_id, duration=duration, time_step=time_step, framesize=framesize)
    dispatch_simulation(sim)
