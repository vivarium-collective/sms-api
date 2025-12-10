"""
/analyses: this router is dedicated to the running and output retrieval of
    simulation analysis jobs/workflows
"""

# TODO: do we require simulation/analysis configs that are supersets of the original configs:
#   IE: where do we provide this special config: in vEcoli or API?
# TODO: what does a "configuration endpoint" actually mean (can we configure via the simulation?)
# TODO: labkey preprocessing
import logging
from collections.abc import Awaitable
from typing import Any, Callable, TypeVar

import fastapi
from fastapi import BackgroundTasks, Depends, HTTPException, Query

from sms_api.api import request_examples
from sms_api.common.gateway.utils import router_config
from sms_api.common.ssh.ssh_service import SSHServiceManaged, get_ssh_service, get_ssh_service_managed
from sms_api.common.utils import timestamp
from sms_api.data import ecoli_handlers as data_handlers
from sms_api.data import handlers as analysis_handlers
from sms_api.data.models import (
    AnalysisConfig,
    AnalysisDomain,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    OutputFile,
    TsvOutputFile,
)
from sms_api.dependencies import get_database_service, get_simulation_service
from sms_api.simulation import ecoli_handlers as simulation_handlers
from sms_api.simulation.models import (
    EcoliSimulationDTO,
    ExperimentMetadata,
    ExperimentRequest,
    SimulationRun,
)

logger = logging.getLogger(__name__)
config = router_config(prefix="ecoli")


def get_analysis_request_config(request: ExperimentAnalysisRequest, analysis_name: str) -> AnalysisConfig:
    return request.to_config(analysis_name=analysis_name)


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def connect_ssh(func: F) -> Any:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        instance = args[0]
        ssh_service: SSHServiceManaged = (
            kwargs.get("ssh_service") if not getattr(instance, "ssh_service", None) else instance.ssh_service
        )
        # ssh_service = kwargs.get('ssh_service', get_ssh_service_managed())
        try:
            print(f"Connecting ssh for function: {func.__name__}!")
            await ssh_service.connect()
            print(f"Connected: {ssh_service.connected}")
            return await func(*args, **kwargs)
        finally:
            print(f"Disconnecting ssh for function: {func.__name__}!")
            await ssh_service.disconnect()
            print(f"Connected: {ssh_service.connected}")

    return wrapper


def missing_experiment_error(exp_id: str) -> None:
    raise Exception(f"There is no experiment with an id of: {exp_id} in the database yet!")


###### -- analyses -- ######


@config.router.post(
    path="/analyses",
    operation_id="run-simulation-analysis",
    tags=["Analyses"],
    summary="Run an analysis",
    dependencies=[
        Depends(get_database_service),
        # Depends(get_ssh_svc)
    ],
)
async def run_analysis(
    request: ExperimentAnalysisRequest = request_examples.analysis_ptools,
) -> list[TsvOutputFile]:
    # get services
    db_service = get_database_service()
    if db_service is None:
        raise HTTPException(status_code=404, detail="Database not found")

    ssh_service = get_ssh_service_managed()
    await ssh_service.connect()

    try:
        # 1. check if expid-specified simulation exists in db first
        simulations = await db_service.list_ecoli_simulations()
        in_db = any([simulation.config.experiment_id == request.experiment_id for simulation in simulations])
        if not in_db:
            missing_experiment_error(request.experiment_id)

        # 2. if in db, that means that the analysis exists, so download
        experiment_id = request.experiment_id
        # TODO: should this be unique? (No...)
        analysis_name = (
            "sms_analysis-03ff8218c86170fe_1761645234195"
            if experiment_id == analysis_handlers.DEFAULT_EXPERIMENT
            # else get_data_id(exp_id=experiment_id, scope="analysis")
            else experiment_id
        )

        # 3. iterate over requested analysis outputs and format
        outputs: list[TsvOutputFile] = []
        requested_domains = request.requested
        for analysis_type in AnalysisDomain.to_list():
            domain_request = requested_domains.get(analysis_type)
            if domain_request is not None:
                output_filenames = [
                    f"{fname}_{analysis_type}.txt" for fname in analysis_handlers.PtoolsAnalysisType.to_list()
                ]
                analysis_config = request.to_config(analysis_name=analysis_name)

                for filename in output_filenames:
                    print(f"Requested file: {filename}")
                    output: TsvOutputFile = await analysis_handlers.get_ptools_output(
                        ssh=ssh_service,
                        analysis_request=request,
                        analysis_request_config=analysis_config,
                        filename=filename,
                    )
                    outputs.append(output)
        return outputs
    except Exception as e:
        logger.exception("Error fetching the simulation analysis file.")
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await ssh_service.disconnect()


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
        return await data_handlers.get_analysis(db_service=db_service, id=id)
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
    ssh_service = get_ssh_service_managed()
    await ssh_service.connect()
    try:
        return await data_handlers.get_analysis_status(db_service=db_service, ssh_service=ssh_service, id=id)
    except Exception as e:
        logger.exception(
            """Error getting simulation status.\
                Are you sure that you've passed the experiment_tag? (not the experiment id)
            """
        )
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await ssh_service.disconnect()


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
        return await data_handlers.get_analysis_log(db_service=db_service, id=id, ssh_service=ssh_service)
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

    ssh_service = get_ssh_service_managed()
    await ssh_service.connect()

    try:
        return await data_handlers.get_analysis_plots(db_service=db_service, id=id, ssh_service=ssh_service)
    except Exception as e:
        logger.exception("Error getting analysis data")
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await ssh_service.disconnect()


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
            db_service=db_service, id=id, ssh_service=get_ssh_service()
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
            db_service=db_service,
            ssh_service=ssh_service,
            id=id,
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
            ssh=get_ssh_service(),
            db_service=db_service,
            id=id,
            lineage_seed=lineage_seed,
            generation=generation,
            variant=variant,
            agent_id=agent_id,
            observables=observables,
            bg_tasks=bg_tasks,
        )
    except Exception as e:
        logger.exception("Error uploading simulation config")
        raise HTTPException(status_code=500, detail=str(e)) from e
