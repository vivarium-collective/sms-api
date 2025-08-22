"""
Ptools sub API
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from sms_api.common.gateway.models import RouterConfig, ServerMode
from sms_api.data.biocyc_service import BiocycService
from sms_api.data.models import BiocycComponent, BiocycData
from sms_api.simulation.hpc_utils import read_latest_commit

logger = logging.getLogger(__name__)

LATEST_COMMIT = read_latest_commit()


def get_server_url(dev: bool = True) -> ServerMode:
    return ServerMode.DEV if dev else ServerMode.PROD


# -- app components -- #

# TODO: mount nfs driver


config = RouterConfig(router=APIRouter(), prefix="/ptools", dependencies=[])


@config.router.get(
    path="/component",
    operation_id="download-ptools-data",
    tags=["Data"],
    summary="Download data for a given component from the Pathway Tools REST API",
)
async def download_ptools_data(
    object_id: str = Query(
        ..., example="--TRANS-ACENAPHTHENE-12-DIOL", description="Object ID of the component you wish to fetch"
    ),
    organism_id: str = Query(default="ECOLI"),
    raw: bool = Query(
        default=False,
        description="If True, return an object containing both the BioCyc component and the request params/data",
    ),
) -> BiocycData | BiocycComponent:
    try:
        biocyc_svc = BiocycService()
        biocyc_data = biocyc_svc.get_data(obj_id=object_id, org_id=organism_id)
        return biocyc_data if raw else biocyc_data.to_dto()
    except Exception as e:
        logger.exception("Error.")
        raise HTTPException(status_code=500, detail=str(e)) from e
