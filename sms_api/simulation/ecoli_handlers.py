import logging
import tempfile
from collections.abc import Generator
from pathlib import Path
from textwrap import dedent
from typing import Any

import fastapi
import orjson
import polars as pl
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse

from sms_api.common.gateway.utils import get_simulator
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.data.data_service import download_transforms, TransformData, SimulationOutputData
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    EcoliSimulationDTO,
    ExperimentRequest,
    JobStatus,
    SimulationConfig,
    SimulationRun,
    SimulatorVersion, ObservablesRequest, BaseModel,
)
from sms_api.simulation.simulation_service import SimulationService


async def run_simulation(
    sim_service: SimulationService,
    config: SimulationConfig,
    request: ExperimentRequest,
    logger: logging.Logger,
    db_service: DatabaseService,
    timestamp: str,
) -> EcoliSimulationDTO:
    simulator: SimulatorVersion = get_simulator()
    slurmjob_name, slurmjob_id = await sim_service.submit_experiment_job(
        config=config,
        simulation_name=request.simulation_name,
        simulator_hash=simulator.git_commit_hash,
        logger=logger,
    )
    simulation_record = await db_service.insert_ecoli_simulation(
        name=request.simulation_name,
        config=config,
        last_updated=timestamp,
        job_name=slurmjob_name,
        job_id=slurmjob_id,
        metadata=request.metadata,
    )
    return simulation_record


async def get_simulation(db_service: DatabaseService, id: int) -> EcoliSimulationDTO:
    return await db_service.get_ecoli_simulation(database_id=id)


async def get_simulation_status(db_service: DatabaseService, id: int, ssh_service: SSHService) -> SimulationRun:
    sim_record = await db_service.get_ecoli_simulation(database_id=id)
    slurmjob_id = sim_record.job_id
    # slurmjob_id = get_jobid_by_experiment(experiment_id)
    # ssh_service = get_ssh_service()
    slurm_user = get_settings().slurm_submit_user
    statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
    status: str = statuses[1].split("\n")[0].split()[-2]
    return SimulationRun(id=int(id), status=JobStatus[status])


async def list_simulations(db_service: DatabaseService) -> list[EcoliSimulationDTO]:
    return await db_service.list_ecoli_simulations()


# variant=0/lineage_seed=1/generation=3/agent_id=000
async def get_simulation_outputs(
    ssh: SSHService,
    bg_tasks: BackgroundTasks,
    db_service: DatabaseService,
    id: int,
    lineage_seed: int = 1,
    generation: int = 3,
    variant: int = 0,
    agent_id: str = "000",
    observables: ObservablesRequest = ObservablesRequest()
) -> SimulationOutputData:
    simulation = await db_service.get_ecoli_simulation(database_id=id)
    experiment_id = simulation.config.experiment_id
    # experiment_id = 'sms_multiseed_multigen'

    outputs: SimulationOutputData = await download_transforms(
        expid=experiment_id,
        remote_outdir_root=Path(str(get_settings().simulation_outdir)),
        variant=variant,
        lineage_seed=lineage_seed,
        generation=generation,
        agent_id=agent_id,
        observables=observables,
        bg_tasks=bg_tasks
    )

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

    # return StreamingResponse(generate(pl.read_parquet(local).to_dicts()), media_type="application/json")
    return outputs


async def get_simulation_data(
    ssh: SSHService,
    db_service: DatabaseService,
    id: int,
    lineage_seed: int,
    generation: int,
    variant: int,
    agent_id: int,
    observables: list[str],
    bg_tasks: BackgroundTasks,
) -> StreamingResponse:
    simulation = await db_service.get_ecoli_simulation(database_id=id)
    experiment_id = simulation.config.experiment_id
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
    remote = get_settings().simulation_outdir.parent / "data" / pq_filename
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

    return StreamingResponse(generate(pl.read_parquet(local).to_dicts()), media_type="application/json")


async def get_simulation_log(db_service: DatabaseService, ssh_service: SSHService, id: int) -> fastapi.Response:
    stdout = await _get_slurm_log(db_service, ssh_service, id)
    _, _, after = stdout.partition("N E X T F L O W")
    result = "N E X T F L O W" + after
    return fastapi.Response(content=result, media_type="text/plain")


async def get_simulation_log_detailed(db_service: DatabaseService, ssh_service: SSHService, id: int) -> str:
    return await _get_slurm_log(db_service=db_service, ssh_service=ssh_service, db_id=id)


async def _get_slurm_log(db_service: DatabaseService, ssh_service: SSHService, db_id: int) -> str:
    experiment = await db_service.get_ecoli_simulation(database_id=db_id)
    remote_log_path = f"{get_settings().slurm_log_base_path!s}/{experiment.job_name}"
    returncode, stdout, stderr = await ssh_service.run_command(f"cat {remote_log_path}.out")
    return stdout
