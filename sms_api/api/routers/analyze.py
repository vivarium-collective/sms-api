import logging
import mimetypes
import tempfile
import zipfile
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from typing import Any, Union
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from sms_api.common.gateway.models import RouterConfig, ServerMode
from sms_api.common.gateway.utils import get_simulator
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import get_settings
from sms_api.data.analysis_service import AnalysisService
from sms_api.dependencies import (
    get_database_service,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    BaseModel,
)

ENV = get_settings()

logger = logging.getLogger(__name__)
config = RouterConfig(router=APIRouter(), prefix="/analyze", dependencies=[])


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


def generate_zip_buffer(file_paths: list[tuple[Path, str]]) -> Generator[Any]:
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


# -- router endpoints -- #


@config.router.get(
    path="/manifest",
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
    path="/download",
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


@config.router.post("/upload", tags=["Configurations - vEcoli"])
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
    path="/run",
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
    path="/status",
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


@config.router.post(
    path="/archive",
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


@config.router.post(path="/get", operation_id="show-analysis", tags=["Data - vEcoli"])
async def get_analysis(experiment_id: str = Query(default="analysis_multigen")) -> list[str]:
    outdir = Path(ENV.slurm_base_path) / "workspace" / "api_outputs"
    return get_analysis_html_outputs(outdir_root=outdir, expid=experiment_id)
