"""Endpoint definitions for the CommunityAPI. NOTE: Users of this API must be first authenticated."""

from fastapi import APIRouter, HTTPException
import fastapi
from gateway import (
    MIC, 
    PAP, 
    AntibioticConfig, 
    AntibioticParams, 
    AntibioticResponse, 
    get_MIC_curve, 
    get_PAP_curve, 
    get_single_cell_trajectories as single_cell_trajectories, 
    list_available_parameters as available_parameters, 
    simulate_antibiotic
)

from data_model.gateway import RouterConfig
from common import auth
from gateway import root_prefix
from gateway import VivariumFactory, new_id


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


@config.router.post("/simulate-antibiotic-response", tags=["Antibiotics"])
async def simulate_antibiotic_response(antibiotic_name: str, params: AntibioticParams) -> AntibioticResponse:
    try:
        # TODO: instead, return a simulation run and emit payload to socket
        response = simulate_antibiotic(antibiotic_name, params)
        return response
    except Exception as e:
        raise HTTPException(400, str(e))


@config.router.post("/get-MIC-curve", tags=["Antibiotics"])
async def get_mic_curve(params: AntibioticParams) -> MIC:
    try:
        response = get_MIC_curve(params)
        return response
    except Exception as e:
        raise HTTPException(400, "Something went wrong.")


@config.router.post("/get-PAP-curve", tags=["Antibiotics"])
async def get_pap_curve(params: AntibioticParams) -> PAP:
    try:
        response = get_PAP_curve(params)
        return response
    except Exception as e:
        raise HTTPException(400, str(e))


@config.router.post("/get-single-cell-trajectories", tags=["Antibiotics"])
async def get_single_cell_trajectories(n_cells: int, params: AntibioticParams):
    try:
        response = single_cell_trajectories(n_cells, params)
        return response 
    except Exception as e:
        raise HTTPException(400, str(e))


@config.router.post("/list-available-parameters", tags=["Antibiotics"])
async def list_available_parameters():
    try:
        response = available_parameters()
        return response 
    except Exception as e:
        raise HTTPException(500, str(e))
