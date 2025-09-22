"""
/analyses: this router is dedicated to the running and output retrieval of
    simulation analysis jobs/workflows
"""
import datetime
import logging
import mimetypes
import tempfile
import uuid
from pathlib import Path
from typing import Union

import fastapi
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from sms_api.common.gateway.models import RouterConfig
from sms_api.common.gateway.utils import get_simulator
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.config import get_settings
from sms_api.data import analysis_service
from sms_api.data.models import AnalysisConfig, AnalysisJob, AnalysisRequest
from sms_api.dependencies import get_database_service

ENV = get_settings()

logger = logging.getLogger(__name__)
config = RouterConfig(router=APIRouter(), prefix="/analyses", dependencies=[])


@config.router.post(
    path="",
    operation_id="run-experiment-analysis",
    tags=["Analysis - vEcoli"],
    summary="Run an analysis workflow (like multigeneration)",
)
async def run_analysis(request: AnalysisRequest):
    try:
        db_service = get_database_service()
        config = AnalysisConfig.from_request(request)
        analysis_name = request.analysis_name
        last_updated = str(datetime.datetime.now())
        analysis = await db_service.insert_analysis(name=analysis_name, config=config, last_updated=last_updated)
        # TODO: now pass analysis object to analysis service and use it to create the analysis.config.outdir
        #   in remote FS, and upload
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/fetch/{id}",
    operation_id="fetch-experiment-analysis",
    tags=["Analysis - vEcoli"]
)
async def fetch_analysis(id: int):
    try:
        db_service = get_database_service()
        return await db_service.get_analysis(database_id=id)
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e

# @config.router.post(
#     path="",
#     operation_id="run-experiment-analysis",
#     tags=["Analysis - vEcoli"],
#     summary="Run an analysis workflow (like multigeneration)",
# )
# async def run_analysis(config: AnalysisConfig) -> AnalysisJob:
#     try:
#         config_id = "analysis_multigen"
#         experiment_id = f"sms_{config_id}_{uuid.uuid4()!s}"
#         slurm_jobid: int = await analysis_service.dispatch_job(
#             experiment_id=experiment_id,
#             config=config,
#             simulator_hash=get_simulator().git_commit_hash,
#             env=ENV,
#             logger=logger,
#         )
#         return AnalysisJob(id=slurm_jobid, status="STARTED")
#
#     except Exception as e:
#         logger.exception("Error fetching the simulation analysis file.")
#         raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="",
    operation_id="get-available-analyses",
    tags=["Analysis - vEcoli"],
    summary="Get all available analysis output ids",
)
async def list_analyses() -> list[str]:  # type: ignore[empty-body]
    pass


@config.router.put("", tags=["Analysis - vEcoli"], summary="Upload custom analysis module")
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


@config.router.get(
    path="/{id}", tags=["Analysis - vEcoli"], summary="Get an array of HTML files as strings and job status6"
)
async def get_analysis(id: str) -> list[str]:
    # id = "analysis_multigen"
    outdir = Path(ENV.slurm_base_path) / "workspace" / "api_outputs"
    if int(ENV.dev_mode):
        outdir = Path("/Users/alexanderpatrie/sms/sms-api/home/FCAM/svc_vivarium/workspace/api_outputs")
    return analysis_service.get_analysis_html_outputs(outdir_root=outdir, expid=id)


@config.router.get(
    path="/{id}/download",
    response_model=None,
    operation_id="download-analysis-output-file",
    tags=["Analysis - vEcoli"],
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


# @config.router.get(
#     path="/manifest",
#     response_model=None,
#     operation_id="get-analysis-manifest",
#     tags=["Analysis - vEcoli"],
#     summary="Get all available analyses for a given simulation",
# )
# async def get_available_analyses(experiment_id: str = Query(...)) -> dict[str, list[str]]:
#     try:
#         service = AnalysisService()
#         outdir = Path(ENV.simulation_outdir)
#         # experiment_id = get_experiment_id_from_tag(experiment_tag)
#         analysis_dir = service.get_analysis_dir(outdir, experiment_id)
#         paths = service.get_analysis_paths(analysis_dir)
#         manifest_template = service.get_manifest_template(paths)
#         manifest = service.get_manifest(analysis_paths=paths, template=manifest_template)
#
#         # class AnalysisOutput(BaseModel):
#         #     id: str
#         #     files: list[str]
#         # class Analyses(BaseModel):
#         #     value: list[AnalysisOutput]
#         # analyses = Analyses(
#         #     value=[
#         #         AnalysisOutput(id=k, files=v)
#         #         for k, v in manifest.items()
#         #     ]
#         # )
#         # return analyses
#         return manifest
#     except Exception as e:
#         logger.exception("Error fetching the simulation analysis file.")
#         raise HTTPException(status_code=500, detail=str(e)) from e
#
#
#
#
#
#
#
#
# @config.router.post(
#     path="/status",
#     operation_id="get-analysis-status",
#     tags=["Analysis - vEcoli"],
#     dependencies=[Depends(get_database_service)],
#     summary="Get the analysis status record by its ID",
# )
# async def get_analysis_status(job: AnalysisJob) -> AnalysisJob:
#     try:
#         slurmjob_id = job.id
#         # slurmjob_id = get_jobid_by_experiment(experiment_id)
#         ssh_service = get_ssh_service()
#         slurm_user = ENV.slurm_submit_user
#         statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
#         status: str = statuses[1].split("\n")[0].split()[-2]
#         return AnalysisJob(id=slurmjob_id, status=status)
#     except Exception as e:
#         logger.exception(
#             """Error getting analysis status.
#             """
#         )
#         raise HTTPException(status_code=500, detail=str(e)) from e
#
#
# @config.router.post(
#     path="/archive",
#     operation_id="get-analysis-archive",
#     tags=["Analysis - vEcoli"],
#     dependencies=[Depends(get_database_service)],
#     summary="Get the analysis archive zip record by its ID",
# )
# async def get_analysis_archive(bg_tasks: BackgroundTasks) -> FileResponse:
#     try:
#         # slurmjob_id = get_jobid_by_experiment(experiment_id)
#         ssh_service = get_ssh_service()
#         tmp = tempfile.TemporaryDirectory()
#         tmpdirname = tmp.name
#         fname = "analysis_multigen.zip"
#         local = Path(tmpdirname) / fname
#         remote = Path(ENV.slurm_base_path) / "workspace" / "api_outputs" / fname
#         await ssh_service.scp_download(local_file=local, remote_path=remote)
#         bg_tasks.add_task(tmp.cleanup)
#
#
#         # now, do this:
#         # 1. unzip archive found at ``local``
#         # 2. recurse ``local`` and return flattened list of available htmls
#         # 3. handle non-htmls (db?)
#         # 4. return htmls
#         return FileResponse(path=local, media_type="application/octet-stream", filename=local.name)
#     except Exception as e:
#         logger.exception(
#             """Error getting analysis status.
#             """
#         )
#         raise HTTPException(status_code=500, detail=str(e)) from e
#
#
# @config.router.post(path="/get", operation_id="show-analysis", tags=["Analysis - vEcoli"])
# async def get_analysis(experiment_id: str = Query(default="analysis_multigen")) -> list[str]:
#     outdir = Path(ENV.slurm_base_path) / "workspace" / "api_outputs"
#     return get_analysis_html_outputs(outdir_root=outdir, expid=experiment_id)
#
