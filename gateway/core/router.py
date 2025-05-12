"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""


import dataclasses as dc
import datetime
from typing import Any 

from fastapi import APIRouter, Depends, UploadFile, File, Body, Query
import fastapi
import process_bigraph
from vivarium.vivarium import Vivarium

from data_model.gateway import RouterConfig
from gateway.handlers import auth
from gateway.handlers.app_config import root_prefix
from gateway.handlers.multi import launch_scan
from gateway.handlers.vivarium import VivariumFactory, fetch_vivarium, new_id, new_vivarium, pickle_vivarium

from data_model.base import BaseClass
from data_model.simulation import SimulationRun
from data_model.vivarium import VivariumDocument
from gateway.handlers.auth import get_user



LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
MAJOR_VERSION = 1


config = RouterConfig(
    router=APIRouter(), 
    prefix=root_prefix(MAJOR_VERSION) + "/core",
    dependencies=[fastapi.Depends(auth.get_user)]
)

viv_factory = VivariumFactory()


@config.router.get("/test-authentication", operation_id="test-authentication", tags=["Core"])
async def test_authentication(user: dict = Depends(get_user)):
    return user


@config.router.post("/run", tags=["Core"])
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


# TODO: have the ecoli interval results call encryption.db.write for each interval
# TODO: have this method call encryption.db.read for interval data
@config.router.get(
    '/get/results', 
    operation_id='get-results', 
    tags=["Core"]
)
async def get_results(key: str, simulation_id: str):
    # for now, data does not need to be encrypted as this api will only be 
    #  available if properly authenticated with an API Key.
    # viv = read(EncodedKey(key), vivarium_id)
    pass


# -- static data -- #

@config.router.get('/get/processes', tags=["Core"])
async def get_registered_processes() -> list[str]:
    # TODO: implement this for ecoli_core
    from ecoli import ecoli_core
    return list(ecoli_core.process_registry.registry.keys())


@config.router.get('/get/types', tags=["Core"])
async def get_registered_types() -> list[str]:
    # TODO: implement this for ecoli_core
    from ecoli import ecoli_core
    return list(ecoli_core.types().keys())