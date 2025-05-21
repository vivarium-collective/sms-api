"""This module assumes prior authentication/config and is generalized as much as possible."""
import os
import subprocess

import numpy as np
import process_bigraph as pbg
from vivarium.vivarium import Vivarium


__all__ = [
    "t",
    "run_vivarium",
    "get_results",
    "get_latest",
    "run_simulation"
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


def run_vivarium(dur: float, viv: Vivarium):
    if 'emitter' not in viv.get_state().keys():
        viv.add_emitter()
    return viv.run(dur)


def get_results(viv: Vivarium) -> list[dict]:
    return viv.get_results()  # type: ignore


def get_latest(viv: Vivarium) -> dict:
    # return viv.make_document()
    results = get_results(viv)
    if len(results):
        return results[-1]
    else:
        raise ValueError("There are no results available.")

