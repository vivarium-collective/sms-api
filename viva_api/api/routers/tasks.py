"""
/tasks: the in-region task-run verb (viva-api#631 slice 1) -- submit a
self-contained repo-path script through the SAME Ray/Batch container path
ParCa and the analysis DAG node already use, and poll its status.
Submit-then-poll rather than a long synchronous request, matching this
repo's own EUTE convention for anything that can outlast a gateway's idle
timeout (see CLAUDE.md "Pitfall 6").
"""

import logging

from fastapi import Body, HTTPException
from fastapi import Path as FastAPIPath

from viva_api.common.gateway.utils import get_router_config
from viva_api.config import ComputeBackend
from viva_api.dependencies import get_database_service, get_simulation_service_for_backend
from viva_api.simulation.models import TaskDTO, TaskRunRequest
from viva_api.simulation.simulation_service_ray import SimulationServiceRay

logger = logging.getLogger(__name__)
config = get_router_config(prefix="api", version_major=False)


@config.router.post(
    path="/tasks",
    response_model=TaskDTO,
    operation_id="run-task",
    tags=["Tasks"],
    summary="Submit a self-contained repo-path script to the in-region task compute (viva-api#631)",
)
async def run_task(request: TaskRunRequest = Body(...)) -> TaskDTO:
    # This verb always runs through the Ray/Batch container path -- ask for it
    # by name rather than trusting the deployment's own COMPUTE_BACKEND default
    # (get_simulation_service()), which is not necessarily Ray/Batch. Same
    # reasoning as run_new_gene_cache/run_variant_cache
    # (viva_api/common/handlers/simulations.py).
    simulation_service = get_simulation_service_for_backend(ComputeBackend.RAY)
    if simulation_service is None:
        raise HTTPException(status_code=404, detail="Simulation service is not initialized")
    if not isinstance(simulation_service, SimulationServiceRay):
        raise HTTPException(status_code=501, detail="task runs require the Ray/Batch simulation service")
    database_service = get_database_service()
    if database_service is None:
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await simulation_service.submit_task(request, database_service)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error submitting task run")
        raise HTTPException(status_code=500, detail=str(e)) from e


@config.router.get(
    path="/tasks/{task_id}/status",
    response_model=TaskDTO,
    operation_id="get-task-status",
    tags=["Tasks"],
    summary="Poll a task run's status (viva-api#631)",
)
async def get_task_status(
    task_id: int = FastAPIPath(description="Database ID of a submitted task."),
) -> TaskDTO:
    simulation_service = get_simulation_service_for_backend(ComputeBackend.RAY)
    if simulation_service is None:
        raise HTTPException(status_code=404, detail="Simulation service is not initialized")
    if not isinstance(simulation_service, SimulationServiceRay):
        raise HTTPException(status_code=501, detail="task runs require the Ray/Batch simulation service")
    database_service = get_database_service()
    if database_service is None:
        raise HTTPException(status_code=500, detail="Database service is not initialized")
    try:
        return await simulation_service.get_task_status(task_id, database_service)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting task status for %s", task_id)
        raise HTTPException(status_code=500, detail=str(e)) from e
