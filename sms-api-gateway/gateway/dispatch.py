from ecoli.experiments.ecoli_master_sim import EcoliSim
import numpy as npy
import os
import json 
import sys 
import copy

DEFAULT_ECOLISIM_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "../resources/config/default.json"
)
DEFAULT_DURATION = 1111
DEFAULT_INTERVAL = 1.0


def dispatch_simulation(
    config_fp: str | None = None, 
    experiment_id: str | None = None,
    duration: float | None = None, 
    time_step: float | None = None,
    framesize: float | None = None,
    datadir: str | None = None,
):
    # load config file TODO: replace with pbg doc!
    composite_config_fp = config_fp or DEFAULT_ECOLISIM_CONFIG_PATH
    with open(composite_config_fp, 'r') as f:
        config = copy.deepcopy(json.load(f))
    if experiment_id is not None:
        config['experiment_id'] = experiment_id
    print('Running sim')
    # override save dir
    if datadir is not None:
        config['daughter_outdir'] = datadir

    # configure times and savetimes
    dur = duration or config.get('total_time', DEFAULT_DURATION)
    timestep = time_step or config.get('time_step', DEFAULT_INTERVAL)
    t = npy.arange(1, dur, framesize or timestep)
    config['save'] = True
    config['save_times'] = t.tolist()
    # build, compile, and run sim
    # if datadir is not None and not os.path.exists(datadir):
    #     os.mkdir(datadir)
    
    sim = EcoliSim(config, datadir)
    sim.build_ecoli()
    sim.total_time = dur

    return sim.run()


if __name__ == "__main__":
    experiment_id = sys.argv[1]
    duration = 111.0
    time_step = 0.1
    framesize = time_step
    dispatch_simulation(
        experiment_id=experiment_id,
        datadir=f'./data/{experiment_id}', 
        time_step=time_step,
        framesize=time_step
    )

    
