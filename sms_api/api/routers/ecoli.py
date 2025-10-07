"""
/analyses: this router is dedicated to the running and output retrieval of
    simulation analysis jobs/workflows
"""

# TODO: do we require simulation/analysis configs that are supersets of the original configs:
#   IE: where do we provide this special config: in vEcoli or API?
# TODO: what does a "configuration endpoint" actually mean (can we configure via the simulation?)
# TODO: labkey preprocessing

import logging

import fastapi
from fastapi import BackgroundTasks, Depends, File, HTTPException, Query, UploadFile

from sms_api.api import request_examples
from sms_api.common.gateway.utils import get_simulator, router_config
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.common.utils import timestamp
from sms_api.config import get_settings
from sms_api.data import analysis_service
from sms_api.data import ecoli_handlers as data_handlers
from sms_api.data.models import (
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    OutputFile,
    TsvOutputFile,
    TsvOutputFileRequest,
)
from sms_api.dependencies import get_database_service, get_simulation_service
from sms_api.simulation import ecoli_handlers as simulation_handlers
from sms_api.simulation.models import (
    EcoliSimulationDTO,
    ExperimentMetadata,
    ExperimentRequest,
    SimulationRun,
)

ENV = get_settings()

logger = logging.getLogger(__name__)
config = router_config(prefix="ecoli")


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
        return await data_handlers.run_analysis(
            request=request,
            simulator=get_simulator(),
            analysis_service=analysis_service,
            env=ENV,
            db_service=db_service,
            timestamp=timestamp(),
            logger=logger,
        )
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
        return await data_handlers.get_analysis(db_service=db_service, id=id)
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}/manifest",
    tags=["Analyses"],
    operation_id="get-analysis-manifest",
    dependencies=[Depends(get_database_service)],
    summary="Get the available outputs of a given analysis",
)
async def get_ptools_manifest(
    id: int = fastapi.Path(..., description="Database ID of the analysis"),
) -> list[TsvOutputFile]:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    ssh_service = get_ssh_service(ENV)

    try:
        return await data_handlers.get_ptools_manifest(
            db_service=db_service, env=ENV, ssh_service=ssh_service, id=id, analysis_service=analysis_service
        )
    except Exception as e:
        logger.exception("Error getting analysis data")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/analyses/{id}/tsv",
    response_model=None,
    operation_id="get-analysis-output-file",
    tags=["Analyses"],
    dependencies=[Depends(get_database_service)],
    summary="Get the contents single file that was generated from a simulation analysis module",
)
async def get_analysis_output_file(request: TsvOutputFileRequest, id: int = fastapi.Path(...)) -> TsvOutputFile:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    ssh_service = get_ssh_service(ENV)
    try:
        return await data_handlers.get_tsv_output(
            request=request, db_service=db_service, id=id, env=ENV, ssh=ssh_service, analysis_service=analysis_service
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
async def get_analysis_status(id: int = fastapi.Path(..., description="Database ID of the analysis")) -> AnalysisRun:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    ssh_service = get_ssh_service(ENV)
    try:
        return await data_handlers.get_analysis_status(db_service=db_service, ssh_service=ssh_service, id=id, env=ENV)
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
    ssh_service = get_ssh_service()
    try:
        # analysis_record = await db_service.get_analysis(database_id=id)
        # slurm_logfile = Path(ENV.slurm_log_base_path) / f"{analysis_record.job_name}.out"
        # ret, stdout, stdin = await ssh_service.run_command(f"cat {slurm_logfile!s}")
        # return stdout
        return await data_handlers.get_analysis_log(db_service=db_service, id=id, env=ENV, ssh_service=ssh_service)
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
    ssh_service = get_ssh_service(ENV)
    try:
        return await data_handlers.get_analysis_plots(
            db_service=db_service, id=id, env=ENV, analysis_service=analysis_service, ssh_service=ssh_service
        )
    except Exception as e:
        logger.exception("Error getting analysis data")
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
    ssh_service = get_ssh_service(ENV)
    try:
        return await data_handlers.upload_analysis_module(
            file=file, ssh=ssh_service, submodule_name=submodule_name, env=ENV
        )
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
        # return await db_service.list_analyses()
        return await data_handlers.list_analyses(db_service=db_service)
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
        return await simulation_handlers.run_simulation(
            sim_service=sim_service,
            config=config,
            request=request,
            env=ENV,
            logger=logger,
            db_service=db_service,
            timestamp=timestamp(),
        )
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
        # return await db_service.get_ecoli_simulation(database_id=id)
        return await simulation_handlers.get_simulation(db_service=db_service, id=id)
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
        return await simulation_handlers.get_simulation_status(
            db_service=db_service, id=id, env=ENV, ssh_service=get_ssh_service(ENV)
        )
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
    ssh_service = get_ssh_service()
    try:
        return await simulation_handlers.get_simulation_log_detailed(
            db_service=db_service, ssh_service=ssh_service, id=id, env=ENV
        )
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
        return await simulation_handlers.get_simulation_log(
            db_service=db_service, ssh_service=ssh_service, id=id, env=ENV
        )
    except Exception as e:
        logger.exception("""Error getting simulation log.""")
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
        # return await db_service.list_ecoli_simulations()
        return await simulation_handlers.list_simulations(db_service=db_service)
    except Exception as e:
        logger.exception("Error fetching the uploaded analyses")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulations/{id}/data",
    operation_id="get-ecoli-simulation-data",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service)],
    summary="Get/Stream simulation data",
)
async def get_simulation_data(
    bg_tasks: BackgroundTasks,
    id: int = fastapi.Path(description="Database ID of the simulation."),
    # experiment_id: str = Query(default="sms_multigeneration"),
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
        return await simulation_handlers.get_simulation_data(
            ssh=get_ssh_service(ENV),
            db_service=db_service,
            id=id,
            lineage_seed=lineage_seed,
            generation=generation,
            variant=variant,
            agent_id=agent_id,
            observables=observables,
            env=ENV,
            bg_tasks=bg_tasks,
        )
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e
