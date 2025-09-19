"""
/configs: this router is dedicated to the upload and introspection of both analysis and simulation
    configuration JSON files
"""

import json
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from sms_api.common.gateway.models import RouterConfig
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import get_settings
from sms_api.data.models import AnalysisConfig
from sms_api.dependencies import (
    get_database_service,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    SimulationConfiguration,
    UploadedAnalysisConfig,
    UploadedSimulationConfig,
)

ENV = get_settings()

logger = logging.getLogger(__name__)
config = RouterConfig(router=APIRouter(), prefix="/configs", dependencies=[])


# -- utils -- #


def DBService() -> DatabaseService:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    return db_service


# -- endpoints -- #


@config.router.post(
    path="/simulation",
    operation_id="upload-simulation-config",
    tags=["Configurations - vEcoli"],
    summary="Upload custom config JSON to be used for simulation workflows",
)
async def upload_simulation_experiment_config(
    config: SimulationConfiguration,
    config_id: str = Query(description="Name by which you wish to save the config"),
) -> UploadedSimulationConfig:
    # here, simply write config serialized to tempdir locally then use that to scp upload to configs dir
    async def upload(config_id: str | None, sim_config: SimulationConfiguration) -> UploadedSimulationConfig:
        # NOTE: this endpoint should upload it to the logged-in client's dedicated dir
        if not sim_config.experiment_id:
            raise HTTPException(status_code=400, detail="Experiment id is required")
        if sim_config.experiment_id.startswith("<P"):
            raise HTTPException(status_code=400, detail="Experiment id is invalid")
        ssh = get_ssh_service(ENV)
        try:
            # store config in db
            db_service = DBService()
            user_suffix = str(uuid.uuid4()).split("-")[-1]  # TODO: let this be a reference instead to the user's id
            if config_id is None:
                config_id = "simconfig"
            confid = f"{config_id}-{user_suffix}"
            sim_config.experiment_id = f"{sim_config.experiment_id}-{user_suffix}"
            sim_config.emitter_arg["out_dir"] = ENV.simulation_outdir
            sim_config.daughter_outdir = ENV.simulation_outdir

            await db_service.insert_simulation_config(config_id=confid, config=sim_config)

            # upload config to hpc(vEcoli dir)
            with tempfile.TemporaryDirectory() as tmpdir:
                fname = f"{confid}.json"
                local = Path(tmpdir).absolute() / fname
                # write temp local
                with open(local, "w") as f:
                    json.dump(sim_config.model_dump(), f, indent=3)

                # upload temp local to remote(vEcoli configs dir)
                remote = Path(ENV.slurm_base_path) / "workspace" / "vEcoli" / "configs" / fname
                await ssh.scp_upload(local_file=local, remote_path=remote)

            uploaded = UploadedSimulationConfig(config_id=confid)
            return uploaded
        except Exception as e:
            logger.exception("Error uploading simulation config")
            raise HTTPException(status_code=500, detail=str(e)) from e

    return await upload(config_id=config_id, sim_config=config)


@config.router.post(
    path="/analysis",
    operation_id="upload-analysis-config",
    tags=["Configurations - vEcoli"],
    summary="Upload custom config JSON to be used for analysis workflows",
)
async def upload_analysis_config(
    config: AnalysisConfig,
    config_id: str = Query(description="Name by which you wish to save the config"),
) -> UploadedAnalysisConfig:
    # here, simply write config serialized to tempdir locally then use that to scp upload to configs dir
    async def upload(config_id: str, analysis_config: AnalysisConfig) -> UploadedAnalysisConfig:
        # NOTE: this endpoint should upload it to the logged-in client's dedicated dir
        ssh = get_ssh_service(ENV)
        try:
            # store config in db
            # db_service = DBService()
            user_suffix = str(uuid.uuid4()).split("-")[-1]  # TODO: let this be a reference instead to the user's id
            if config_id is None:
                config_id = "analysis"
            confid = f"{config_id}-{user_suffix}"

            # await db_service.insert_simulation_config(config_id=confid, config=analysis_config)
            # TODO: adjust the above to an added insert_analysis_config method

            # upload config to hpc(vEcoli dir)
            with tempfile.TemporaryDirectory() as tmpdir:
                fname = f"{confid}.json"
                local = Path(tmpdir).absolute() / fname
                # write temp local
                with open(local, "w") as f:
                    json.dump(analysis_config.model_dump(), f, indent=3)

                # upload temp local to remote(vEcoli configs dir)
                remote = Path(ENV.slurm_base_path) / "workspace" / "vEcoli" / "configs" / fname
                await ssh.scp_upload(local_file=local, remote_path=remote)

            uploaded = UploadedAnalysisConfig(config_id=confid)
            return uploaded
        except Exception as e:
            logger.exception("Error uploading analysis config")
            raise HTTPException(status_code=500, detail=str(e)) from e

    return await upload(config_id=config_id, analysis_config=config)


@config.router.get(
    path="",
    operation_id="list-configs",
    tags=["Configurations - vEcoli"],
    summary="Get the config ids of all available configurations",
)
async def list_all_configs() -> str:
    ssh = get_ssh_service(ENV)
    ret, stdout, stderr = await ssh.run_command(f"ls {ENV.vecoli_config_dir}")
    return stdout


# @config.router.get(
#     path="",
#     operation_id="list-configs",
#     tags=["Configurations - vEcoli"],
#     summary="Get the config ids of all available configurations",
# )
# async def list_all_configs() -> str:
#     # here, simply recurse configs dir in FS and return config ids without ext
#     try:
#         db_service = DBService()
#         return await db_service.list_simulation_configs()
#     except Exception as e:
#         logger.exception("Error getting configs")
#         raise HTTPException(status_code=500, detail=str(e)) from e


# @config.router.get(
#     path="/{id}",
#     operation_id="get-config",
#     tags=["Configurations - vEcoli"],
#     summary="Fetch a single config json from the database",
# )
# async def get_uploaded_config(id: str) -> SimulationConfiguration:
#     # here, read config json from db from its id
#     try:
#         db_service = DBService()
#         return await db_service.get_simulation_config(config_id=id)
#     except Exception as e:
#         logger.exception("Error uploading simulation config")
#         raise HTTPException(status_code=500, detail=str(e)) from e


# @config.router.put(
#     path="/{id}",
#     operation_id="overwrite-simulation-config",
#     tags=["Configurations - vEcoli"],
#     summary="Change an existing config json in the database and remote fs",
# )
# async def overwrite_simulation_config(id: str, config: SimulationConfiguration) -> int:
#     # here:
#     # 1. first confirm that config by id exists in the db
#     # 2. if exists, overwrite row in db with given config at id
#     # 3. scp upload (basically upload-simulation-config) to same spot in remote fs
#     # 4. return confirmation
#     return 0


# @config.router.delete(
#     path="/{id}",
#     operation_id="delete-simulation-config",
#     tags=["Configurations - vEcoli"],
#     summary="Delete an existing config json in the database and remote fs",
# )
# async def delete_simulation_config(id: str) -> int:
#     # here:
#     # 1. first confirm that config by id exists in the db
#     # 2. if exists, delete row in db with given config at id
#     # 3. ssh.run_command('rm $CONFIG_PATH')
#     # 4. return confirmation
#     try:
#         db_service = DBService()
#         ssh = get_ssh_service(ENV)
#         # delete from db
#         await db_service.delete_simulation_config(config_id=config_id)
#         # delete from remote fs
#         config_path = f"{ENV.vecoli_config_dir}/{config_id}.json"
#         await ssh.run_command(f"rm {config_path}")
#         return f"Config {config_id} deleted successfully"
#     except Exception as e:
#         logger.exception("Error uploading simulation config")
#         raise HTTPException(status_code=500, detail=str(e)) from e
#     return 0
