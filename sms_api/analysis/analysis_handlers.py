"""
Simulation analysis handler for SMS API simulation experiment outputs.

NOTE: this module is essentially "analysis_handlers_hpc". TODO: abstract this into interface
"""

import asyncio
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import pandas as pd
from pydantic import BaseModel
from starlette.requests import Request

from sms_api.analysis import AnalysisService, AnalysisServiceFS, AnalysisServiceSlurm
from sms_api.analysis.analysis_service_local import AnalysisServiceLocal
from sms_api.analysis.analysis_utils import get_html_outputs_local
from sms_api.analysis.models import (
    AnalysisConfig,
    AnalysisDomain,
    AnalysisModuleConfig,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    JobStatus,
    OutputFile,
    OutputFileMetadata,
    PtoolsAnalysisConfig,
    TsvOutputFile,
)
from sms_api.common.ssh.ssh_service import SSHService, SSHServiceManaged
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import get_data_id, timestamp
from sms_api.config import Settings, get_settings, REPO_ROOT
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulatorVersion


class CacheQueryResult(BaseModel):
    exists: list[Path]
    missing: list[Path]


async def handle(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceLocal,
    logger: logging.Logger,
    _request: Request,
) -> Sequence[OutputFileMetadata | TsvOutputFile]:
    """
    Execute an analysis request.

    :param request:
    :param simulator:
    :param analysis_service:
    :param logger:
    :param _request:
    :return:
    """
    handler = handle_analysis_local
    return await handler(
        request=request,
        simulator=simulator,
        analysis_service=analysis_service,
        logger=logger,
        _request=_request
    )


async def handle_analysis_local(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceLocal,
    logger: logging.Logger,
    _request: Request,
) -> Sequence[TsvOutputFile]:
    analysis_name: str = (
        get_data_id(exp_id=request.experiment_id, scope="analysis")
        if request.analysis_name is None
        else request.analysis_name
    )
    expid = request.experiment_id
    requested_analyses = request.requested
    config = request.to_config(analysis_name=analysis_name)
    return await analysis_service.run_analysis(analysis_config=config, expid=expid, analysis_name=analysis_name, requested=requested_analyses)


async def handle_analysis_slurm(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceSlurm,
    logger: logging.Logger,
    db_service: DatabaseService,
    _request: Request,
) -> Sequence[OutputFileMetadata | TsvOutputFile]:
    analysis_name: str = (
        get_data_id(exp_id=request.experiment_id, scope="analysis")
        if request.analysis_name is None
        else request.analysis_name
    )
    analysis_cache: Path | None = get_analysis_cache(
        request=request, _request=_request, env=analysis_service.env, analysis_name=analysis_name
    )

    if analysis_cache is None:
        run, analysis_cache = await dispatch_new_analysis(
            request=request,
            _request=_request,
            analysis_name=analysis_name,
            simulator=simulator,
            analysis_service=analysis_service,
            logger=logger,
            db_service=db_service,
        )

    # check available
    available_paths: list[HPCFilePath] = await analysis_service.get_available_output_paths(analysis_name)

    # download available
    return await download_available(
        available_paths=available_paths,
        requested=request.requested,
        analysis_cache=analysis_cache,
        ssh=analysis_service.ssh,
        logger=logger,
    )


def create_analysis_cache(env: Settings, _request: Request, analysis_name: str) -> Path:
    # make cache dir for analysis
    cached_dir = Path(env.cache_dir) / _request.state.session_id / analysis_name
    if not cached_dir.exists():
        os.mkdir(cached_dir)
    return cached_dir


async def insert_analysis(
    db_service: DatabaseService, analysis_name: str, config: AnalysisConfig, job_name: str, job_id: int
):
    # insert new analysis
    return await db_service.insert_analysis(
        name=analysis_name,
        config=config,
        last_updated=timestamp(),
        job_name=job_name,
        job_id=job_id,
    )


# === AnalysisDispatch ===


async def dispatch_new_analysis(
    request: ExperimentAnalysisRequest,
    analysis_name: str,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceSlurm,
    logger: logging.Logger,
    db_service: DatabaseService,
    _request: Request,
) -> tuple[AnalysisRun, Path]:
    # dispatch slurm
    slurmjob_name, slurmjob_id, config = await analysis_service.dispatch_analysis(
        request=request, logger=logger, simulator_hash=simulator.git_commit_hash, analysis_name=analysis_name
    )

    # insert new analysis
    analysis_record = await insert_analysis(
        analysis_name=analysis_name, config=config, job_name=slurmjob_name, job_id=slurmjob_id, db_service=db_service
    )

    # poll
    await asyncio.sleep(1.111)
    run = await poll_status(analysis_record=analysis_record, db_service=db_service, analysis_service=analysis_service)

    # make cache dir for analysis
    cached_dir = create_analysis_cache(env=analysis_service.env, _request=_request, analysis_name=analysis_name)
    return run, cached_dir


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
    analysis_record: ExperimentAnalysisDTO, db_service: DatabaseService, analysis_service: AnalysisServiceSlurm
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


async def get_analysis_log(db_service: DatabaseService, id: int, ssh_service: SSHService) -> str:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurm_logfile = get_settings().slurm_log_base_path / f"{analysis_record.job_name}.out"
    ret, stdout, stdin = await ssh_service.run_command(f"cat {slurm_logfile!s}")
    return stdout


# === AnalysisStorage ===


def get_analysis_cache(
    request: ExperimentAnalysisRequest, env: Settings, analysis_name: str, _request: Request
) -> Path | None:
    """
    Gets the dirpath of the analysis:
        where:
            ``analysis_cache = <BASE_CACHE_DIR_ROOT> / <USER_CACHE_DIR_ROOT> / <ANALYSIS_NAME>``
        and
            ``analysis_result_download_location = analysis_cache``
    """
    cache_dir = Path(env.cache_dir) / _request.state.session_id / analysis_name
    return cache_dir if cache_dir.exists() else None


def find_relevant_files(requested_filename: str, available_paths: list[HPCFilePath]) -> list[HPCFilePath]:
    return [fp for fp in filter(lambda fpath: requested_filename in str(fpath.remote_path), available_paths)]


def verify_result(local_result_path: Path, expected_n_tp: int) -> bool:
    tsv_data = pd.read_csv(local_result_path, sep="\t")
    actual_cols = [col for col in tsv_data.columns if col.startswith("t")]
    return len(actual_cols) == expected_n_tp


# === AnalysisInfo ===


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


# === AnalysisOutputData ===


async def download_available(
    available_paths: list[HPCFilePath],
    requested: dict[str, list[AnalysisModuleConfig | PtoolsAnalysisConfig]],
    analysis_cache: Path,
    ssh: SSHServiceManaged,
    logger: logging.Logger,
) -> list[TsvOutputFile]:
    results: list[TsvOutputFile] = []
    if len(available_paths):
        # download requested available to cache and generate dto outputs
        for domain, configs in requested.items():
            for config in configs:
                requested_filename = f"{config.name}_{AnalysisDomain[domain.upper()]}.txt"
                relevant_files = find_relevant_files(requested_filename, available_paths)
                for remote_path in relevant_files:
                    # TODO: better save to cache
                    local = analysis_cache / requested_filename
                    if not local.exists():
                        await ssh.scp_download(local_file=local, remote_path=remote_path)
                    verification = verify_result(local, 5)
                    if not verification:
                        logger.info("WARNING: resulting num cols/tps do not match requested.")
                    file_content = local.read_text()
                    output = TsvOutputFile(filename=requested_filename, content=file_content)
                    results.append(output)
    return results


async def get_analysis_plots(db_service: DatabaseService, id: int, ssh_service: SSHServiceManaged) -> list[OutputFile]:
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    return await get_html_outputs_local(output_id=output_id, ssh_service=ssh_service)
