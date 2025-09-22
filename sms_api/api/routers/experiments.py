"""
/experiments: this router is dedicated to the running and introspection of experiments (getting output pq data)
"""

import datetime
import json
import logging
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from sms_api.common.gateway.io import get_zip_buffer, write_zip_buffer
from sms_api.common.gateway.models import RouterConfig, ServerMode
from sms_api.common.gateway.utils import get_simulator
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import get_settings
from sms_api.data.parquet_service import ParquetService
from sms_api.dependencies import (
    get_database_service,
    get_simulation_service,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.handlers import launch_vecoli_simulation
from sms_api.simulation.models import (
    EcoliExperimentDTO,
    EcoliExperimentRequestDTO,
    EcoliSimulationDTO,
    ExperimentMetadata,
    JobStatus,
    SimulationConfiguration,
    SimulationRun,
    SimulatorVersion,
)

ENV = get_settings()

logger = logging.getLogger(__name__)
config = RouterConfig(router=APIRouter(), prefix="/experiments", dependencies=[])
# config = RouterConfig(router=APIRouter(), prefix="/wcm", dependencies=[])


# -- service and data model -- #


def DBService() -> DatabaseService:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    return db_service


def get_server_url(dev: bool = True) -> ServerMode:
    return ServerMode.DEV if dev else ServerMode.PROD


def get_experiment_id_from_tag(experiment_tag: str) -> str:
    parts = experiment_tag.split("-")
    parts.remove(parts[-1])
    return "-".join(parts)


def generate_zip(file_paths: list[tuple[Path, str]]) -> Generator[Any]:
    """
    Generator function to stream a zip file dynamically.
    """
    # Use BytesIO as an in-memory file-like object for chunks
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
        for file_path, arcname in file_paths:
            # arcname is the filename inside the zip (can handle non-unique names)
            zip_file.write(file_path, arcname=arcname)
    buffer.seek(0)
    yield from buffer


# -- endpoints -- #


async def read_config_file(config_file: UploadFile) -> SimulationConfiguration:
    file_contents = await config_file.read()
    config = SimulationConfiguration(**json.loads(file_contents))
    for attrname in list(SimulationConfiguration.model_fields.keys()):
        attr = getattr(config, attrname)
        if attr is None:
            delattr(config, attrname)
        if isinstance(attr, (list, dict)) and not len(attr):
            delattr(config, attrname)
        # if isinstance(attr, list) or isinstance(attr, dict):
        #     if not len(attr):
        #         delattr(config, attrname)
    return config


"""
async def run_analysis(request: AnalysisRequest):
    try:
        db_service = get_database_service()
        config = AnalysisConfig.from_request(request)
        analysis_name = request.analysis_name
        last_updated = str(datetime.datetime.now())
        analysis = await db_service.insert_analysis(name=analysis_name, config=config, last_updated=last_updated)
        slurmjob_id = await dispatch(
            analysis=analysis, simulator_hash=get_simulator().git_commit_hash, env=ENV, logger=logger
        )
        return analysis
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e
"""


@config.router.post(
    path="",
    operation_id="run-sim-experiment",
    response_model=EcoliSimulationDTO,
    tags=["Simulations - vEcoli"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="Launches a nextflow-powered vEcoli simulation workflow",
)
async def run_simulation(
    config: SimulationConfiguration, metadata: ExperimentMetadata | None = None
) -> EcoliSimulationDTO:
    # validate services
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")

    # construct params
    simulator: SimulatorVersion = get_simulator()
    if config.experiment_id is None:
        raise HTTPException(status_code=400, detail="Experiment ID is required")

    ecoli_experiment: EcoliSimulationDTO = await db_service.insert_ecoli_experiment(
        config=config, metadata=metadata, last_updated=str(datetime.datetime.now())
    )

    # now do the following:
    # 1. get experiment id from config
    # 2. Get slurmjobname
    # async def dispatch(
    #         analysis: ExperimentAnalysisDTO,
    #         simulator_hash: str,
    #         env: Settings,
    #         logger: logging.Logger
    # ) -> int:
    #     experiment_id = analysis.config.analysis_options.experiment_id[0]
    #     slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)
    #     base_path = Path(env.slurm_base_path)
    #     slurm_log_file = base_path / f"prod/htclogs/{experiment_id}.out"    #
    #     slurm_script = script(
    #         slurm_log_file=slurm_log_file,
    #         slurm_job_name=slurmjob_name,
    #         env=env,
    #         latest_hash=simulator_hash,
    #         analysis=analysis,
    #         # experiment_id=experiment_id,
    #     )   #
    #     ssh = get_ssh_service(env)
    #     slurmjob_id = await _submit(
    #         config=analysis.config,
    #         experiment_id=experiment_id,
    #         script_content=slurm_script,
    #         slurm_job_name=slurmjob_name,
    #         env=env,
    #         ssh=ssh,
    #     )   #
    #     return slurmjob_id

    try:
        return ecoli_experiment
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/launch",
    operation_id="run-experiment",
    response_model=EcoliExperimentDTO,
    tags=["Simulations - vEcoli"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="Launches a nextflow-powered vEcoli simulation workflow",
)
async def launch_simulation(
    config_id: str | None = Query(default=None),
    config_file: UploadFile | str | None = File(default=None),  # noqa: B008
    # overrides: Optional[ConfigOverrides] = None,
    # metadata: Mapping[str, str] | None = None,
    # TODO: enable overrides here, not variants directly
    #  (variants should be specified as a top level key-val in overrides,
    #   mirroring the structure of simulation config JSON directly,
    #   for now assume knowledge of configs available in db via list endpoint...
) -> EcoliExperimentDTO:
    # validate services
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")

    # construct params
    simulator: SimulatorVersion = get_simulator()
    overrides = None

    config = await read_config_file(config_file) if config_file else None
    if config is None and config_id is None:
        raise HTTPException(status_code=404, detail="No configuration provided")

    request = EcoliExperimentRequestDTO(
        config_id=config_id if config is None else config.experiment_id, overrides=overrides
    )

    try:
        return await launch_vecoli_simulation(
            request=request,
            simulator=simulator,
            metadata={"creator": "Alexander Patrie", "publication": "myjournal"},
            simulation_service_slurm=sim_service,
            database_service=db_service,
            config=config,
        )
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(path="/get", operation_id="fetch-experiment", tags=["Simulations - vEcoli"])
async def get_experiment(experiment_id: str) -> EcoliExperimentDTO:
    try:
        db_service = DBService()
        return await db_service.get_experiment(experiment_id=experiment_id)
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.delete(path="/remove", operation_id="remove-experiment", tags=["Simulations - vEcoli"])
async def delete_experiment(experiment_id: str) -> str:
    try:
        db_service = DBService()
        # delete from db
        await db_service.delete_experiment(experiment_id=experiment_id)
        return f"Experiment {experiment_id} deleted successfully"
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(path="/versions", operation_id="list-all-experiments", tags=["Simulations - vEcoli"])
async def list_experiments() -> list[EcoliExperimentDTO]:
    try:
        db_service = DBService()
        return await db_service.list_experiments()
    except Exception as e:
        logger.exception("Error getting experiments")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/status",
    response_model=SimulationRun,
    operation_id="get-simulation-experiment-status",
    tags=["Simulations - vEcoli"],
    dependencies=[Depends(get_database_service)],
    summary="Get the simulation status record by its ID",
)
async def get_simulation_status(experiment_tag: str = Query(...)) -> SimulationRun:
    try:
        slurmjob_id = experiment_tag.split("-")[-1]
        # slurmjob_id = get_jobid_by_experiment(experiment_id)
        ssh_service = get_ssh_service()
        slurm_user = ENV.slurm_submit_user
        statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
        status: str = statuses[1].split("\n")[0].split()[-2]
        return SimulationRun(id=experiment_tag, status=JobStatus[status])
    except Exception as e:
        logger.exception(
            """Error getting simulation status.\
                Are you sure that you've passed the experiment_tag? (not the experiment id)
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simlog",
    # response_model=SimulationRun,
    # operation_id="get-simulation-experiment-status",
    tags=["Simulations - vEcoli"],
    dependencies=[Depends(get_database_service)],
    summary="Get the simulation status record by its ID",
)
async def get_simlog(experiment_id: str = Query(...)):
    try:
        # slurmjob_id = get_jobid_by_experiment(experiment_id)
        ssh_service = get_ssh_service()
        slurm_user = ENV.slurm_submit_user
        ret, stdout, stderr = await ssh_service.run_command(
            f"cd /home/FCAM/svc_vivarium/workspace && make slurmlog id={experiment_id}"
        )
        return stdout
    except Exception as e:
        logger.exception(
            """Error getting simulation status.\
                Are you sure that you've passed the experiment_tag? (not the experiment id)
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/log",
    operation_id="get-simulation-experiment-log",
    tags=["Simulations - vEcoli"],
    summary="Get the simulation log record of a given experiment",
)
async def get_simulation_log(experiment_id: str = Query(...)) -> str:
    try:
        # slurmjob_id = get_jobid_by_experiment(experiment_id)
        ssh_service = get_ssh_service()
        # slurm_user = env.slurm_submit_user
        returncode, stdout, stderr = await ssh_service.run_command(
            f"cat {ENV.slurm_base_path!s}/prod/htclogs/{experiment_id}.out"
        )
        # Split at the first occurrence of 'N E X T F L O W'
        _, _, after = stdout.partition("N E X T F L O W")

        result = "N E X T F L O W" + after

        # Print with original formatting preserved
        return result
    except Exception as e:
        logger.exception("""Error getting simulation log.""")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/data",
    response_class=FileResponse,
    operation_id="get-output-data",
    tags=["Simulations - vEcoli"],
    summary="Get simulation outputs",
)
async def get_results(
    background_tasks: BackgroundTasks,
    experiment_id: str = Query(..., description="Experiment id for the simulation."),
    # experiment: EcoliExperiment,
    variant_id: int = Query(default=0),
    lineage_seed_id: int = Query(default=0),
    generation_id: int = Query(default=1),
    agent_id: int = Query(default=0),
    filename: str | None = Query(default=None, description="Name you wish to assign to the downloaded zip file"),
) -> FileResponse:
    try:
        service = ParquetService()
        # experiment_id = get_experiment_id_from_tag(experiment_tag)
        pq_dir = service.get_parquet_dir(
            experiment_id=experiment_id,
            variant=variant_id,
            lineage_seed=lineage_seed_id,
            generation=generation_id,
            agent_id=agent_id,
        )
        buffer = get_zip_buffer(pq_dir)
        fname = filename or experiment_id
        filepath = write_zip_buffer(buffer, fname, background_tasks)

        # return FileResponse(path=filepath, media_type="application/octet-stream", filename=filepath.name)
        # return str(pq_dir)
        return FileResponse(path=filepath, media_type="application/octet-stream", filename=filepath.name)
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e
