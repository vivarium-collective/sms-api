"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""

import fastapi
from common import auth
from data_model.gateway import RouterConfig
from fastapi import APIRouter

from gateway import VivariumFactory, root_prefix

API_PREFIX = "inference"
LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
MAJOR_VERSION = 1


config = RouterConfig(
    router=APIRouter(),
    prefix=root_prefix(MAJOR_VERSION) + f"/{API_PREFIX}",
    dependencies=[fastapi.Depends(auth.get_user)],
)

viv_factory = VivariumFactory()
