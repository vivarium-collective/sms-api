"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""


import dataclasses as dc
import datetime
from typing import Any 

from fastapi import APIRouter, Depends, UploadFile, File, Body, Query
import fastapi
from vivarium.vivarium import Vivarium

from data_model.base import BaseClass
from data_model.gateway import RouterConfig
from data_model.simulation import SimulationRun
from data_model.vivarium import VivariumDocument
from gateway.handlers import auth
from gateway.handlers.app_config import root_prefix
from gateway.handlers.vivarium import VivariumFactory, new_id


API_PREFIX = "antibiotics"
LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
MAJOR_VERSION = 1


config = RouterConfig(
    router=APIRouter(), 
    prefix=root_prefix(MAJOR_VERSION) + f"/{API_PREFIX}",
    dependencies=[fastapi.Depends(auth.get_user)]
)
viv_factory = VivariumFactory()


@config.router.get("/test-authentication", operation_id="test-authentication", tags=["Antibiotics"])
async def test_authentication(user: dict = Depends(auth.get_user)):
    return user


@dc.dataclass
class AntibioticConfig(BaseClass):
    name: str 
    params: dict = dc.field(default_factory=dict)


@config.router.post("/launch-antibiotic", tags=["Antibiotics"])
async def launch_antibiotic(
    antibiotic_config: AntibioticConfig = AntibioticConfig(name="A.B.C", params={"concentration": 0.1122}),
    duration: float = Query(default=11.0),
) -> SimulationRun:
    # make sim id
    sim_id = new_id(antibiotic_config.name)

    # emit payload message to websocket or grpc

    return SimulationRun(
        id=sim_id,  # ensure users can use this to retrieve the data later
        last_updated=str(datetime.datetime.now())
    )

