"""
Simulation analysis handler for SMS API simulation experiment outputs.

NOTE: this module is essentially "analysis_handlers_hpc". TODO: abstract this into interface
"""

import json
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from textwrap import dedent

from starlette.requests import Request

from sms_api.analysis.analysis_service import AnalysisServiceSlurm, RequestPayload
from sms_api.analysis.models import (
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    OutputFile,
    OutputFileMetadata,
    TsvOutputFile,
)
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import get_data_id, timestamp
from sms_api.config import get_settings
from sms_api.dependencies import get_ssh_session_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulatorVersion


async def handle_run_analysis(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceSlurm,
    db_service: DatabaseService,
    logger: logging.Logger,
    _request: Request,
) -> Sequence[OutputFileMetadata | TsvOutputFile]:
    """
    Execute an analysis request.
    """
    return await handle_run_analysis_slurm(
        request=request,
        simulator=simulator,
        analysis_service=analysis_service,
        logger=logger,
        _request=_request,
        db_service=db_service,
    )


async def handle_run_analysis_slurm(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceSlurm,
    logger: logging.Logger,
    db_service: DatabaseService,
    _request: Request,
) -> Sequence[OutputFileMetadata | TsvOutputFile]:
    # 1. check if hashed/cached payload exists
    payload_hash = RequestPayload(data=request.model_dump()).hash()
    analysis_request_cache = Path(analysis_service.env.cache_dir) / payload_hash
    analysis_name: str = get_data_id(scope="analysis")

    results: list[TsvOutputFile] = []
    # 2. if not, run an analysis
    if not analysis_request_cache.exists():
        # 2a. mk local cache
        os.mkdir(analysis_request_cache)
        # Use a single SSH session for job submission and polling
        async with get_ssh_session_service().session() as ssh:
            # 2c. dispatch job
            jobname, jobid, config = await analysis_service.dispatch_analysis(
                request=request,
                logger=logger,
                analysis_name=analysis_name,
                ssh=ssh,
                simulator_hash=simulator.git_commit_hash,
            )
            # 2d. insert analysis into db
            dto: ExperimentAnalysisDTO = await db_service.insert_analysis(
                name=analysis_name,
                config=config,
                last_updated=timestamp(),
                job_name=jobname,
                job_id=jobid,
            )
            # 2e. poll status
            _run = await analysis_service.poll_status(dto=dto, ssh=ssh)
        # check available in specified HPC dir for analysis_config.outdir
        available_paths: list[HPCFilePath] = []
        # available_paths: list[HPCFilePath] = await analysis_service.get_available_output_paths(
        #     remote_analysis_outdir=HPCFilePath(remote_path=Path(config.analysis_options.outdir))
        # )

        # download available
        for remote_path in available_paths:
            output_i: TsvOutputFile = await analysis_service.download_analysis_output(
                local_dir=analysis_request_cache, remote_path=remote_path
            )
            results.append(output_i)
    else:
        # config = request.to_config(analysis_name=analysis_name, env=analysis_service.env)
        for fp in analysis_request_cache.iterdir():
            filename = fp.parts[-1]
            if filename.endswith(".txt"):
                file_content = fp.read_text()
                output_i = TsvOutputFile(filename=filename, content=file_content)
                results.append(output_i)

    return results


async def handle_get_analysis_status(
    ref: int | ExperimentAnalysisDTO,
    analysis_service: AnalysisServiceSlurm,
    db_service: DatabaseService,
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
    if analysis_record.job_id is None:
        raise ValueError("Analysis record has no job_id")
    async with get_ssh_session_service().session() as ssh:
        return await analysis_service.get_analysis_status(
            job_id=analysis_record.job_id, db_id=analysis_record.database_id, ssh=ssh
        )


async def handle_get_analysis_log(db_service: DatabaseService, id: int) -> str:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurm_logfile = get_settings().slurm_log_base_path / f"{analysis_record.job_name}.out"

    async with get_ssh_session_service().session() as ssh:
        ret, stdout, stdin = await ssh.run_command(f"cat {slurm_logfile!s}")

    return stdout


async def handle_get_analysis(db_service: DatabaseService, id: int) -> ExperimentAnalysisDTO:
    return await db_service.get_analysis(database_id=id)


async def handle_list_analyses(db_service: DatabaseService) -> list[ExperimentAnalysisDTO]:
    return await db_service.list_analyses()


async def handle_get_analysis_plots(db_service: DatabaseService, id: int) -> list[OutputFile]:
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    return await get_html_outputs_local(output_id=output_id)


async def get_html_outputs_local(output_id: str) -> list[OutputFile]:
    """Run in DEV"""
    settings = get_settings()
    slurm_base = settings.slurm_base_path
    remote_uv_executable = slurm_base / ".local" / "bin" / "uv"
    workspace_dir = slurm_base / "workspace"

    async with get_ssh_session_service().session() as ssh:
        ret, stdin, stdout = await ssh.run_command(
            dedent(f"""
                    cd {workspace_dir} \
                        && {remote_uv_executable} run scripts/html_outputs.py --output_id {output_id}
                """)
        )

    deserialized = json.loads(stdin.replace("'", '"'))
    outputs = []
    for spec in deserialized:
        output = OutputFile(name=spec["name"], content=spec["content"])
        outputs.append(output)
    return outputs
