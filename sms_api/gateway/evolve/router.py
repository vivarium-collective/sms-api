"""
TODO: track down and re-implement the evolve method (unpickle, set, run, pickle) for i in duration
"""

import fastapi
from common import auth
from common.encryption.keydist import generate_keys
from common.managers import mongo_manager
from common.managers.db import write_vivarium
from data_model.gateway import RouterConfig
from data_model.vivarium import VivariumDocument, VivariumMetadata
from fastapi import APIRouter, Body, File, Query, UploadFile
from gateway import VivariumFactory, new_id, root_prefix
from process_bigraph import ProcessTypes
from vivarium.vivarium import Vivarium

LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
MAJOR_VERSION = 1


config = RouterConfig(
    router=APIRouter(),
    prefix=root_prefix(MAJOR_VERSION) + "/experimental",
    dependencies=[fastapi.Depends(auth.get_user)],
)


@config.router.post("/add/core", operation_id="add-core", tags=["Experimental"])
async def add_core(
    core_spec: UploadFile = File(..., description="new pbg.ProcessTypes instance with registered types and processes"),
):
    pass


@config.router.post("/create/vivarium", operation_id="create-vivarium", tags=["Experimental"])
async def create_vivarium(
    document: VivariumDocument | None = Body(default=None),
    name: str = Query(default="new_example"),
    protocol: str = Query(
        default="vivarium", description="This argument is not yet used, but will be to determine which core to use."
    ),  # TODO: implement this
) -> VivariumMetadata:
    new_vivarium_factory = VivariumFactory()

    v: Vivarium = new_vivarium_factory(document=document, core=ProcessTypes())
    viv_id = new_id(name)
    keys = generate_keys(secret_string=viv_id)
    await write_vivarium(viv_id, v, mongo_manager)

    return VivariumMetadata(viv_id)


@config.router.get("/get/vivarium", operation_id="get-vivarium", tags=["Experimental"])
async def get_vivarium(vivarium_id: str):
    pass
