"""
TODO: track down and re-implement the evolve method (unpickle, set, run, pickle) for i in duration
"""


from fastapi import APIRouter, Depends, UploadFile, File, Body, Query
import fastapi
from vivarium.vivarium import Vivarium

from data_model.gateway import RouterConfig
from data_model.vivarium import VivariumDocument, VivariumMetadata
from gateway.handlers import auth
from gateway.handlers.app_config import root_prefix
from gateway.handlers.encryption import db
from gateway.handlers.vivarium import VivariumFactory, new_id


LOCAL_URL = "http://localhost:8080"
PROD_URL = ""  # TODO: define this
MAJOR_VERSION = 1


config = RouterConfig(
    router=APIRouter(), 
    prefix=root_prefix(MAJOR_VERSION) + "/evolve",
    dependencies=[fastapi.Depends(auth.get_user)]
)


@config.router.get("/test-authentication", operation_id="test-authentication", tags=["Evolve"])
async def test_authentication(user: dict = Depends(auth.get_user)):
    return user


@config.router.post('/add/core', operation_id='add-core', tags=["Evolve"])
async def add_core(
    core_spec: UploadFile = File(..., description="new pbg.ProcessTypes instance with registered types and processes")):
    pass 


@config.router.post(
    '/create', 
    operation_id='create', 
    tags=["Evolve"]
)
async def create_vivarium(
    private_key: str = Query(default="1"),  # make_test_password("example")
    document: VivariumDocument | None = Body(default=None),
    name: str = Query(default="new_example"),
    secure: bool = Query(default=True, description="This argument is not yet used, but will be whether or not to use the community API (secure)"),  # TODO: implement this
    protocol: str = Query(default="vivarium", description="This argument is not yet used, but will be to determine which core to use.")  # TODO: implement this
) -> VivariumMetadata:  
    new_vivarium_factory = VivariumFactory()

    v: Vivarium = new_vivarium_factory(document=document)
    viv_id = new_id(name)
    db.write(v, viv_id, private_key.encode('utf-8'))
    
    return VivariumMetadata(viv_id)
