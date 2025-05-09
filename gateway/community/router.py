"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""


import dataclasses as dc
import datetime
from typing import Any 

from fastapi import APIRouter, Depends, UploadFile, File, Body, Query
import fastapi
import process_bigraph
from vivarium import Vivarium

from api.data_model.gateway import RouterConfig
from api.gateway.community import auth
from api.gateway.handlers.app_config import root_prefix
from api.gateway.handlers.multi import launch_scan
from api.gateway.handlers.vivarium import VivariumFactory, fetch_vivarium, new_id, new_vivarium, pickle_vivarium
from ecoli import ecoli_core

from api.data_model.base import BaseClass
from api.data_model.simulation import SimulationRun
from api.data_model.vivarium import VivariumDocument
from api.gateway.community.auth import get_user



LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
MAJOR_VERSION = 1


config = RouterConfig(
    router=APIRouter(), 
    prefix=root_prefix(MAJOR_VERSION) + "/community",
    dependencies=[fastapi.Depends(auth.get_user)]
)

viv_factory = VivariumFactory()

# e54d4431-5dab-474e-b71a-0db1fcb9e659

@config.router.get("/test-authentication", operation_id="test-authentication", tags=["CommunityAPI"])
async def test_authentication(user: dict = Depends(get_user)):
    return user


@config.router.post("/run", tags=["CommunityAPI"])
async def run_simulation(
    document: VivariumDocument,
    duration: float = Query(default=11.0),
    name: str = Query(default="community_simulation")
) -> SimulationRun:
    """TODO: instead, here emit a new RequestMessage to gRPC to server with document, duration, and sim_id and run
        it there, then storing the secured results in the server, and then return a sim result confirmation with sim_id
    """
    # make sim id
    sim_id = new_id(name)

    # emit payload message to websocket or grpc

    return SimulationRun(
        id=sim_id,  # ensure users can use this to retrieve the data later
        last_updated=str(datetime.datetime.now())
    )


@config.router.post(
    "/scan", 
    tags=["CommunityAPI"], 
    description="Launch n of the same/similar simulations in parallel async"
)
async def run_scan(
    document: VivariumDocument, 
    duration: float, 
    n_threads: int, 
    perturbation_config: dict[str, Any] | None = None,
    distribution_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    return launch_scan(document, duration, n_threads, perturbation_config, distribution_config)


# TODO: have the ecoli interval results call encryption.db.write for each interval
# TODO: have this method call encryption.db.read for interval data
@config.router.get(
    '/get/results', 
    operation_id='get-results', 
    tags=["CommunityAPI"]
)
async def get_results(key: str, simulation_id: str):
    # for now, data does not need to be encrypted as this api will only be 
    #  available if properly authenticated with an API Key.
    # viv = read(EncodedKey(key), vivarium_id)
    pass


@config.router.post('/new-vivarium')
async def create_vivarium(name: str, document: VivariumDocument | None = None):
    return new_vivarium(name, document)


@config.router.get('/get-vivarium')
async def get_vivarium(viv_id: str = Query(default="testd59659a7-f746-4ce3-a8d1-aeb2e843f208")):
    viv = fetch_vivarium(viv_id)
    return viv.make_document()


@config.router.post('/run-vivarium')
async def run_vivarium(
    viv_id: str = Query(default="testd59659a7-f746-4ce3-a8d1-aeb2e843f208"), 
    duration: float = Query(default=11.11)
):
    try:
        # get viv pickle
        viv = fetch_vivarium(viv_id)
        if "emitter" not in viv.get_state().keys():
            viv.add_emitter()

        # run
        viv.run(duration)  # TODO: add timestep?

        # get current state
        current = viv.make_document()

        # save state
        pickle_vivarium(viv, viv_id)

        return current

    except Exception as e:
        raise fastapi.HTTPException(404, str(e))


@config.router.post('/sensitivity-analysis')
async def sensitivity_analysis(parameter_path: str):
    pass


# -- static data -- #

@config.router.get('/get/processes', tags=["CommunityAPI"])
async def get_registered_processes() -> list[str]:
    # TODO: implement this for ecoli_core
    from ecoli import ecoli_core
    return list(ecoli_core.process_registry.registry.keys())


@config.router.get('/get/types', tags=["CommunityAPI"])
async def get_registered_types() -> list[str]:
    # TODO: implement this for ecoli_core
    from ecoli import ecoli_core
    return list(ecoli_core.types().keys())