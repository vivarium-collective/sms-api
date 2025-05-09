"""This module assumes prior authentication/config and is generalized as much as possible."""


import numpy as np
import process_bigraph as pbg
from vivarium.vivarium import Vivarium


__all__ = [
    "t",
    "run_vivarium",
    "get_results",
    "get_latest",
]


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

