"""Request handlers for the compose simulation subsystem."""

import asyncio
import logging
import random
import shutil
import string
import tempfile
import zipfile
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException
from pbest.containerization.container_constructor import generate_container_def_file
from pbest.utils.input_types import (
    ContainerizationEngine,
    ContainerizationProgramArguments,
    ContainerizationTypes,
)

from sms_api.compose.database_service import ComposeDatabaseService
from sms_api.compose.hpc_utils import get_compose_correlation_id, get_compose_experiment_id
from sms_api.compose.job_monitor import ComposeJobMonitor
from sms_api.compose.models import (
    ComposeHpcRun,
    ComposeJobStatus,
    ComposeJobType,
    ComposeRegisteredSimulators,
    ComposeSimulation,
    ComposeSimulationExperiment,
    ComposeSimulationRequest,
    PBAllowList,
    SimulationFileType,
    get_singularity_hash,
)
from sms_api.compose.simulation_service import ComposeSimulationService

logger = logging.getLogger(__name__)


async def get_compose_simulator_versions(db_service: ComposeDatabaseService) -> ComposeRegisteredSimulators:
    simulators = await db_service.get_simulator_db().list_simulators()
    return ComposeRegisteredSimulators(versions=simulators)


async def run_compose_simulation(
    simulation_request: ComposeSimulationRequest,
    database_service: ComposeDatabaseService,
    simulation_service: ComposeSimulationService,
    job_monitor: ComposeJobMonitor,
    pb_allow_list: PBAllowList,
    background_tasks: BackgroundTasks,
) -> ComposeSimulationExperiment:
    with tempfile.TemporaryDirectory(delete=False) as tmp_dir:
        singularity_rep = generate_container_def_file(
            ContainerizationProgramArguments(
                input_file_path=str(simulation_request.request_file_path),
                working_directory=Path(tmp_dir),
                containerization_type=ContainerizationTypes.SINGLE,
                containerization_engine=ContainerizationEngine.APPTAINER,
            ),
        )

    simulator_db = database_service.get_simulator_db()
    simulator_version = await simulator_db.get_simulator_by_def_hash(get_singularity_hash(singularity_rep))
    if simulator_version is None:
        simulator_version = await simulator_db.insert_simulator(singularity_rep)

    random_string = "".join(random.choices(string.hexdigits, k=7))
    experiment_id = get_compose_experiment_id(simulator=simulator_version, random_str=random_string)
    simulation = await simulator_db.insert_simulation(
        sim_request=simulation_request, experiment_id=experiment_id, simulator_version=simulator_version
    )

    async def perform_job() -> None:
        await _dispatch_compose_job(
            database_service=database_service,
            job_monitor=job_monitor,
            simulation_service=simulation_service,
            simulation=simulation,
            experiment_id=experiment_id,
        )

    def remove_temp_dir() -> None:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    background_tasks.add_task(perform_job)
    background_tasks.add_task(remove_temp_dir)

    return ComposeSimulationExperiment(
        simulation_database_id=simulation.database_id,
        simulator_database_id=simulator_version.database_id,
    )


async def run_compose_curated(
    templated_pbif: str,
    simulator_name: str,
    background_tasks: BackgroundTasks,
    loaded_sbml: Path,
    db_service: ComposeDatabaseService,
    sim_service: ComposeSimulationService,
    job_monitor: ComposeJobMonitor,
    use_interesting: bool = True,
) -> ComposeSimulationExperiment:
    with tempfile.TemporaryDirectory(delete=False) as tmp_dir:
        with zipfile.ZipFile(tmp_dir + "/input.omex", "w") as omex:
            omex.writestr(data=templated_pbif, zinfo_or_arcname=f"{simulator_name}.pbg")
            if use_interesting:
                omex.write(loaded_sbml.absolute(), arcname="interesting.sbml")
            else:
                omex.write(loaded_sbml.absolute(), arcname=loaded_sbml.name)
        if omex.filename is None:
            raise HTTPException(500, "Can't create omex file.")
        simulation_request = ComposeSimulationRequest(
            request_file_path=Path(omex.filename), simulation_file_type=SimulationFileType.OMEX, is_batch=False
        )
        return await run_compose_simulation(
            simulation_request=simulation_request,
            database_service=db_service,
            simulation_service=sim_service,
            job_monitor=job_monitor,
            pb_allow_list=PBAllowList(allow_list=[]),
            background_tasks=background_tasks,
        )


async def _dispatch_compose_job(
    database_service: ComposeDatabaseService,
    job_monitor: ComposeJobMonitor,
    simulation_service: ComposeSimulationService,
    simulation: ComposeSimulation,
    experiment_id: str,
) -> None:
    simulator_version = simulation.simulator_version
    hpc_db = database_service.get_hpc_db()
    simulator_hpc_id = await hpc_db.get_hpcrun_id_by_simulator_id(simulator_id=simulator_version.database_id)
    random_string = "".join(random.choices(string.hexdigits, k=7))

    if simulator_hpc_id is None:
        hpc_run = await simulation_service.build_container(
            simulator_version=simulator_version, random_str=random_string, db_service=database_service
        )
        job_queue: asyncio.Queue[ComposeHpcRun] = asyncio.Queue()
        job_monitor.internal_subscribe(job_queue, hpc_run.slurmjobid)
        wait_time = 0
        current_status = hpc_run.status
        while current_status != ComposeJobStatus.COMPLETED:
            wait_time += 1
            try:
                current_status = (await asyncio.wait_for(job_queue.get(), timeout=60)).status
            except TimeoutError:
                latest = await hpc_db.get_hpcrun_by_slurmjobid(hpc_run.slurmjobid)
                if latest is None:
                    raise RuntimeError(
                        f"Can't get HPC Run for container build {simulator_version.singularity_def_hash}"
                    )
                current_status = latest.status
            if current_status == ComposeJobStatus.FAILED:
                raise RuntimeError(f"Building container for simulator {simulator_version.database_id} failed.")
            elif wait_time == 30:
                raise RuntimeError(f"Container build for simulator {simulator_version.database_id} timed out.")
        job_monitor.internal_unsubscribe(hpc_run.slurmjobid)

    sim_slurmjobid = await simulation_service.submit_simulation_job(simulation=simulation, experiment_id=experiment_id)
    correlation_id = get_compose_correlation_id(random_string=random_string, job_type=ComposeJobType.SIMULATION)
    await hpc_db.insert_hpcrun(
        slurmjobid=sim_slurmjobid,
        job_type=ComposeJobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id=correlation_id,
    )
