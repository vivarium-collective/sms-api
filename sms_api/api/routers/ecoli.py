"""
/analyses: this router is dedicated to the running and output retrieval of
    simulation analysis jobs/workflows
"""

# TODO: do we require simulation/analysis configs that are supersets of the original configs:
#   IE: where do we provide this special config: in vEcoli or API?
# TODO: what does a "configuration endpoint" actually mean (can we configure via the simulation?)
# TODO: labkey preprocessing

import logging
import mimetypes
import tempfile
import zipfile
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from typing import Any

import fastapi
import orjson
import polars as pl
from fastapi import BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from sms_api.api import request_examples
from sms_api.common.gateway.io import get_zip_buffer, write_zip_buffer
from sms_api.common.gateway.utils import get_simulator, router_config
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.common.utils import timestamp
from sms_api.config import get_settings
from sms_api.data.models import (
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    OutputFile,
    TsvOutputFile,
    TsvOutputFileRequest,
)
from sms_api.data.services import analysis
from sms_api.data.services.analysis import (
    format_html_string,
    format_tsv_string,
    get_html_outputs_local,
    get_html_outputs_remote,
    get_tsv_manifest_local,
    get_tsv_manifest_remote,
    get_tsv_outputs_local,
    get_tsv_outputs_remote,
    read_tsv_file,
)
from sms_api.data.services.parquet import ParquetService
from sms_api.dependencies import get_database_service, get_simulation_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    EcoliSimulationDTO,
    ExperimentMetadata,
    ExperimentRequest,
    JobStatus,
    SimulationRun,
    SimulatorVersion,
)

ENV = get_settings()

logger = logging.getLogger(__name__)
config = router_config(prefix="ecoli")


###### -- utils -- ######


async def get_slurm_log(db_service: DatabaseService, ssh_service: SSHService, db_id: int) -> str:
    experiment = await db_service.get_ecoli_simulation(database_id=db_id)
    remote_log_path = f"{ENV.slurm_log_base_path!s}/{experiment.job_name}"
    returncode, stdout, stderr = await ssh_service.run_command(f"cat {remote_log_path}.out")
    return stdout


###### -- analyses -- ######


@config.router.post(
    path="/analyses",
    response_model=ExperimentAnalysisDTO,
    operation_id="run-experiment-analysis",
    tags=["Analyses"],
    summary="Run an analysis workflow (like multigeneration)",
    dependencies=[Depends(get_database_service)],
)
async def run_analysis(request: ExperimentAnalysisRequest = request_examples.ptools_analysis) -> ExperimentAnalysisDTO:
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
    path="/analyses/{id}/manifest",
    tags=["Analyses"],
    operation_id="get-analysis-manifest",
    dependencies=[Depends(get_database_service)],
    summary="Get an array of tsv files formatted for ptools.",
)
async def get_ptools_manifest(
    id: int = fastapi.Path(..., description="Database ID of the analysis"),
) -> list[TsvOutputFile]:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        analysis_data = await db_service.get_analysis(database_id=id)
        output_id = analysis_data.name
        if int(ENV.dev_mode):
            return await get_tsv_manifest_local(output_id=output_id, ssh_service=get_ssh_service(ENV))
        else:
            return get_tsv_manifest_remote(output_id)
    except Exception as e:
        logger.exception("Error getting analysis data")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/analyses/{id}/tsv",
    response_model=None,
    operation_id="fetch-analysis-output-file",
    tags=["Analyses"],
    dependencies=[Depends(get_database_service)],
    summary="Download a single file that was generated from a simulation analysis module",
)
async def fetch_analysis_output_file(request: TsvOutputFileRequest, id: int = fastapi.Path(...)) -> TsvOutputFile:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        variant_id = request.variant
        lineage_seed_id = request.lineage_seed
        generation_id = request.generation
        agent_id = request.agent_id
        filename = request.filename
        analysis_data = await db_service.get_analysis(database_id=id)
        output_id = analysis_data.name
        fp = (
            Path(ENV.simulation_outdir)
            / output_id
            / f"experiment_id={analysis_data.config.analysis_options.experiment_id[0]}"
        )
        if variant_id is not None:
            fp = fp / f"variant={variant_id}"
        if lineage_seed_id is not None:
            fp = fp / f"lineage_seed={lineage_seed_id}"
        if generation_id is not None:
            fp = fp / f"generation={generation_id}"
        if agent_id is not None:
            fp = fp / f"agent_id={agent_id}"

        filepath = fp / filename
        mimetype, _ = mimetypes.guess_type(filepath)

        if int(ENV.dev_mode):
            ssh = get_ssh_service(ENV)
            _, stdout, stderr = await ssh.run_command(f"cat {filepath!s}")
            return TsvOutputFile(
                filename=filename,
                variant=variant_id,
                lineage_seed=lineage_seed_id,
                generation=generation_id,
                agent_id=agent_id,
                content=stdout,
            )

        return TsvOutputFile(
            filename=filename,
            variant=variant_id,
            lineage_seed=lineage_seed_id,
            generation=generation_id,
            agent_id=agent_id,
            content=read_tsv_file(filepath),
        )
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
async def get_analysis_plots(
    id: int = fastapi.Path(..., description="Database ID of the analysis"),
) -> list[OutputFile]:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        analysis_data = await db_service.get_analysis(database_id=id)
        output_id = analysis_data.name
        if int(ENV.dev_mode):
            return await get_html_outputs_local(output_id=output_id, ssh_service=get_ssh_service(ENV))
        else:
            return get_html_outputs_remote(output_id=output_id)
    except Exception as e:
        logger.exception("Error getting analysis data")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/plots/formatted",
    tags=["Analyses"],
    operation_id="get-analysis-plots-formatted",
    dependencies=[Depends(get_database_service)],
    summary="Get a stream of multiple html file contents representing plots.",
)
async def get_analysis_plots_formatted(
    id: int = fastapi.Path(..., description="Database ID of the analysis"),
) -> fastapi.responses.StreamingResponse:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        data = None
        analysis_data = await db_service.get_analysis(database_id=id)
        output_id = analysis_data.name
        if int(ENV.dev_mode):
            data = await get_html_outputs_local(output_id=output_id, ssh_service=get_ssh_service())
        else:
            # data = FileServiceTsv().get_outputs(output_id=output_id)
            data = get_html_outputs_remote(output_id=output_id)

        boundary = "myboundary"

        def generate() -> Generator[str, None, None]:
            for idx, item in enumerate(data, 1):
                filename = f"{item.name if hasattr(item, 'name') else f'item{idx}'}.tsv"
                yield f"--{boundary}\r\n"
                yield "Content-Type: text/plain\r\n"
                yield f'Content-Disposition: attachment; filename="{filename}"\r\n\r\n'
                yield format_html_string(item) + "\r\n"

            yield f"--{boundary}--\r\n"

        return fastapi.responses.StreamingResponse(generate(), media_type=f"multipart/mixed; boundary={boundary}")
    except Exception as e:
        logger.exception("Error uploading analysis module")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/ptools",
    tags=["Analyses"],
    operation_id="get-analysis-tsv",
    dependencies=[Depends(get_database_service)],
    summary="Get an array of tsv files formatted for ptools.",
)
async def get_ptools_tsv(id: int = fastapi.Path(..., description="Database ID of the analysis")) -> list[OutputFile]:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        analysis_data = await db_service.get_analysis(database_id=id)
        output_id = analysis_data.name
        if int(ENV.dev_mode):
            return await get_tsv_outputs_local(output_id=output_id, ssh_service=get_ssh_service(ENV))
        else:
            return get_tsv_outputs_remote(output_id=output_id)
    except Exception as e:
        logger.exception("Error getting analysis data")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/ptools/formatted",
    tags=["Analyses"],
    operation_id="get-analysis-tsv-formatted",
    dependencies=[Depends(get_database_service)],
    summary="Get a stream of multiple tsv file contents formatted for ptools.",
)
async def get_ptools_tsv_formatted(
    id: int = fastapi.Path(..., description="Database ID of the analysis"),
) -> fastapi.responses.StreamingResponse:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        data = None
        analysis_data = await db_service.get_analysis(database_id=id)
        output_id = analysis_data.name
        if int(ENV.dev_mode):
            data = await get_tsv_outputs_local(output_id=output_id, ssh_service=get_ssh_service())
        else:
            # data = FileServiceTsv().get_outputs(output_id=output_id)
            data = get_tsv_outputs_remote(output_id=output_id)

        boundary = "myboundary"

        def generate() -> Generator[str, None, None]:
            for idx, item in enumerate(data, 1):
                filename = f"{item.name if hasattr(item, 'name') else f'item{idx}'}.tsv"
                yield f"--{boundary}\r\n"
                yield "Content-Type: text/plain\r\n"
                yield f'Content-Disposition: attachment; filename="{filename}"\r\n\r\n'
                yield format_tsv_string(item) + "\r\n"

            yield f"--{boundary}--\r\n"

        return fastapi.responses.StreamingResponse(generate(), media_type=f"multipart/mixed; boundary={boundary}")
    except Exception as e:
        logger.exception("Error getting analysis data")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/ptools/download",
    tags=["Analyses"],
    operation_id="download-tsv-zip",
    dependencies=[Depends(get_database_service)],
    summary="Download zip file of TSV outputs formatted for ptools.",
)
async def download_ptools_zip(
    id: int = fastapi.Path(..., description="Database ID of the analysis"),
) -> fastapi.responses.StreamingResponse:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        data = None
        analysis_data = await db_service.get_analysis(database_id=id)
        output_id = analysis_data.name
        if int(ENV.dev_mode):
            data = await get_tsv_outputs_local(output_id=output_id, ssh_service=get_ssh_service())
        else:
            # data = FileServiceTsv().get_outputs(output_id=output_id)
            data = get_tsv_outputs_remote(output_id=output_id)

        def write_file(outdir: Path, output_file: OutputFile) -> Path:
            lines = "".join(output_file.content).split("\n")
            outfile = outdir / output_file.name
            with open(outfile, "w") as f:
                for item in lines:
                    f.write(f"{item}\n")
            return outfile

        with tempfile.TemporaryDirectory() as tmpdir:
            dirpath = Path(tmpdir)
            files = []
            for output in data:
                f = write_file(dirpath, output)
                if f.exists():
                    files.append(f)
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in files:
                    # Add file to ZIP; arcname makes sure only the file name is used
                    zip_file.write(file_path, arcname=file_path.name)
            zip_buffer.seek(0)

            return fastapi.responses.StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{output_id}.zip"'},
            )
    except Exception as e:
        logger.exception("Error uploading analysis module")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
    request: ExperimentRequest = request_examples.base_simulation,
    metadata: ExperimentMetadata | None = None,
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
        ssh_service = get_ssh_service()
        return await get_slurm_log(db_service, ssh_service, id)
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
async def get_simulation_log(id: int = fastapi.Path(...)) -> fastapi.Response:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    ssh_service = get_ssh_service()
    try:
        stdout = await get_slurm_log(db_service, ssh_service, id)
        _, _, after = stdout.partition("N E X T F L O W")
        result = "N E X T F L O W" + after
        return fastapi.Response(content=result, media_type="text/plain")
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


@config.router.get(
    path="/simulations",
    operation_id="list-ecoli-simulations",
    tags=["Simulations"],
    summary="List all simulation specs uploaded to the database",
    dependencies=[Depends(get_database_service)],
)
async def list_simulations() -> list[EcoliSimulationDTO]:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await db_service.list_ecoli_simulations()
    except Exception as e:
        logger.exception("Error fetching the uploaded analyses")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulations/data",
    operation_id="get-ecoli-simulation-data",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service)],
    summary="Get/Stream simulation data",
)
async def get_simulation_data(
    bg_tasks: BackgroundTasks,
    experiment_id: str = Query(default="sms_multigeneration"),
    lineage_seed: int = Query(default=6),
    generation: int = Query(default=1),
    variant: int = Query(default=0),
    agent_id: int = Query(default=0),
    observables: list[str] = request_examples.base_observables,
) -> fastapi.responses.StreamingResponse:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        ssh = get_ssh_service(ENV)

        # first, slice parquet and write temp pq to remote disk
        remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
        ret, stdout, stderr = await ssh.run_command(
            dedent(f"""\
                cd /home/FCAM/svc_vivarium/workspace \
                && {remote_uv_executable} run scripts/get_parquet_data.py \
                    --experiment_id {experiment_id} \
                    --lineage_seed {lineage_seed} \
                    --generation {generation} \
                    --variant {variant} \
                    --agent_id {agent_id} \
                    --observables {" ".join(observables)!s}
            """)
        )

        # then, download the temp pq
        pq_filename = f"{experiment_id}.parquet"
        tmpdir = tempfile.TemporaryDirectory()
        local = Path(tmpdir.name, pq_filename)
        bg_tasks.add_task(tmpdir.cleanup)
        remote = Path(ENV.simulation_outdir).parent / "data" / pq_filename
        await ssh.scp_download(local_file=local, remote_path=remote)
        bg_tasks.add_task(ssh.run_command, f"rm {remote!s}")

        def generate(data: list[dict[str, Any]]) -> Generator[bytes, Any, None]:
            yield b"["
            first = True
            for item in data:
                if not first:
                    yield b","
                else:
                    first = False
                yield orjson.dumps(item)
            yield b"]"

        return fastapi.responses.StreamingResponse(
            generate(pl.read_parquet(local).to_dicts()), media_type="application/json"
        )

        # def generate(path: Path):
        #     # Collect with streaming engine
        #     df = pl.scan_parquet(path).collect(streaming=True)
        #     yield b"["
        #     first = True
        #     for batch in df.iter_slices(n_rows=10_000):  # chunked iteration
        #         for row in batch.iter_rows(named=True):
        #             if not first:
        #                 yield b","
        #             else:
        #                 first = False
        #             yield orjson.dumps(row)
        #     yield b"]"
        # return fastapi.responses.StreamingResponse(
        #     generate(local), media_type="application/json"
        # )

    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulations/data/download",
    operation_id="download-ecoli-simulation-data",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service)],
    summary="Download selected simulation data as a parquet file",
)
async def download_simulation_data(
    bg_tasks: BackgroundTasks,
    experiment_id: str = Query(default="sms_multigeneration"),
    lineage_seed: int = Query(default=6),
    generation: int = Query(default=1),
    variant: int = Query(default=0),
    agent_id: int = Query(default=0),
    observables: list[str] = request_examples.base_observables,
) -> FileResponse:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        ssh = get_ssh_service(ENV)

        # first, slice parquet and write temp pq to remote disk
        remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
        ret, stdout, stderr = await ssh.run_command(
            dedent(f"""\
                cd /home/FCAM/svc_vivarium/workspace \
                && {remote_uv_executable} run scripts/get_parquet_data.py \
                    --experiment_id {experiment_id} \
                    --lineage_seed {lineage_seed} \
                    --generation {generation} \
                    --variant {variant} \
                    --agent_id {agent_id} \
                    --observables {" ".join(observables)!s}
            """)
        )

        # then, download the temp pq
        pq_filename = f"{experiment_id}.parquet"
        tmpdir = tempfile.TemporaryDirectory()
        local = Path(tmpdir.name, pq_filename)
        bg_tasks.add_task(tmpdir.cleanup)
        remote = Path(ENV.simulation_outdir).parent / "data" / pq_filename
        await ssh.scp_download(local_file=local, remote_path=remote)
        bg_tasks.add_task(ssh.run_command, f"rm {remote!s}")

        # -- file blob response -- #
        tmpdir = tempfile.TemporaryDirectory()
        local = Path(tmpdir.name, pq_filename)
        bg_tasks.add_task(tmpdir.cleanup)
        remote = Path(ENV.simulation_outdir).parent / pq_filename
        await ssh.scp_download(local_file=local, remote_path=remote)
        return FileResponse(path=local, media_type="application/octet-stream", filename=local.name)
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e
