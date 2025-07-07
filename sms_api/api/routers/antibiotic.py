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

from fastapi import APIRouter, HTTPException, Query

from sms_api.api.routers.core import run_vecoli_simulation
from sms_api.common.gateway.models import RouterConfig, ServerMode
from sms_api.log_config import setup_logging
from sms_api.simulation.hpc_utils import read_latest_commit
from sms_api.simulation.models import (
    EcoliSimulationRequest,
)
from sms_api.simulation.simulation_service import SimulationServiceHpc

logger = logging.getLogger(__name__)
setup_logging(logger)

LATEST_COMMIT = read_latest_commit()


def get_server_url(dev: bool = True) -> ServerMode:
    return ServerMode.DEV if dev else ServerMode.PROD


# -- app components -- #

# TODO: mount nfs driver


config = RouterConfig(router=APIRouter(), prefix="/antibiotic", dependencies=[])


@config.router.get("/simulator/versions", operation_id="get-antibiotics-simulator-versions", tags=["Simulators"])
async def get_antibiotics(
    git_repo_url: str = Query(default="https://github.com/CovertLab/vEcoli"),
    git_branch: str = Query(default="master"),
):
    hpc_service = SimulationServiceHpc()
    if hpc_service is None:
        logger.error("HPC service is not initialized")
        raise HTTPException(status_code=500, detail="HPC service is not initialized")

    try:
        return {"version": f"{git_repo_url}_{git_branch}"}
    except Exception as e:
        logger.exception("Error getting the latest simulator commit.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get("/simulation/run", operation_id="get-antibiotics-simulator-versions", tags=["Simulations"])
async def run_antibiotics(request: EcoliSimulationRequest):
    hpc_service = SimulationServiceHpc()
    if hpc_service is None:
        logger.error("HPC service is not initialized")
        raise HTTPException(status_code=500, detail="HPC service is not initialized")

    try:
        return await run_vecoli_simulation(request)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from e
