"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""

from fastapi import APIRouter
import fastapi
import process_bigraph

from common import auth
from data_model.gateway import RouterConfig
from gateway import root_prefix
from gateway import launch_scan
from gateway import VivariumFactory, fetch_vivarium, new_id, new_vivarium, pickle_vivarium

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

