import json
import logging
import mimetypes
import os
import tempfile
import uuid
import zipfile
from collections.abc import Generator, Mapping
from io import BytesIO
from pathlib import Path
from typing import Any, Union
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from sms_api.api.request_examples import DEFAULT_SIMULATION_CONFIG
from sms_api.common.gateway.io import get_zip_buffer, write_zip_buffer
from sms_api.common.gateway.models import RouterConfig, ServerMode
from sms_api.common.gateway.utils import get_simulator
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import get_settings
from sms_api.data.analysis_service import AnalysisService
from sms_api.data.parquet_service import ParquetService
from sms_api.dependencies import (
    get_database_service,
    get_simulation_service,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.handlers import launch_vecoli_simulation
from sms_api.simulation.models import (
    BaseModel,
    ConfigOverrides,
    EcoliExperimentDTO,
    EcoliExperimentRequestDTO,
    JobStatus,
    SimulationConfiguration,
    SimulationRun,
    SimulatorVersion,
    UploadedSimulationConfig,
)

ENV = get_settings()

logger = logging.getLogger(__name__)

config = RouterConfig(router=APIRouter(), prefix="/wcm", dependencies=[])


# -- service and data model -- #


class AnalysisJob(BaseModel):
    id: int
    status: str = "WAITING"


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


def get_analysis_dir(outdir: Path, experiment_id: str) -> Path:
    return outdir / experiment_id / "analyses"


def get_analysis_paths(analysis_dir: Path) -> set[Path]:
    paths = set()
    for root, _, files in analysis_dir.walk():
        for fname in files:
            fp = root / fname
            if fp.exists():
                paths.add(fp)
    return paths


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


# @config.router.post(
#     path="/simulation/run",
#     operation_id="run-simulation-workflow",
#     response_model=EcoliExperiment,
#     tags=["Simulations - vEcoli"],
#     dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
#     summary="Dispatches a nextflow-powered vEcoli simulation workflow",
# )
# async def run_simulation_workflow(
#     background_tasks: BackgroundTasks,
#     config_id: Optional[str] = None,
#     overrides: Optional[Overrides] = None,
#     variants: Optional[Variants] = None,
#     config: SimulationConfiguration | None = None,
#     # max_duration: float = Query(default=10800.0),
#     # time_step: float = Query(default=1.0),
# ) -> EcoliExperiment:
#     simulator: SimulatorVersion = get_simulator()
#     sim_request = EcoliWorkflowRequest(
#         config_id=config_id or "sms_single", overrides=overrides, variants=variants, simulator=simulator
#     )
#     sim_service = get_simulation_service()
#     if sim_service is None:
#         logger.error("Simulation service is not initialized")
#         raise HTTPException(status_code=500, detail="Simulation service is not initialized")
#     db_service = get_database_service()
#     if db_service is None:
#         logger.error("Database service is not initialized")
#         raise HTTPException(status_code=500, detail="Database service is not initialized")
#
#     try:
#         return await run_workflow(
#             simulation_request=sim_request,
#             simulation_service_slurm=sim_service,
#             # background_tasks=background_tasks,
#             # database_service=db_service,
#         )
#     except Exception as e:
#         logger.exception("Error running vEcoli simulation")
#         raise HTTPException(status_code=500, detail=str(e)) from e


# -- endpoints -- #


@config.router.post(
    path="/experiment",
    operation_id="launch-experiment",
    response_model=EcoliExperimentDTO,
    tags=["Simulations - vEcoli"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="Launches a nextflow-powered vEcoli simulation workflow",
)
async def launch_simulation(
    config_id: str = Query(
        default="sms", description="Configuration ID of an existing available vecoli simulation configuration JSON"
    ),
    overrides: ConfigOverrides | None = None,
    metadata: Mapping[str, str] | None = None,
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
    request = EcoliExperimentRequestDTO(config_id=config_id, overrides=overrides)

    try:
        return await launch_vecoli_simulation(
            request=request,
            simulator=simulator,
            metadata=metadata or {},
            simulation_service_slurm=sim_service,
            database_service=db_service,
        )
    except Exception as e:
        logger.exception("Error running vEcoli simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(path="/experiment", operation_id="get-experiment", tags=["Simulations - vEcoli"])
async def get_experiment(experiment_id: str) -> EcoliExperimentDTO:
    try:
        db_service = DBService()
        return await db_service.get_experiment(experiment_id=experiment_id)
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.delete(path="/experiment", operation_id="delete-experiment", tags=["Simulations - vEcoli"])
async def delete_experiment(experiment_id: str) -> str:
    try:
        db_service = DBService()
        # delete from db
        await db_service.delete_experiment(experiment_id=experiment_id)
        return f"Experiment {experiment_id} deleted successfully"
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(path="/experiment/versions", operation_id="list-experiments", tags=["Simulations - vEcoli"])
async def list_experiments() -> list[EcoliExperimentDTO]:
    try:
        db_service = DBService()
        return await db_service.list_experiments()
    except Exception as e:
        logger.exception("Error getting experiments")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/experiment/status",
    response_model=SimulationRun,
    operation_id="get-vecoli-simulation-status",
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


@config.router.post(
    path="/experiment/log",
    operation_id="get-vecoli-simulation-log",
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


@config.router.get(
    path="/experiment/analysis",
    response_model=None,
    operation_id="get-analysis-manifest",
    tags=["Data - vEcoli"],
    summary="Get all available analyses for a given simulation",
)
async def get_available_analyses(experiment_id: str = Query(...)) -> dict[str, list[str]]:
    try:
        service = AnalysisService()
        outdir = Path(ENV.simulation_outdir)
        # experiment_id = get_experiment_id_from_tag(experiment_tag)
        analysis_dir = service.get_analysis_dir(outdir, experiment_id)
        paths = service.get_analysis_paths(analysis_dir)
        manifest_template = service.get_manifest_template(paths)
        manifest = service.get_manifest(analysis_paths=paths, template=manifest_template)

        # class AnalysisOutput(BaseModel):
        #     id: str
        #     files: list[str]
        # class Analyses(BaseModel):
        #     value: list[AnalysisOutput]
        # analyses = Analyses(
        #     value=[
        #         AnalysisOutput(id=k, files=v)
        #         for k, v in manifest.items()
        #     ]
        # )
        # return analyses
        return manifest
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/experiment/analysis/download",
    response_model=None,
    # response_class=FileResponse,
    operation_id="download-analysis-output",
    tags=["Data - vEcoli"],
    summary="Download a file that was generated from a simulation analysis module",
)
async def download_analysis(
    experiment_id: str = Query(...),
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
            / experiment_id
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
    path="/analyses/download",
    response_class=StreamingResponse,
    operation_id="download-analyses",
    tags=["Data - vEcoli"],
    description="Download all available simulation analysis outputs as a .zip file",
)
async def download_analyses(
    # experiment: EcoliExperiment,
    experiment_id: str = Query(...),
) -> StreamingResponse:
    try:
        # outdir = Path("/Users/alexanderpatrie/sms/vEcoli/out")
        # experiment_id = "sms_multiseed"
        settings = get_settings()
        outdir = Path(settings.slurm_base_path) / "workspace" / "outputs"
        # experiment_id = get_experiment_id_from_tag(experiment_tag)
        analysis_dir = get_analysis_dir(outdir=outdir, experiment_id=experiment_id)

        file_paths = []
        for root, _, files in analysis_dir.walk():
            for f in files:
                fp = root / f
                abs_path = fp.absolute()
                arcname = os.path.relpath(str(abs_path), analysis_dir)
                file_paths.append((abs_path, arcname))

        return StreamingResponse(
            generate_zip(file_paths),
            media_type="application/x-zip-compressed",
            headers={"Content-Disposition": f"attachment; filename={experiment_id}.zip"},
        )
    except Exception as e:
        logger.exception("Error fetching the simulation analysis files.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/experiment/data",
    response_class=FileResponse,
    operation_id="get-data",
    tags=["Data - vEcoli"],
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


@config.router.post(
    path="/experiment/config", operation_id="upload-experiment-config", tags=["Configurations - vEcoli"]
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


@config.router.get(path="/experiment/config", operation_id="get-experiment-config", tags=["Configurations - vEcoli"])
async def get_simulation_config(config_id: str) -> SimulationConfiguration:
    try:
        db_service = DBService()
        return await db_service.get_simulation_config(config_id=config_id)
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.delete(
    path="/experiment/config", operation_id="delete-experiment-config", tags=["Configurations - vEcoli"]
)
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


@config.router.get(
    path="/experiment/config/versions", operation_id="list-simulation-configs", tags=["Configurations - vEcoli"]
)
async def list_simulation_configs() -> list[SimulationConfiguration]:
    try:
        db_service = DBService()
        return await db_service.list_simulation_configs()
    except Exception as e:
        logger.exception("Error getting configs")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post("/experiment/analysis/upload", tags=["myEcoli - vEcoli"])
async def upload_analysis_module(
    file: UploadFile = File(...),  # noqa: B008
    submodule_name: str = Query(..., description="Submodule name(single, multiseed, etc)"),
) -> dict[str, object]:
    try:
        # db_service = DBService()
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


@config.router.post(
    path="/experiment/analysis",
    operation_id="run-analysis",
    tags=["Data - vEcoli"],
    summary="Run an analysis",
)
async def run_analysis(config: dict[str, Any] | None = None) -> AnalysisJob:
    try:
        service = AnalysisService()
        config_id = "analysis_multigen"
        slurm_jobid: int = await service.submit_analysis_job(
            config_id=config_id, experiment_id=config_id, simulator_hash=get_simulator().git_commit_hash, env=ENV
        )
        return AnalysisJob(id=slurm_jobid, status="STARTED")

    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/analysis/status",
    operation_id="get-analysis-status",
    tags=["Data - vEcoli"],
    dependencies=[Depends(get_database_service)],
    summary="Get the analysis status record by its ID",
)
async def get_analysis_status(job: AnalysisJob) -> AnalysisJob:
    try:
        slurmjob_id = job.id
        # slurmjob_id = get_jobid_by_experiment(experiment_id)
        ssh_service = get_ssh_service()
        slurm_user = ENV.slurm_submit_user
        statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
        status: str = statuses[1].split("\n")[0].split()[-2]
        return AnalysisJob(id=slurmjob_id, status=status)
    except Exception as e:
        logger.exception(
            """Error getting analysis status.
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


def unzip_archive(zip_path: Path, dest_dir: Path) -> str:
    zip_path = Path(zip_path).resolve()
    dest_dir = Path(dest_dir).resolve()

    if not zip_path.is_file():
        raise FileNotFoundError(f"{zip_path} does not exist or is not a file")

    if not dest_dir.is_dir():
        raise NotADirectoryError(f"{dest_dir} does not exist or is not a directory")

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(dest_dir)

    return str(dest_dir)


@config.router.post(
    path="/analysis/archive",
    operation_id="get-analysis-archive",
    tags=["Data - vEcoli"],
    dependencies=[Depends(get_database_service)],
    summary="Get the analysis archive zip record by its ID",
)
async def get_analysis_archive(bg_tasks: BackgroundTasks) -> FileResponse:
    try:
        # slurmjob_id = get_jobid_by_experiment(experiment_id)
        ssh_service = get_ssh_service()
        tmp = tempfile.TemporaryDirectory()
        tmpdirname = tmp.name
        fname = "analysis_multigen.zip"
        local = Path(tmpdirname) / fname
        remote = Path(ENV.slurm_base_path) / "workspace" / "api_outputs" / fname
        await ssh_service.scp_download(local_file=local, remote_path=remote)
        bg_tasks.add_task(tmp.cleanup)

        # now, do this:
        # 1. unzip archive found at ``local``
        # 2. recurse ``local`` and return flattened list of available htmls
        # 3. handle non-htmls (db?)
        # 4. return htmls
        return FileResponse(path=local, media_type="application/octet-stream", filename=local.name)
    except Exception as e:
        logger.exception(
            """Error getting analysis status.
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(path="/analysis", operation_id="show-analysis", tags=["Data - vEcoli"])
async def get_analysis(experiment_id: str = Query(default="analysis_multigen")) -> list[str]:
    outdir = Path(ENV.slurm_base_path) / "workspace" / "api_outputs"
    return get_analysis_html_outputs(outdir_root=outdir, expid=experiment_id)


def get_html_output_paths(outdir_root: Path, experiment_id: str) -> list[Path]:
    outdir = outdir_root / experiment_id
    filepaths = []
    for root, _, files in outdir.walk():
        for f in files:
            fp = root / f
            if fp.exists() and fp.is_file():
                filepaths.append(fp)
    return list(filter(lambda _file: _file.name.endswith(".html"), filepaths))


def read_html_file(file_path: Path) -> str:
    """Read an HTML file and return its contents as a single string."""
    with open(str(file_path), encoding="utf-8") as f:
        return f.read()


def get_analysis_html_outputs(outdir_root: Path, expid: str = "analysis_multigen") -> list[str]:
    filepaths = get_html_output_paths(outdir_root, expid)
    return [read_html_file(path) for path in filepaths]


@config.router.get(
    path="/analysis/download",
    response_model=None,
    # response_class=FileResponse,
    operation_id="download-analysis-output-data",
    tags=["Data - vEcoli"],
    summary="Download a file that was generated from a simulation analysis module",
)
async def download_analysis_file(
    experiment_id: str = Query(...),
    variant_id: int = Query(default=0),
    lineage_seed_id: int = Query(default=0),
    generation_id: int = Query(default=1),
    agent_id: int = Query(default=0),
    filename: str = Query(examples=["mass_fraction_summary.html"]),
) -> Union[FileResponse, HTMLResponse]:
    try:
        env = get_settings()
        # experiment_id = get_experiment_id_from_tag(experiment_tag)
        # filepath = service.get_file_path(experiment_id, filename, remote=True, logger_instance=logger)

        outdir = env.local_simulation_outdir if int(env.dev_mode) else env.simulation_outdir
        filepath = (
            Path(outdir)
            / experiment_id
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