import asyncio
import logging
import os
from pathlib import Path
from types import ModuleType

import pandas as pd
from pydantic import BaseModel
from starlette.requests import Request

from sms_api.common.ssh.ssh_service import SSHService, SSHServiceManaged
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import get_data_id
from sms_api.config import REPO_ROOT, Settings, get_settings
from sms_api.data.analysis_service import AnalysisService, AnalysisServiceHpc
from sms_api.data.analysis_utils import get_html_outputs_local
from sms_api.data.models import (
    AnalysisDomain,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    JobStatus,
    OutputFile,
    OutputFileMetadata,
    TsvOutputFile,
    TsvOutputFileRequest,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulatorVersion


class CacheQueryResult(BaseModel):
    exists: list[Path]
    missing: list[Path]


async def handle_analysis(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceHpc,
    logger: logging.Logger,
    db_service: DatabaseService,
    timestamp: str,
    _request: Request,
) -> list[OutputFileMetadata | TsvOutputFile]:
    # TODO: use request, _request, and analysis_service.env to dynamically generate requested filepaths
    # TODO: if above check returns true, SKIP DIRECTLY TO DOWNLOAD BLOCK
    analysis_name: str = (
        get_data_id(exp_id=request.experiment_id, scope="analysis")
        if request.analysis_name is None
        else request.analysis_name
    )
    # get_uuid(scope="analysis")

    # dispatch slurm
    slurmjob_name, slurmjob_id, config = await analysis_service.dispatch_analysis(
        request=request, logger=logger, simulator_hash=simulator.git_commit_hash, analysis_name=analysis_name
    )

    # insert new analysis
    analysis_record = await db_service.insert_analysis(
        name=analysis_name,
        config=config,
        last_updated=timestamp,
        job_name=slurmjob_name,
        job_id=slurmjob_id,
    )

    # poll
    await asyncio.sleep(1.111)
    _ = await poll_status(analysis_record=analysis_record, db_service=db_service, analysis_service=analysis_service)

    # check available
    available_paths: list[HPCFilePath] = await analysis_service.available_output_filepaths(analysis_name)

    # download requested available to cache and generate dto outputs
    results: list[TsvOutputFile] = []
    for domain, configs in request.requested.items():
        for config in configs:
            requested_filename = f"{config.name}_{AnalysisDomain[domain.upper()]}.txt"
            relevant_files = find_relevant_files(requested_filename, available_paths)

            for remote_path in relevant_files:
                # TODO: better save to cache
                cached_dir = Path(analysis_service.env.cache_dir) / _request.state.session_id / analysis_name
                # cached_dir = Path(analysis_service.env.cache_dir) / analysis_name
                if not cached_dir.exists():
                    os.mkdir(cached_dir)
                local = cached_dir / requested_filename
                if not local.exists():
                    await analysis_service.ssh.scp_download(local_file=local, remote_path=remote_path)

                verification = verify_result(local, 5)
                if not verification:
                    logger.info("WARNING: resulting num cols/tps do not match requested.")
                file_content = local.read_text()
                output = TsvOutputFile(filename=requested_filename, content=file_content)
                results.append(output)

    return results


def check_analysis_cache(
    request: ExperimentAnalysisRequest,
    analysis_service: AnalysisService,
    analysis_name: str,
    _request: Request
) -> CacheQueryResult | Path:
    exists = []
    missing = []
    for domain, configs in request.requested.items():
        for config in configs:
            requested_filename = f"{config.name}_{AnalysisDomain[domain.upper()]}.txt"
            # TODO: better save to cache
            cached_dir = Path(analysis_service.env.cache_dir) / _request.state.session_id / analysis_name
            # cached_dir = Path(analysis_service.env.cache_dir) / analysis_name
            if not cached_dir.exists():
                cached_dir.mkdir()
                return cached_dir
            local = cached_dir / requested_filename
            exists.append(local) if local.exists() else missing.append(local)

    return CacheQueryResult(
        exists=exists, missing=missing
    )


def verify_result(local_result_path: Path, expected_n_tp: int) -> bool:
    tsv_data = pd.read_csv(local_result_path, sep="\t")
    actual_cols = [col for col in tsv_data.columns if col.startswith("t")]
    return len(actual_cols) == expected_n_tp


async def get_analysis_status(
    ref: int | ExperimentAnalysisDTO,
    db_service: DatabaseService,
    analysis_service: AnalysisService,
) -> AnalysisRun:
    """
    If a database_id is passed, an analysis record should NOT Be
    :param ref: (``int<ExperimentAnalysisDTO.database_id> | ExperimentAnalysisDTO>``) One of an instance of
        objects stored and read in the "analyses" db table, OR the database_id of such an aforementioned
        instance. **_NOTE: really, the <POST>/analyses endpoint should pass the DTO to this param, and the
        modular status/other endpoints should pass the db id.
    :param db_service:
    :param analysis_service:
    :return:
    """
    analysis_record: ExperimentAnalysisDTO = (
        await db_service.get_analysis(database_id=ref) if isinstance(ref, int) else ref
    )
    slurmjob_id = analysis_record.job_id
    slurm_user = analysis_service.env.slurm_submit_user
    ssh_service = analysis_service.ssh
    if not ssh_service.connected:
        await ssh_service.connect()

    try:
        statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
    except Exception:
        statuses = await ssh_service.run_command(f"sacct -j {slurmjob_id}")
    finally:
        status: str = statuses[1].split("\n")[0].split()[-2]
    return AnalysisRun(id=analysis_record.database_id, status=JobStatus[status])


async def poll_status(
    analysis_record: ExperimentAnalysisDTO, db_service: DatabaseService, analysis_service: AnalysisServiceHpc
) -> AnalysisRun:
    await asyncio.sleep(3)
    run = await get_analysis_status(
        ref=analysis_record,
        db_service=db_service,
        analysis_service=analysis_service,
    )
    while run.status.lower() not in ["completed", "failed"]:
        await asyncio.sleep(3)
        run = await get_analysis_status(
            ref=analysis_record,
            db_service=db_service,
            analysis_service=analysis_service,
        )
    if run.status.lower() == "failed":
        raise Exception(f"Analysis Run has failed:\n{run}")
    return run


async def get_analysis(db_service: DatabaseService, id: int) -> ExperimentAnalysisDTO:
    return await db_service.get_analysis(database_id=id)


async def list_analyses(db_service: DatabaseService) -> list[ExperimentAnalysisDTO]:
    return await db_service.list_analyses()


async def get_ptools_manifest(
    db_service: DatabaseService, env: Settings, ssh_service: SSHService, id: int, analysis_service: ModuleType
) -> list[TsvOutputFile]:
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    return await analysis_service.get_tsv_manifest_local(output_id=output_id, ssh_service=ssh_service)  # type: ignore[no-any-return]


async def get_tsv_output(
    request: TsvOutputFileRequest,
    db_service: DatabaseService,
    id: int,
    ssh: SSHServiceManaged,
) -> TsvOutputFile:
    if not ssh.connected:
        await ssh.connect()

    variant_id = request.variant
    lineage_seed_id = request.lineage_seed
    generation_id = request.generation
    agent_id = request.agent_id
    filename = request.filename
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    fp = (
        get_settings().simulation_outdir
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

    filepath: HPCFilePath = fp / filename

    # tmpdir = "/tmp"
    cache_dir = f"{REPO_ROOT}/.results_cache"
    local = Path(cache_dir) / filename
    if not local.exists():
        print(f"{local!s} does not yet exist!")
        if not ssh.connected:
            await ssh.connect()
        try:
            await ssh.scp_download(local_file=local, remote_path=filepath)
        except Exception:
            print(f"There was an issue downloading {filepath!s} to {local!s}")

    file_content = local.read_text()
    return TsvOutputFile(
        filename=filename,
        variant=variant_id,
        lineage_seed=lineage_seed_id,
        generation=generation_id,
        agent_id=agent_id,
        content=file_content,
    )


async def get_analysis_log(db_service: DatabaseService, id: int, ssh_service: SSHService) -> str:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurm_logfile = get_settings().slurm_log_base_path / f"{analysis_record.job_name}.out"
    ret, stdout, stdin = await ssh_service.run_command(f"cat {slurm_logfile!s}")
    return stdout


async def get_analysis_plots(db_service: DatabaseService, id: int, ssh_service: SSHServiceManaged) -> list[OutputFile]:
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    return await get_html_outputs_local(output_id=output_id, ssh_service=ssh_service)


def find_relevant_files(requested_filename: str, available_paths: list[HPCFilePath]) -> list[HPCFilePath]:
    return [fp for fp in filter(lambda fpath: requested_filename in str(fpath.remote_path), available_paths)]
