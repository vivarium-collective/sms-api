"""
/analyses: this router is dedicated to the running and output retrieval of
    simulation analysis jobs/workflows
"""

import datetime
import json
import logging
import mimetypes
import tempfile
import uuid
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from typing import Union
from zipfile import ZIP_DEFLATED, ZipFile

import fastapi
from fastapi import BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from sms_api.api.request_examples import examples
from sms_api.common.gateway.io import get_zip_buffer, write_zip_buffer
from sms_api.common.gateway.models import ServerMode
from sms_api.common.gateway.utils import get_simulator, router_config
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import get_settings
from sms_api.data.models import ExperimentAnalysisDTO, ExperimentAnalysisRequest
from sms_api.data.services import analysis
from sms_api.data.services.parquet import ParquetService
from sms_api.dependencies import get_database_service, get_simulation_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    EcoliSimulationDTO,
    ExperimentMetadata,
    ExperimentRequest,
    JobStatus,
    SimulationConfig,
    SimulationConfiguration,
    SimulationRun,
    SimulatorVersion,
)

ENV = get_settings()

logger = logging.getLogger(__name__)
config = router_config(prefix="ecoli")


###### -- utils -- ######


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


def generate_zip(file_paths: list[tuple[Path, str]]) -> Generator[bytes, None, None]:
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


async def read_config_file(config_file: UploadFile) -> SimulationConfiguration:
    file_contents = await config_file.read()
    config = SimulationConfiguration(**json.loads(file_contents))
    for attrname in list(SimulationConfiguration.model_fields.keys()):
        attr = getattr(config, attrname)
        if attr is None:
            delattr(config, attrname)
        if isinstance(attr, (list, dict)) and not len(attr):
            delattr(config, attrname)
    return config


def unique_id(scope: str) -> str:
    return f"{scope}-{uuid.uuid4().hex}"


def timestamp() -> str:
    return str(datetime.datetime.now())


###### -- analyses -- ######


@config.router.post(
    path="/analyses",
    response_model=ExperimentAnalysisDTO,
    operation_id="run-experiment-analysis",
    tags=["Analyses"],
    summary="Run an analysis workflow (like multigeneration)",
    dependencies=[Depends(get_database_service)],
)
async def run_analysis(request: ExperimentAnalysisRequest = examples["core_analysis_request"]) -> ExperimentAnalysisDTO:  # type: ignore[assignment]
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        config = request.to_config()
        slurmjob_name, slurmjob_id = await analysis.dispatch(
            config=config,
            analysis_name=request.analysis_name,
            simulator_hash=get_simulator().git_commit_hash,
            env=ENV,
            logger=logger,
        )
        analysis_record = await db_service.insert_analysis(
            name=request.analysis_name,
            config=config,
            last_updated=timestamp(),
            job_name=slurmjob_name,
            job_id=slurmjob_id,
        )
        return analysis_record
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}",
    operation_id="fetch-experiment-analysis",
    tags=["Analyses"],
    dependencies=[Depends(get_database_service)],
    summary="Retrieve an existing experiment analysis spec detail from the database",
)
async def get_analysis_spec(id: int) -> ExperimentAnalysisDTO:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        return await db_service.get_analysis(database_id=id)
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/status",
    tags=["Analyses"],
    operation_id="get-analysis-status",
    dependencies=[Depends(get_database_service)],
    summary="Get the status of an existing experiment analysis run",
)
async def get_analysis_status(id: int = fastapi.Path(..., description="Database ID of the analysis")) -> SimulationRun:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        analysis_record = await db_service.get_analysis(database_id=id)
        slurmjob_id = analysis_record.job_id
        # slurmjob_id = get_jobid_by_experiment(experiment_id)
        ssh_service = get_ssh_service()
        slurm_user = ENV.slurm_submit_user
        statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
        status: str = statuses[1].split("\n")[0].split()[-2]
        return SimulationRun(id=id, status=JobStatus[status])
    except Exception as e:
        logger.exception(
            """Error getting simulation status.\
                Are you sure that you've passed the experiment_tag? (not the experiment id)
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/log",
    tags=["Analyses"],
    operation_id="get-analysis-log",
    dependencies=[Depends(get_database_service)],
    summary="Get the log of an existing experiment analysis run",
)
async def get_analysis_log(id: int = fastapi.Path(..., description="Database ID of the analysis")) -> str:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        analysis_record = await db_service.get_analysis(database_id=id)
        slurm_logfile = Path(ENV.slurm_log_base_path) / f"{analysis_record.job_name}.out"
        ssh_service = get_ssh_service()
        slurm_user = ENV.slurm_submit_user
        ret, stdout, stdin = await ssh_service.run_command(f"cat {slurm_logfile!s}")
        return stdout
    except Exception as e:
        logger.exception(
            """Error getting simulation status.\
                Are you sure that you've passed the experiment_tag? (not the experiment id)
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/plots",
    tags=["Analyses"],
    operation_id="get-analysis-plots",
    dependencies=[Depends(get_database_service)],
    summary="Get an array of HTML files representing all plot outputs of a given analysis.",
)
async def get_analysis_plots(id: int = fastapi.Path(..., description="Database ID of the analysis")) -> list[str]:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    outdir = Path(ENV.simulation_outdir)
    if int(ENV.dev_mode):
        ssh = get_ssh_service(ENV)
        # f"cd /home/FCAM/svc_vivarium/workspace && /home/FCAM/svc_vivarium/.local/bin/uv run scripts/html_outputs.py --output_id {output_id}"  # noqa: E501
        remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
        ret, stdin, stdout = await ssh.run_command(
            dedent(f"""
            cd /home/FCAM/svc_vivarium/workspace \
                && {remote_uv_executable} run scripts/html_outputs.py --output_id {output_id}
        """)
        )
        return [stdin]
    return analysis.get_analysis_html_outputs(outdir_root=outdir, expid=output_id)


@config.router.put(
    "/analyses",
    tags=["Analyses"],
    summary="Upload custom python vEcoli analysis module according to the vEcoli analysis API",
    operation_id="upload-analysis-module",
)
async def upload_analysis_module(
    file: UploadFile = File(...),  # noqa: B008
    submodule_name: str = Query(..., description="Submodule name(single, multiseed, etc)"),
) -> dict[str, object]:
    try:
        contents = await file.read()
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmp_path: Path = Path(tmpdirname) / (file.filename or str(file))

            # Write the file contents to the temp file
            with open(tmp_path, "wb") as tmpfile:
                tmpfile.write(contents)

            result = {"tmp_path": str(tmp_path), "size": len(contents)}

            local = tmp_path
            remote = Path(ENV.vecoli_config_dir).parent / "ecoli" / "analysis" / submodule_name / file.filename  # type: ignore[operator]
            ssh = get_ssh_service(ENV)
            await ssh.scp_upload(local_file=local, remote_path=remote)
            return result
    except Exception as e:
        logger.exception("Error uploading analysis module")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/download",
    response_model=None,
    operation_id="download-analysis-output-file",
    tags=["Analyses"],
    summary="Download a single file that was generated from a simulation analysis module",
)
async def download_analysis(
    id: str = fastapi.Path(...),
    variant_id: int = Query(default=0),
    lineage_seed_id: int = Query(default=0),
    generation_id: int = Query(default=1),
    agent_id: int = Query(default=0),
    filename: str = Query(examples=["mass_fraction_summary.html"]),
) -> Union[FileResponse, HTMLResponse]:
    try:
        # experiment_id = get_experiment_id_from_tag(experiment_tag)
        # filepath = service.get_file_path(experiment_id, filename, remote=True, logger_instance=logger)
        filepath = (
            Path(ENV.simulation_outdir)
            / id
            / "analyses"
            / f"variant={variant_id}"
            / f"lineage_seed={lineage_seed_id}"
            / f"generation={generation_id}"
            / f"agent_id={agent_id}"
            / "plots"
            / filename
        )
        mimetype, _ = mimetypes.guess_type(filepath)

        if str(filepath).endswith(".html"):
            return HTMLResponse(content=filepath.read_text(encoding="utf-8"))
        return FileResponse(path=filepath, media_type=mimetype or "application/octet-stream", filename=filepath.name)
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses",
    operation_id="list-analyses",
    tags=["Analyses"],
    summary="List all analysis specs uploaded to the database",
    dependencies=[Depends(get_database_service)],
)
async def list_analyses() -> list[ExperimentAnalysisDTO]:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await db_service.list_analyses()
    except Exception as e:
        logger.exception("Error fetching the uploaded analyses")
        raise HTTPException(status_code=500, detail=str(e)) from e


###### -- simulations -- ######


@config.router.post(
    path="/simulations",
    operation_id="run-ecoli-simulation",
    response_model=EcoliSimulationDTO,
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="Launches a nextflow-powered vEcoli simulation workflow",
)
async def run_simulation(
    request: ExperimentRequest, config: SimulationConfig, metadata: ExperimentMetadata | None = None
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

    config = request.to_config()
    if config.experiment_id is None:
        raise HTTPException(status_code=400, detail="Experiment ID is required")

    try:
        simulator: SimulatorVersion = get_simulator()
        last_update = timestamp()
        slurmjob_name, slurmjob_id = await sim_service.submit_experiment_job(
            config=config,
            simulation_name=request.simulation_name,
            simulator_hash=simulator.git_commit_hash,
            env=ENV,
            logger=logger,
        )
        simulation_record = await db_service.insert_ecoli_simulation(
            name=request.simulation_name,
            config=config,
            last_updated=timestamp(),
            job_name=slurmjob_name,
            job_id=slurmjob_id,
            metadata=request.metadata,
        )
        return simulation_record
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulations/{id}",
    operation_id="get-ecoli-simulation",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service)],
)
async def get_simulation(id: int = fastapi.Path(description="Database ID of the simulation")) -> EcoliSimulationDTO:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await db_service.get_ecoli_simulation(database_id=id)
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulations/{id}/status",
    response_model=SimulationRun,
    operation_id="get-ecoli-simulation-status",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service)],
    summary="Get the simulation status record by its ID",
)
async def get_simulation_status(id: int = fastapi.Path(...)) -> SimulationRun:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        sim_record = await db_service.get_ecoli_simulation(database_id=id)
        slurmjob_id = sim_record.job_id
        # slurmjob_id = get_jobid_by_experiment(experiment_id)
        ssh_service = get_ssh_service()
        slurm_user = ENV.slurm_submit_user
        statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
        status: str = statuses[1].split("\n")[0].split()[-2]
        return SimulationRun(id=int(id), status=JobStatus[status])
    except Exception as e:
        logger.exception(
            """Error getting simulation status.\
                Are you sure that you've passed the experiment_tag? (not the experiment id)
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulations/{id}/log/detailed",
    tags=["Simulations"],
    operation_id="get-ecoli-simulation-log-detail",
    dependencies=[Depends(get_database_service)],
    summary="Get the simulation status record by its ID",
)
async def get_simlog(id: int = fastapi.Path(...)) -> str:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        experiment = await db_service.get_ecoli_simulation(database_id=id)
        ssh_service = get_ssh_service()
        slurm_user = ENV.slurm_submit_user
        ret, stdout, stderr = await ssh_service.run_command(
            f"cd /home/FCAM/svc_vivarium/workspace && make slurmlog id={experiment.config.experiment_id}"
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
    path="/simulations/{id}/log",
    operation_id="get-ecoli-simulation-log",
    tags=["Simulations"],
    summary="Get the simulation log record of a given experiment",
)
async def get_simulation_log(id: str = fastapi.Path(...)) -> str:
    try:
        ssh_service = get_ssh_service()
        returncode, stdout, stderr = await ssh_service.run_command(f"cat {ENV.slurm_base_path!s}/prod/htclogs/{id}.out")
        # Split at the first occurrence of 'N E X T F L O W'
        _, _, after = stdout.partition("N E X T F L O W")

        result = "N E X T F L O W" + after

        # Print with original formatting preserved
        return result
    except Exception as e:
        logger.exception("""Error getting simulation log.""")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulations/{id}/metadata",
    operation_id="get-ecoli-simulation-metadata",
    tags=["Simulations"],
    summary="Get simulation metadata",
)
async def get_metadata(id: int = fastapi.Path(description="Database ID")) -> ExperimentMetadata:
    return ExperimentMetadata(root={})


@config.router.post(
    path="/simulations/{id}/state",
    response_class=FileResponse,
    operation_id="get-ecoli-simulation-outdata",
    tags=["Simulations"],
    summary="Get simulation outputs",
)
async def get_results(
    background_tasks: BackgroundTasks,
    id: int = fastapi.Path(..., description="Experiment id for the simulation."),
    # experiment: EcoliExperiment,
    variant_id: int = Query(default=0),
    lineage_seed_id: int = Query(default=0),
    generation_id: int = Query(default=1),
    agent_id: int = Query(default=0),
    filename: str | None = Query(default=None, description="Name you wish to assign to the downloaded zip file"),
) -> FileResponse:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        experiment = await db_service.get_ecoli_simulation(database_id=id)
        service = ParquetService()
        # experiment_id = get_experiment_id_from_tag(experiment_tag)
        pq_dir = service.get_parquet_dir(
            experiment_id=experiment.config.experiment_id,
            variant=variant_id,
            lineage_seed=lineage_seed_id,
            generation=generation_id,
            agent_id=agent_id,
        )
        buffer = get_zip_buffer(pq_dir)
        fname = filename or experiment.config.experiment_id
        filepath = write_zip_buffer(buffer, fname, background_tasks)

        return FileResponse(path=filepath, media_type="application/octet-stream", filename=filepath.name)
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e
