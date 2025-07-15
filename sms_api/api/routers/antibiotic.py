"""
[x] base sim (cached)
- antibiotic
- biomanufacturing
- batch variant endpoint
- design specific endpoints.
- downsampling ...
- biocyc id
- api to download the data
- marimo instead of Jupyter notebooks....(auth). ... also on gov cloud.
- endpoint to send sql like queries to parquet files back to client
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from sms_api.api.routers.core import run_vecoli_simulation
from sms_api.common.gateway.models import RouterConfig, ServerMode
from sms_api.dependencies import get_simulation_service
from sms_api.simulation.hpc_utils import read_latest_commit
from sms_api.simulation.models import (
    EcoliExperiment,
    EcoliSimulationRequest,
)

logger = logging.getLogger(__name__)

LATEST_COMMIT = read_latest_commit()


def get_server_url(dev: bool = True) -> ServerMode:
    return ServerMode.DEV if dev else ServerMode.PROD


# -- app components -- #

# TODO: mount nfs driver


config = RouterConfig(router=APIRouter(), prefix="/antibiotic", dependencies=[])


@config.router.get(
    path="/simulation/run",
    response_model=EcoliExperiment,
    operation_id="get-antibiotics-simulator-versions",
    tags=["Simulations"],
    summary="Run vEcoli simulation with antibiotics (not yet implemented)",
)
async def run_antibiotics(background_tasks: BackgroundTasks, request: EcoliSimulationRequest) -> EcoliExperiment:
    hpc_service = get_simulation_service()
    if hpc_service is None:
        logger.error("HPC service is not initialized")
        raise HTTPException(status_code=500, detail="HPC service is not initialized")

    try:
        return await run_vecoli_simulation(sim_request=request, background_tasks=background_tasks)
    except Exception as e:
        logger.exception("Could not run simulation.")
        raise HTTPException(status_code=500, detail=str(e)) from e
