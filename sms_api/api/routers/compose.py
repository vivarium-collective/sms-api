"""Compose (process-bigraph) simulation router — mounted at /compose/v1/."""

import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile
from jinja2 import Template
from starlette.responses import FileResponse

from sms_api.compose.database_service import ComposeDatabaseService
from sms_api.compose.handlers import (
    get_compose_simulator_versions,
    run_compose_curated,
    run_compose_simulation,
)
from sms_api.compose.job_monitor import ComposeJobMonitor
from sms_api.compose.models import (
    BiGraphComputeType,
    BiGraphProcess,
    BiGraphStep,
    ComposeHpcRun,
    ComposeJobType,
    ComposeRegisteredSimulators,
    ComposeSimulationExperiment,
    ComposeSimulationRequest,
    PBAllowList,
    SimulationFileType,
)
from sms_api.compose.simulation_service import ComposeSimulationService

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Dependency helpers (lazy — populated at app startup via dependencies.py)
# ---------------------------------------------------------------------------

_compose_db_service: ComposeDatabaseService | None = None
_compose_sim_service: ComposeSimulationService | None = None
_compose_job_monitor: ComposeJobMonitor | None = None

COMPOSE_ALLOW_LIST = [
    "pypi::git+https://github.com/biosimulators/bspil-basico.git@initial_work",
    "pypi::cobra",
    "pypi::tellurium",
    "pypi::copasi-basico",
    "pypi::smoldyn",
    "pypi::numpy",
    "pypi::matplotlib",
    "pypi::scipy",
    "pypi::pb_multiscale_actin",
    "conda::readdy",
]


def set_compose_services(
    db: ComposeDatabaseService,
    sim: ComposeSimulationService,
    monitor: ComposeJobMonitor,
) -> None:
    global _compose_db_service, _compose_sim_service, _compose_job_monitor
    _compose_db_service = db
    _compose_sim_service = sim
    _compose_job_monitor = monitor


def _require_db() -> ComposeDatabaseService:
    if _compose_db_service is None:
        raise HTTPException(500, "Compose database service not initialized")
    return _compose_db_service


def _require_sim() -> ComposeSimulationService:
    if _compose_sim_service is None:
        raise HTTPException(500, "Compose simulation service not initialized")
    return _compose_sim_service


def _require_monitor() -> ComposeJobMonitor:
    if _compose_job_monitor is None:
        raise HTTPException(500, "Compose job monitor not initialized")
    return _compose_job_monitor


# ---------------------------------------------------------------------------
# Upload helper
# ---------------------------------------------------------------------------


async def _parse_upload(uploaded_file: UploadFile, batch_submission: bool = False) -> ComposeSimulationRequest:
    if uploaded_file is None or uploaded_file.filename is None or uploaded_file.size == 0:
        raise HTTPException(400, "Empty uploaded file")
    suffix = Path(uploaded_file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        contents = await uploaded_file.read()
        tmp_file.write(contents)
    return ComposeSimulationRequest(
        request_file_path=Path(tmp_file.name),
        simulation_file_type=SimulationFileType.get_file_type(suffix),
        is_batch=batch_submission,
    )


# ---------------------------------------------------------------------------
# Simulation endpoints
# ---------------------------------------------------------------------------


@router.post(
    path="/simulation/run",
    operation_id="compose-run-simulation",
    response_model=ComposeSimulationExperiment,
    tags=["Compose Simulation"],
    summary="Run a process-bigraph simulation (OMEX/PBG/SBML upload)",
)
async def submit_simulation(
    background_tasks: BackgroundTasks,
    uploaded_file: UploadFile,
    interval_time: float = 1.0,
    batch_submission: bool = False,
) -> ComposeSimulationExperiment:
    if interval_time < 0 or interval_time > 1000:
        raise HTTPException(400, "interval_time must be between 0 and 1000")
    simulation_request = await _parse_upload(uploaded_file, batch_submission)
    simulation_request.end_time_point = interval_time
    return await run_compose_simulation(
        simulation_request=simulation_request,
        database_service=_require_db(),
        simulation_service=_require_sim(),
        job_monitor=_require_monitor(),
        pb_allow_list=PBAllowList(allow_list=COMPOSE_ALLOW_LIST),
        background_tasks=background_tasks,
    )


# ---------------------------------------------------------------------------
# Results endpoints
# ---------------------------------------------------------------------------


@router.get(
    path="/simulation/{simulation_id}/status",
    operation_id="compose-get-simulation-status",
    response_model=ComposeHpcRun,
    tags=["Compose Results"],
    summary="Get compose simulation job status",
)
async def get_simulation_status(simulation_id: int) -> ComposeHpcRun:
    db = _require_db()
    hpc_run = await db.get_hpc_db().get_hpcrun_by_ref(ref_id=simulation_id, job_type=ComposeJobType.SIMULATION)
    if hpc_run is None:
        raise HTTPException(404, f"Compose simulation {simulation_id} not found")
    return hpc_run


@router.get(
    path="/simulations/status/batch",
    operation_id="compose-get-simulations-status-batch",
    response_model=list[ComposeHpcRun],
    tags=["Compose Results"],
    summary="Batch status lookup for compose simulations",
)
async def get_simulations_status_batch(ids: list[int] = Query()) -> list[ComposeHpcRun]:
    return await _require_db().get_hpc_db().get_hpcruns_by_refs(ref_ids=ids, job_type=ComposeJobType.SIMULATION)


@router.get(
    path="/simulation/{simulation_id}/results",
    response_class=FileResponse,
    operation_id="compose-get-simulation-results",
    tags=["Compose Results"],
    summary="Download compose simulation results as zip",
    responses={200: {"content": {"application/zip": {}}, "description": "Results zip file"}},
)
async def get_results(simulation_id: int) -> FileResponse:
    from sms_api.compose.hpc_utils import get_compose_sim_results_path

    db = _require_db()
    experiment_id = await db.get_simulator_db().get_simulations_experiment_id(simulation_id=simulation_id)
    results_path = get_compose_sim_results_path(experiment_id)
    # In a deployed environment, results are on a shared filesystem mount
    return FileResponse(path=str(results_path), filename=f"{experiment_id}_results.zip", media_type="application/zip")


@router.get(
    path="/simulator/{simulator_id}/build/status",
    operation_id="compose-get-simulator-build-status",
    response_model=ComposeHpcRun,
    tags=["Compose Results"],
    summary="Get compose container build status",
)
async def get_simulator_build_status(simulator_id: int) -> ComposeHpcRun:
    hpc_run = (
        await _require_db().get_hpc_db().get_hpcrun_by_ref(ref_id=simulator_id, job_type=ComposeJobType.BUILD_CONTAINER)
    )
    if hpc_run is None:
        raise HTTPException(404, f"Build for simulator {simulator_id} not found")
    return hpc_run


@router.get(
    path="/simulation/{simulation_id}/document",
    operation_id="compose-get-simulation-document",
    tags=["Compose Results"],
    summary="Retrieve the process-bigraph document used for a compose simulation",
    responses={
        200: {"content": {"application/json": {}}, "description": "PBG/SBML document content"},
        404: {"description": "Simulation not found or no document stored"},
    },
)
async def get_simulation_document(simulation_id: int) -> dict:  # type: ignore[type-arg]
    """Return the process-bigraph document (PBG JSON, SBML XML, or OMEX manifest)
    that was uploaded when this simulation was submitted."""
    import json

    db = _require_db()
    doc = await db.get_simulator_db().get_simulation_document(simulation_id)
    if doc is None:
        raise HTTPException(404, f"No document stored for compose simulation {simulation_id}")
    # Try to parse as JSON (PBG files are JSON); fall back to wrapping raw content
    try:
        return json.loads(doc)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {"format": "raw", "content": doc}


# ---------------------------------------------------------------------------
# Compute registry endpoints
# ---------------------------------------------------------------------------


@router.get(
    path="/simulators",
    operation_id="compose-list-simulators",
    response_model=ComposeRegisteredSimulators,
    tags=["Compose Compute"],
    summary="List registered compose simulators",
)
async def list_simulators() -> ComposeRegisteredSimulators:
    return await get_compose_simulator_versions(_require_db())


@router.get(
    path="/processes",
    operation_id="compose-list-processes",
    response_model=list[BiGraphProcess],
    tags=["Compose Compute"],
    summary="List registered process-bigraph processes",
)
async def list_processes() -> list[BiGraphProcess]:
    result: list[BiGraphProcess] = await _require_db().get_package_db().list_all_computes(BiGraphComputeType.PROCESS)
    return result


@router.get(
    path="/steps",
    operation_id="compose-list-steps",
    response_model=list[BiGraphStep],
    tags=["Compose Compute"],
    summary="List registered process-bigraph steps",
)
async def list_steps() -> list[BiGraphStep]:
    result: list[BiGraphStep] = await _require_db().get_package_db().list_all_computes(BiGraphComputeType.STEP)
    return result


# ---------------------------------------------------------------------------
# Curated simulator endpoints
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


@router.post(
    path="/curated/copasi",
    operation_id="compose-run-copasi",
    response_model=ComposeSimulationExperiment,
    tags=["Compose Curated"],
    summary="Run COPASI simulation from SBML",
)
async def run_copasi(
    background_tasks: BackgroundTasks, sbml: UploadFile, start_time: float, duration: float, num_data_points: float
) -> ComposeSimulationExperiment:
    from sms_api.config import get_settings

    with open(os.path.join(_TEMPLATES_DIR, "copasi.jinja")) as f:
        render = Template(f.read()).render(
            start_time=start_time,
            duration=duration,
            num_data_points=num_data_points,
            output_dir=get_settings().compose_containers_output_dir,
        )
    request = await _parse_upload(sbml)
    if request.simulation_file_type is not SimulationFileType.SBML:
        raise HTTPException(400, "Expected a SBML file.")
    return await run_compose_curated(
        templated_pbif=render,
        simulator_name="Copasi",
        loaded_sbml=request.request_file_path,
        background_tasks=background_tasks,
        db_service=_require_db(),
        sim_service=_require_sim(),
        job_monitor=_require_monitor(),
    )


@router.post(
    path="/curated/tellurium",
    operation_id="compose-run-tellurium",
    response_model=ComposeSimulationExperiment,
    tags=["Compose Curated"],
    summary="Run Tellurium simulation from SBML",
)
async def run_tellurium(
    background_tasks: BackgroundTasks, sbml: UploadFile, start_time: float, end_time: float, num_data_points: float
) -> ComposeSimulationExperiment:
    from sms_api.config import get_settings

    with open(os.path.join(_TEMPLATES_DIR, "tellurium.jinja")) as f:
        render = Template(f.read()).render(
            start_time=start_time,
            end_time=end_time,
            num_data_points=num_data_points,
            output_dir=get_settings().compose_containers_output_dir,
        )
    request = await _parse_upload(sbml)
    if request.simulation_file_type is not SimulationFileType.SBML:
        raise HTTPException(400, "Expected a SBML file.")
    return await run_compose_curated(
        templated_pbif=render,
        simulator_name="Tellurium",
        loaded_sbml=request.request_file_path,
        background_tasks=background_tasks,
        db_service=_require_db(),
        sim_service=_require_sim(),
        job_monitor=_require_monitor(),
    )
