import json
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from sms_api.api.request_examples import DEFAULT_SIMULATION_CONFIG
from sms_api.common.gateway.models import RouterConfig
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import get_settings
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
config = RouterConfig(router=APIRouter(), prefix="/configure", dependencies=[])


def DBService() -> DatabaseService:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    return db_service


def get_experiment_id_from_tag(experiment_tag: str) -> str:
    parts = experiment_tag.split("-")
    parts.remove(parts[-1])
    return "-".join(parts)


@config.router.post(
    path="/upload/simulation",
    operation_id="upload-simulation-config",
    tags=["Configurations - vEcoli"],
    description="Upload simulation config JSON",
)
async def upload_simulation_config(
    config_id: str | None = Query(default=None), sim_config: SimulationConfiguration = DEFAULT_SIMULATION_CONFIG
) -> UploadedSimulationConfig:
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


@config.router.post(
    path="/upload/analysis",
    operation_id="upload-analysis-config",
    tags=["Configurations - vEcoli"],
    description="Upload analysis config JSON",
)
async def upload_analysis_config(
    config_id: str | None = Query(default=None), sim_config: SimulationConfiguration = DEFAULT_SIMULATION_CONFIG
) -> UploadedAnalysisConfig:
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

        uploaded = UploadedAnalysisConfig(config_id=confid)
        return uploaded
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(path="/get", operation_id="get-simulation-config", tags=["Configurations - vEcoli"])
async def get_simulation_config(config_id: str) -> SimulationConfiguration:
    try:
        db_service = DBService()
        return await db_service.get_simulation_config(config_id=config_id)
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.delete(path="/remove", operation_id="delete-simulation-config", tags=["Configurations - vEcoli"])
async def delete_simulation_config(config_id: str) -> str:
    try:
        db_service = DBService()
        ssh = get_ssh_service(ENV)
        # delete from db
        await db_service.delete_simulation_config(config_id=config_id)

        # delete from remote fs
        config_path = f"{ENV.vecoli_config_dir}/{config_id}.json"
        await ssh.run_command(f"rm {config_path}")

        return f"Config {config_id} deleted successfully"
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(path="/versions", operation_id="list-simulation-configs", tags=["Configurations - vEcoli"])
async def list_simulation_configs() -> list[SimulationConfiguration]:
    try:
        db_service = DBService()
        return await db_service.list_simulation_configs()
    except Exception as e:
        logger.exception("Error getting configs")
        raise HTTPException(status_code=500, detail=str(e)) from e
