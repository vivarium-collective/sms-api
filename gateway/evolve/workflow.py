"""
Bigraph Workflow: New workflow runner to replace nextflow, allowing for parameterization via JSON

NOTE: this is very analogous to processing API requests and a common thread will be drawn here.
TODO: Extract API functionality/structure from this workflow and visa-versa
"""

import dataclasses
import hashlib
import json
import os
import pickle
import sys
from typing import Any

import typer
import numpy as np

from vivarium.vivarium import Vivarium
from ecoli import ecoli_core


cli = typer.Typer()


@dataclasses.dataclass
class Coordinate:
    x: float 
    y: float
    z: float

    
@dataclasses.dataclass
class ZoneCoordinate:
    min: Coordinate
    max: Coordinate

    def __post_init__(self):
        if not self.min:
            self.min = Coordinate(11, 11, 11)
            self.max = Coordinate(-11, -11, 22)


@dataclasses.dataclass
class ZoneCoordinates:
    north: ZoneCoordinate
    south: ZoneCoordinate
    east: ZoneCoordinate
    west: ZoneCoordinate


@dataclasses.dataclass
class ZoneData:
    id: str
    timezone_format: str
    coordinates: ZoneCoordinates


@dataclasses.dataclass
class Client:
    id: str
    location: tuple[float, float, float]
    zone_data: ZoneData


@dataclasses.dataclass
class Authentication:
    client: Client
    metadata: dict = dataclasses.field(default_factory=dict)

    @property
    def hash(self):
        v = pickle.dumps(json.dumps(self.metadata))
        return hashlib.sha256(v).hexdigest()
    
    def prove(self, key_hash: str):
        return self.hash == key_hash
    

class WorkflowRunner:
    def __init__(self, auth_settings: dict | None = None):
        self.auth_settings = auth_settings or {}
    
    def new_vivarium(self, core, doc=None):
        return Vivarium(
            core=core, processes=core.process_registry.registry, types=core.types(), document=doc
        )
    
    def pickle_vivarium(self, viv_id: str, viv: Vivarium):
        """TODO: let this method take in a vivarium instance (stateful), pickle it, and save it to the given path"""
        pickle_path = self.lookup_pickle_path(viv_id)

        # TODO: write to bucket
        pass

    def unpickle_vivarium(self, path: str):
        with open(path, 'rb') as f:
            return pickle.load(f)
    
    def lookup_pickle_path(self, vivarium_id: str) -> str:
        """TODO: let this method take in a vivarium_id and search the secure vivarium instance bucket for the appropriate path"""
        return ""
    
    def set_vivarium(self, vivarium_id: str, viv: Vivarium):
        # TODO: replace this with an authenticated request
        return self.pickle_vivarium(vivarium_id, viv)
    
    def get_vivarium(self, vivarium_id: str | None = None, doc: dict | None = None):
        if vivarium_id is not None:
            pickle_path = self.lookup_pickle_path(vivarium_id)
            return self.unpickle_vivarium(pickle_path)
        else:
            return self.new_vivarium(core=ecoli_core, doc=doc)

    def run_simulation(self, duration: float, doc: dict, experiment_id: str, out_dir: str, vivarium_id: str | None = None):
        # get current vivarium
        viv = self.get_vivarium(vivarium_id=vivarium_id, doc=doc)
        viv.add_emitter()
        
        # run
        viv.run(duration)
        results = viv.get_results()

        # export results TODO: replace this with secure emission
        viv.save(filename=f"{experiment_id}.json", outdir=out_dir)

        # repickle vivarium to secure location with latest state
        self.set_vivarium(vivarium_id or "", viv)
        return {
            "data": results
        }
    
    def _parse_args(self, args: list[float | int]):
        return [str(arg) for arg in args]


@cli.command(short_help="Parameterize and write a new workflow experiment as JSON to ecoli experiments.")
def new(duration: float, document_path: str, composite_id: str):
    schema = locals()
    with open(f"ecoli/composites/ecoli_configs/{composite_id}.json", "w") as fp:
        json.dump(schema, fp, indent=4)
    

@cli.command(short_help="Run a Vivarium Workflow.")
def run(config_path: str, out_dir: str):
    # config_path = sys.argv[1]

    with open(config_path) as f:
        config = json.load(f)

    duration = config["duration"]
    doc = config["document_path"]
    experiment_id = config["composite_id"]

    runner = WorkflowRunner()

    result = runner.run_simulation(duration, doc, experiment_id, out_dir)
    results_path = os.path.join(out_dir, f"{experiment_id}.json")
    with open(results_path, 'r') as f:
        result_data = json.load(f)

    print(f'Results:\n{result_data}\n-----END-----\n')


@cli.command(short_help="Get a Vivarium instance.")
def get(vivarium_id: str, auth):
    print(f"Fetching secure pickle path for {vivarium_id}")


if __name__ == "__main__":
    # TODO: this is interchangable with Requests! :)
    cli()
