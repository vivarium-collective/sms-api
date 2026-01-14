"""
/analyses: this router is dedicated to the running and output retrieval of
    simulation analysis jobs/workflows
"""

# TODO: do we require simulation/analysis configs that are supersets of the original configs:
#   IE: where do we provide this special config: in vEcoli or API?
# TODO: what does a "configuration endpoint" actually mean (can we configure via the simulation?)
# TODO: labkey preprocessing
import logging
from collections.abc import Sequence

from fastapi import BackgroundTasks, Depends, HTTPException, Query
from fastapi import Path as FastAPIPath
from fastapi.requests import Request

from sms_api.analysis.analysis_service import AnalysisServiceSlurm
from sms_api.analysis.models import (
    AnalysisJobFailedException,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    OutputFile,
    OutputFileMetadata,
    TsvOutputFile,
)
from sms_api.api import request_examples
from sms_api.common import handlers
from sms_api.common.gateway.utils import router_config
from sms_api.config import get_settings
from sms_api.dependencies import get_database_service, get_simulation_service
from sms_api.simulation.models import Simulation, SimulationRun

ENV = get_settings()

logger = logging.getLogger(__name__)
config = router_config(prefix="api", version_major=False)


@config.router.post(
    path="/simulations",
    operation_id="run-ecoli-simulation",
    response_model=Simulation,
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="Launches a vEcoli simulation workflow with simple parameters",
)
async def run_simulation(
    simulator_id: int = Query(..., description="Database ID of the simulator to use"),
    experiment_id: str = Query(..., description="Unique experiment identifier"),
    simulation_config_filename: str = Query(..., description="Config filename in vEcoli/configs/ on HPC"),
    num_generations: int | None = Query(default=None, ge=1, le=10, description="Number of generations to simulate"),
    num_seeds: int | None = Query(default=None, ge=1, le=100, description="Number of initial seeds (lineages)"),
    description: str | None = Query(default=None, description="Description of the simulation"),
) -> Simulation:
    """Run a vEcoli simulation workflow with simplified parameters.

    This endpoint reads the workflow configuration from the vEcoli repo on the HPC
    system and allows overriding specific parameters via query params.
    """
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    database_service = get_database_service()
    if database_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await handlers.simulations.run_workflow_simple(
            database_service=database_service,
            simulation_service=sim_service,
            simulator_id=simulator_id,
            experiment_id=experiment_id,
            simulation_config_filename=simulation_config_filename,
            num_generations=num_generations,
            num_seeds=num_seeds,
            description=description,
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
async def get_simulation(id: int = FastAPIPath(description="Database ID of the simulation")) -> Simulation | None:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        # return await db_service.get_simulation(database_id=id)
        return await db_service.get_simulation(simulation_id=id)
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
async def get_simulation_status(id: int = FastAPIPath(...)) -> SimulationRun:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        return await handlers.simulations.get_simulation_status(db_service=db_service, id=id)
    except Exception as e:
        logger.exception(
            """Error getting simulation status.\
                Are you sure that you've passed the experiment_tag? (not the experiment id)
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulations",
    operation_id="list-ecoli-simulations",
    tags=["Simulations"],
    summary="List all simulation specs uploaded to the database",
    dependencies=[Depends(get_database_service)],
)
async def list_simulations() -> list[Simulation]:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        # return await db_service.list_simulations()
        return await handlers.simulations.list_simulations(db_service=db_service)
    except Exception as e:
        logger.exception("Error fetching the uploaded analyses")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulations/{id}/data",
    operation_id="get-ecoli-simulation-data",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service)],
    summary="Get simulation omics data in TSV format",
)
async def get_simulation_data(
    bg_tasks: BackgroundTasks,
    id: int = FastAPIPath(description="Database ID of the simulation."),
) -> list[TsvOutputFile]:
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await handlers.simulations.get_simulation_outputs(
            db_service=db_service, simulation_id=id, hpc_sim_base_path=ENV.hpc_sim_base_path
        )
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/analyses",
    operation_id="run-ecoli-simulation-analysis",
    tags=["Analyses"],
    summary="Run an analysis",
    dependencies=[
        Depends(get_database_service),
    ],
)
async def run_analysis(
    _request: Request,
    request: ExperimentAnalysisRequest = request_examples.analysis_ptools,
) -> Sequence[TsvOutputFile | OutputFileMetadata]:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    analysis_service = AnalysisServiceSlurm(env=ENV)

    # Look up the simulation by experiment_id to get the correct simulator
    simulation = await db_service.get_simulation_by_experiment_id(request.experiment_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail=f"No simulation found with experiment_id '{request.experiment_id}'")

    simulator = await db_service.get_simulator(simulation.simulator_id)
    if simulator is None:
        raise HTTPException(status_code=404, detail=f"Simulator with id {simulation.simulator_id} not found")

    try:
        return await handlers.analyses.handle_run_analysis(
            request=request,
            simulator=simulator,
            analysis_service=analysis_service,
            logger=logger,
            _request=_request,
            db_service=db_service,
        )
    except AnalysisJobFailedException as e:
        # Return detailed error for failed analysis jobs
        logger.warning(f"Analysis job failed: {e.message}")
        raise HTTPException(status_code=422, detail=e.to_dict()) from e
    except Exception as e:
        logger.exception("Error running analysis.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/analyses/{id}",
    operation_id="get-analysis",
    tags=["Analyses"],
    dependencies=[Depends(get_database_service)],
    summary="Retrieve an experiment analysis spec from the database",
)
async def get_analysis_spec(id: int) -> ExperimentAnalysisDTO:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        return await handlers.analyses.handle_get_analysis(db_service=db_service, id=id)
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
async def get_analysis_status(id: int = FastAPIPath(..., description="Database ID of the analysis")) -> AnalysisRun:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    aservice = AnalysisServiceSlurm(env=ENV)
    try:
        return await handlers.analyses.handle_get_analysis_status(
            db_service=db_service, analysis_service=aservice, ref=id
        )
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
async def get_analysis_log(id: int = FastAPIPath(..., description="Database ID of the analysis")) -> str:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        return await handlers.analyses.handle_get_analysis_log(db_service=db_service, id=id)
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
    id: int = FastAPIPath(..., description="Database ID of the analysis"),
) -> list[OutputFile]:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        return await handlers.analyses.handle_get_analysis_plots(db_service=db_service, id=id)
    except Exception as e:
        logger.exception("Error getting analysis data")
        raise HTTPException(status_code=500, detail=str(e)) from e
