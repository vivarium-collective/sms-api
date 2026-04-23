"""
/analyses: this router is dedicated to the running and output retrieval of
    simulation analysis jobs/workflows
"""

# TODO: do we require simulation/analysis configs that are supersets of the original configs:
#   IE: where do we provide this special config: in vEcoli or API?
# TODO: what does a "configuration endpoint" actually mean (can we configure via the simulation?)
# TODO: labkey preprocessing
import json
import logging
from collections.abc import Sequence

from fastapi import BackgroundTasks, Depends, HTTPException, Query
from fastapi import Path as FastAPIPath
from fastapi.requests import Request
from fastapi.responses import FileResponse, Response, StreamingResponse

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
from sms_api.common.gateway.utils import get_router_config
from sms_api.config import ComputeBackend, get_job_backend, get_settings
from sms_api.dependencies import get_database_service, get_simulation_service
from sms_api.simulation.models import AnalysisOptions, RepoDiscovery, Simulation, SimulationRun


def _validate_simulation_config_filename(simulation_config_filename: str) -> None:
    """Reject ``configs/`` prefix typos that would silently 404 on the server."""
    if simulation_config_filename.startswith("configs/"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"simulation_config_filename {simulation_config_filename!r} starts "
                "with 'configs/'. The server prepends 'configs/' itself; pass the "
                "path relative to the repo's configs/ directory (e.g. "
                "'campaigns/pilot_mixed.json' instead of "
                "'configs/campaigns/pilot_mixed.json')."
            ),
        )


ENV = get_settings()

logger = logging.getLogger(__name__)
config = get_router_config(prefix="api", version_major=False)


def get_experiment_id(simulator_id: int, config_filename: str) -> str:
    return f"sim{simulator_id}-{config_filename.replace('.json', '')}"


AnalysisOptions()


@config.router.get(
    path="/simulations/discovery",
    operation_id="discover-simulator-repo-contents",
    response_model=RepoDiscovery,
    tags=["Simulations"],
    summary="Discover available config files and analysis modules for a simulator",
)
async def discover_repo_contents(
    simulator_id: int = Query(..., description="database_id of the simulator to introspect"),
) -> RepoDiscovery:
    """Enumerate config filenames and analysis modules available in the simulator's repo."""
    sim_service = get_simulation_service()
    database_service = get_database_service()
    if sim_service is None or database_service is None:
        raise HTTPException(status_code=500, detail="Services not initialized")
    simulator = await database_service.get_simulator(simulator_id)
    if simulator is None:
        raise HTTPException(status_code=404, detail=f"Simulator {simulator_id} not found")
    return await sim_service.discover_repo_contents(simulator)


@config.router.post(
    path="/simulations",
    operation_id="run-ecoli-simulation-new",
    response_model=Simulation,
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="[New] Launches a vEcoli simulation workflow with simple parameters",
)
async def run_simulation_workflow(
    simulator_id: int = Query(
        ..., description="`database_id` of the simulator object returned by /core/v1/simulator/upload"
    ),
    experiment_id: str | None = Query(default=None, description="Unique experiment identifier"),
    simulation_config_filename: str = Query(
        default="api_simulation_default.json",
        description="Config filename in vEcoli/configs/. Use GET /simulations/discovery to list available files.",
    ),
    num_generations: int | None = Query(default=None, description="Number of generations to simulate"),
    num_seeds: int | None = Query(default=None, description="Number of initial seeds (lineages)"),
    description: str | None = Query(default=None, description="Description of the simulation"),
    run_parca: bool | None = Query(
        default=None,
        description="If true, run the simulation parameter calculator prior "
        "to running simulation (re-parameterizes simulation "
        "workflow).",
    ),
    observables: list[str] | None = Query(
        default=None,
        description="Dot-separated vEcoli output paths to observe. "
        "E.g. ['bulk', 'listeners.mass.cell_mass']. "
        "Maps to engine_process_reports in the vEcoli config. "
        "If omitted, all outputs are emitted.",
    ),
    analysis_options: AnalysisOptions | None = None,
) -> Simulation:
    """Run a vEcoli simulation workflow with simplified parameters.

    This endpoint reads the workflow configuration from the vEcoli repo on the HPC
    system and allows overriding specific parameters via query params.
    """
    _validate_simulation_config_filename(simulation_config_filename)
    if experiment_id is None:
        experiment_id = get_experiment_id(simulator_id, simulation_config_filename)
    sim_service = get_simulation_service()
    if sim_service is None:
        logger.error("Simulation service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    database_service = get_database_service()
    if database_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await handlers.simulations.run_simulation_workflow(
            database_service=database_service,
            simulation_service=sim_service,
            simulator_id=simulator_id,
            experiment_id=experiment_id,
            simulation_config_filename=simulation_config_filename,
            num_generations=num_generations,
            num_seeds=num_seeds,
            description=description,
            run_parca=run_parca,
            observables=observables,
            analysis_options=analysis_options,
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


@config.router.delete(
    path="/simulations/{id}/cancel",
    response_model=SimulationRun,
    operation_id="cancel-ecoli-simulation",
    tags=["Simulations"],
    dependencies=[Depends(get_simulation_service), Depends(get_database_service)],
    summary="Cancel a running simulation",
)
async def cancel_simulation(id: int = FastAPIPath(description="Database ID of the simulation")) -> SimulationRun:
    """Cancel a running simulation by killing its backend job."""
    sim_service = get_simulation_service()
    if sim_service is None:
        raise HTTPException(status_code=500, detail="Simulation service is not initialized")
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await handlers.simulations.cancel_simulation(
            db_service=db_service,
            simulation_service=sim_service,
            simulation_id=id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error cancelling simulation")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/simulations/{id}/log",
    operation_id="get-ecoli-simulation-log",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service)],
    summary="Get the structured output of a given simulation workflow log.",
)
async def get_simulation_log(
    id: int = FastAPIPath(...),
    truncate: bool = Query(
        default=True,
        description="If true, return only the Nextflow header + final status block "
        "(separated by '... truncated ...'). Set to false for the full log.",
    ),
) -> Response:
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")
    try:
        return await handlers.simulations.get_simulation_log(db_service=db_service, simulation_id=id, truncate=truncate)
    except Exception as e:
        logger.exception(
            """Error getting simulation status.\
                Are you sure that you've passed the experiment_tag? (not the experiment id)
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.post(
    path="/simulations/{id}/analysis",
    operation_id="run-ecoli-simulation-analysis",
    tags=["Simulations"],
    dependencies=[Depends(get_database_service)],
    summary="Run standalone analysis on existing simulation output",
)
async def run_simulation_analysis(
    id: int = FastAPIPath(description="Database ID of a completed simulation."),
    modules: str | None = Query(
        default=None,
        description="JSON object mapping analysis domains to module configs. "
        'E.g. \'{"multiseed": {"ptools_rna": {"n_tp": 10}}}\'.'
        " If omitted, runs default ptools modules.",
    ),
) -> dict:  # type: ignore[type-arg]
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        parsed_modules = json.loads(modules) if modules else None
        return await handlers.simulations.run_standalone_analysis(
            database_service=db_service,
            simulation_id=id,
            modules=parsed_modules,
        )
    except Exception as e:
        logger.exception("Error running standalone analysis")
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
    summary="Get simulation omics data as a downloadable tar.gz archive",
    response_model=None,
    responses={
        200: {
            "content": {"application/gzip": {}},
            "description": "A tar.gz archive containing simulation output files",
        }
    },
)
async def get_simulation_data(
    bg_tasks: BackgroundTasks,
    id: int = FastAPIPath(description="Database ID of the simulation."),
    response_type: handlers.simulations.SimulationAnalysisDataResponseType = Query(
        default=handlers.simulations.SimulationAnalysisDataResponseType.FILE,
        description="Response type: 'file' for direct download (recommended for browsers/Swagger UI), "
        "'streaming' for chunked streaming response (better for large files or programmatic access)",
    ),
) -> StreamingResponse | FileResponse:
    """Get simulation outputs as a tar.gz archive.

    Choose response_type based on your use case:
    - **file**: Creates the archive and returns it as a downloadable file.
      Best for browser downloads and Swagger UI - shows a "Download" button.
    - **streaming**: Streams the archive in chunks as it's created.
      Better for very large files or when you want to start processing before download completes.
    """
    db_service = get_database_service()
    if db_service is None:
        logger.error("Database service is not initialized")
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await handlers.simulations.get_simulation_outputs(
            db_service=db_service,
            simulation_id=id,
            hpc_sim_base_path=ENV.hpc_sim_base_path,
            data_response_type=response_type,
            bg_tasks=bg_tasks,
        )
    except Exception as e:
        logger.exception("Error retrieving simulation data")
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
    if get_job_backend() != ComputeBackend.SLURM:
        raise HTTPException(
            status_code=501,
            detail="Legacy analysis not supported for K8s backend. Use POST /api/v1/simulations/{id}/analysis instead.",
        )
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
    if get_job_backend() != ComputeBackend.SLURM:
        raise HTTPException(status_code=501, detail="Legacy analysis status not supported for K8s backend")
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
