import logging
import random
import string
import tempfile
from collections.abc import Generator
from pathlib import Path
from textwrap import dedent
from typing import Any

import fastapi
import orjson
import polars as pl
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import get_settings
from sms_api.dependencies import get_database_service, get_simulation_service, get_ssh_session_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import get_correlation_id
from sms_api.simulation.models import (
    JobStatus,
    JobType,
    ParcaDataset,
    ParcaDatasetRequest,
    Simulation,
    SimulationRequest,
    SimulationRun,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationService

logger = logging.getLogger(__name__)


async def run_parca(
    simulator: SimulatorVersion,
    simulation_service_slurm: SimulationService | None = None,
    database_service: DatabaseService | None = None,
    parca_config: dict[str, int | float | str] | None = None,
) -> ParcaDataset:
    if not simulation_service_slurm:
        simulation_service_slurm = get_simulation_service()
    if simulation_service_slurm is None:
        logger.exception("Simulation service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation service is not initialized")
    if not database_service:
        database_service = get_database_service()
    if database_service is None:
        logger.exception("Simulation database service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation database service is not initialized")

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=parca_config or {})
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    # Submit parca job
    parca_slurmjobid = await simulation_service_slurm.submit_parca_job(parca_dataset=parca_dataset)
    _hpc_run = await database_service.insert_hpcrun(
        slurmjobid=parca_slurmjobid,
        job_type=JobType.PARCA,
        ref_id=parca_dataset.database_id,
        correlation_id="N/A",
    )

    return parca_dataset


async def get_parca_datasets(
    simulation_service_slurm: SimulationService | None = None,
    database_service: DatabaseService | None = None,
) -> list[ParcaDataset]:
    if not simulation_service_slurm:
        simulation_service_slurm = get_simulation_service()
    if simulation_service_slurm is None:
        logger.exception("Simulation service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation service is not initialized")
    if not database_service:
        database_service = get_database_service()
    if database_service is None:
        logger.exception("Simulation database service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation database service is not initialized")

    parca_datasets = await database_service.list_parca_datasets()
    return parca_datasets


async def run_simulation(
    database_service: DatabaseService,
    request: SimulationRequest,
    sim_service: SimulationService,
) -> Simulation:
    simulator = await database_service.get_simulator(simulator_id=request.simulator_id)
    parca_dataset = await database_service.get_parca_dataset(parca_dataset_id=request.parca_dataset_id)
    if simulator is None and parca_dataset is None:
        raise ValueError(f"Simulator {request.simulator_id} and Parca {request.parca_dataset_id} not found.")
    config = request.experiment.to_config(
        simulator_hash=simulator.git_commit_hash, parca_dataset_id=parca_dataset.database_id
    )
    if config.experiment_id is None:
        raise HTTPException(status_code=400, detail="Experiment ID is required")

    simulation = await database_service.insert_simulation(sim_request=request, config=config)

    # dispatch and insert hpc job
    random_string_7_hex = "".join(random.choices(string.hexdigits, k=7))
    correlation_id = get_correlation_id(
        ecoli_simulation=simulation, random_string=random_string_7_hex, simulator=simulator
    )

    slurmjob_id = await sim_service.submit_ecoli_simulation_job(
        ecoli_simulation=simulation, database_service=database_service, correlation_id=correlation_id
    )
    _ = await database_service.insert_hpcrun(
        slurmjobid=slurmjob_id,
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id=correlation_id,
    )

    simulation.job_id = slurmjob_id
    return simulation


async def get_simulation(db_service: DatabaseService, id: int) -> Simulation:
    return await db_service.get_simulation(simulation_id=id)


async def get_simulation_status(db_service: DatabaseService, id: int) -> SimulationRun:
    sim_record = await db_service.get_simulation(simulation_id=id)
    slurmjob_id = sim_record.job_id
    if slurmjob_id is None:
        raise RuntimeError(f"Not yet dispatched!: {sim_record}")
    slurm_user = get_settings().slurm_submit_user

    async with get_ssh_session_service().session() as ssh:
        statuses = await ssh.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")

    status: str = statuses[1].split("\n")[0].split()[-2]
    return SimulationRun(id=int(id), status=JobStatus[status])


async def list_simulations(db_service: DatabaseService) -> list[Simulation]:
    return await db_service.list_simulations()


async def get_simulation_data(
    db_service: DatabaseService,
    id: int,
    lineage_seed: int,
    generation: int,
    variant: int,
    agent_id: int,
    observables: list[str],
    bg_tasks: fastapi.BackgroundTasks,
) -> fastapi.responses.StreamingResponse:
    simulation = await db_service.get_ecoli_simulation(database_id=id)
    experiment_id = simulation.config.experiment_id
    ssh_session_service = get_ssh_session_service()

    # first, slice parquet and write temp pq to remote disk
    remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
    async with ssh_session_service.session() as ssh:
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
        remote = get_settings().simulation_outdir.parent / "data" / pq_filename
        await ssh.scp_download(local_file=local, remote_path=remote)

    # Schedule cleanup of remote file in background
    async def cleanup_remote_file() -> None:
        async with ssh_session_service.session() as ssh:
            await ssh.run_command(f"rm {remote!s}")

    bg_tasks.add_task(cleanup_remote_file)

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

    return StreamingResponse(generate(pl.read_parquet(local).to_dicts()), media_type="application/json")


async def get_simulation_log(db_service: DatabaseService, id: int) -> fastapi.Response:
    stdout = await _get_slurm_log(db_service, id)
    _, _, after = stdout.partition("N E X T F L O W")
    result = "N E X T F L O W" + after
    return fastapi.Response(content=result, media_type="text/plain")


async def get_simulation_log_detailed(db_service: DatabaseService, id: int) -> str:
    return await _get_slurm_log(db_service=db_service, db_id=id)


async def _get_slurm_log(remote_log_path: HPCFilePath) -> str | None:
    async with get_ssh_session_service().session() as ssh:
        returncode, stdout, stderr = await ssh.run_command(f"cat {remote_log_path!s}.out")
    return stdout
