"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""


import dataclasses as dc
import datetime
from typing import Any 

from fastapi import APIRouter, Depends, UploadFile, File, Body, Query
import fastapi
import process_bigraph
from vivarium.vivarium import Vivarium

from common import auth
from data_model.gateway import RouterConfig
from gateway.handlers.app_config import root_prefix
from gateway.handlers.multi import launch_scan
from gateway.handlers.vivarium import VivariumFactory, fetch_vivarium, new_id, new_vivarium, pickle_vivarium

from data_model.base import BaseClass
from data_model.simulation import SimulationRun
from data_model.vivarium import VivariumDocument


API_PREFIX = "sensitivity-analysis"
LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
MAJOR_VERSION = 1


config = RouterConfig(
    router=APIRouter(), 
    prefix=root_prefix(MAJOR_VERSION) + f"/{API_PREFIX}",
    dependencies=[fastapi.Depends(auth.get_user)]
)

viv_factory = VivariumFactory()

