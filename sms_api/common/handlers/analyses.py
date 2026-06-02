"""
Simulation analysis handler for SMS API simulation experiment outputs.

NOTE: this module is essentially "analysis_handlers_hpc". TODO: abstract this into interface
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from textwrap import dedent

from starlette.requests import Request

from sms_api.analysis.analysis_service import (
    AnalysisServiceSlurm,
    RequestPayload,
    build_canonical_ptools_request,
    canonical_ptools_cache_dir,
    ptools_aggregation_mode,
    reaggregate_ptools_columns,
    should_eagerly_materialize_ptools,
)
from sms_api.analysis.models import (
    PTOOLS_CANONICAL_N_TP,
    AnalysisJobFailedException,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    OutputFile,
    OutputFileMetadata,
    PtoolsAnalysisConfig,
    TsvOutputFile,
)
from sms_api.common.models import SSHTarget
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.streaming import format_sse_event
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
    _request: Request | None = None,
) -> Sequence[OutputFileMetadata | TsvOutputFile]:
    # 1. check if hashed/cached payload exists.
    # Path B1: RequestPayload.hash() strips n_tp from every ptools module, so
    # re-requests with a different n_tp hit the cache from the SLURM run that
    # produced the canonical (n_tp=PTOOLS_CANONICAL_N_TP) artifact.
    payload_hash = RequestPayload(data=request.model_dump()).hash()
    analysis_request_cache = Path(analysis_service.env.cache_dir) / payload_hash
    analysis_name: str = get_data_id(scope="analysis")
    target_n_tp_by_module = _collect_target_n_tp(request)

    results: list[TsvOutputFile] = []
    # 2. if cache doesn't exist or is empty, run an analysis
    cache_has_files = analysis_request_cache.exists() and len([fp for fp in analysis_request_cache.iterdir()]) > 0
    if not cache_has_files:
        # 2a. mk local cache (use makedirs with exist_ok for empty directories)
        analysis_request_cache.mkdir(parents=True, exist_ok=True)
        # Use a single SSH session for job submission and polling
        async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
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

        # Fetch available output files from the analysis output directory
        # Analysis outputs are stored at: hpc_sim_base_path / experiment_id / "analyses"
        remote_analysis_outdir = HPCFilePath(remote_path=Path(config.analysis_options.outdir))  # type: ignore[attr-defined]
        available_paths: list[HPCFilePath] = await analysis_service.get_available_output_paths(
            remote_analysis_outdir=remote_analysis_outdir
        )

        # download available
        for remote_path in available_paths:
            output_i: TsvOutputFile = await analysis_service.download_analysis_output(
                local_dir=analysis_request_cache,
                remote_path=remote_path,
                target_n_tp_by_module=target_n_tp_by_module,
            )
            results.append(output_i)
    else:
        # Load cached results — filenames use the pattern: module_vX_sY_gZ.tsv.
        # Cached files are at canonical resolution; re-aggregate per requested n_tp.
        for fp in analysis_request_cache.iterdir():
            filename = fp.parts[-1]
            if filename.endswith(".tsv"):
                file_content = fp.read_text()
                metadata = _parse_cached_filename_metadata(filename)
                module_name = _module_name_from_cached_filename(filename)
                target_n_tp = target_n_tp_by_module.get(module_name)
                if target_n_tp is not None and target_n_tp != PTOOLS_CANONICAL_N_TP:
                    file_content = reaggregate_ptools_columns(
                        csv_text=file_content,
                        target_n_tp=target_n_tp,
                        source_n_tp=PTOOLS_CANONICAL_N_TP,
                        mode=ptools_aggregation_mode(module_name),
                    )
                output_i = TsvOutputFile(
                    filename=filename,
                    content=file_content,
                    variant=metadata.get("variant", 0),
                    lineage_seed=metadata.get("lineage_seed"),
                    generation=metadata.get("generation"),
                )
                results.append(output_i)

    return results


async def handle_run_analysis_sse(  # noqa: C901
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceSlurm,
    logger: logging.Logger,
    db_service: DatabaseService,
    poll_interval: float = 3.0,
) -> AsyncIterator[bytes]:
    """Path E — drive the same analysis pipeline as ``handle_run_analysis_slurm``
    but yield Server-Sent Events at each phase transition.

    Event sequence on success:
      ``received`` → (``cache-hit`` | ``dispatched`` → ``running`` * N → ``downloading``) →
      ``result`` (inline TsvOutputFile array) → ``end``.

    Event sequence on failure:
      ``received`` → (...) → ``error`` (``{error, message}``) → ``end``.

    All bytes are SSE-formatted: ``event: <name>\\ndata: <json>\\n\\n``. The
    ``result`` payload mirrors the synchronous endpoint's response body, so a
    UI that already knows how to consume the sync JSON can reuse its parser.
    """
    try:
        payload_hash = RequestPayload(data=request.model_dump()).hash()
        analysis_request_cache = Path(analysis_service.env.cache_dir) / payload_hash
        analysis_name: str = get_data_id(scope="analysis")
        target_n_tp_by_module = _collect_target_n_tp(request)
        results: list[TsvOutputFile] = []

        yield format_sse_event(
            "status",
            {"phase": "received", "experiment_id": request.experiment_id, "payload_hash": payload_hash},
        )

        cache_has_files = analysis_request_cache.exists() and any(analysis_request_cache.iterdir())
        if cache_has_files:
            yield format_sse_event("status", {"phase": "cache-hit"})
            for fp in analysis_request_cache.iterdir():
                filename = fp.parts[-1]
                if not filename.endswith(".tsv"):
                    continue
                file_content = fp.read_text()
                metadata = _parse_cached_filename_metadata(filename)
                module_name = _module_name_from_cached_filename(filename)
                target_n_tp = target_n_tp_by_module.get(module_name)
                if target_n_tp is not None and target_n_tp != PTOOLS_CANONICAL_N_TP:
                    file_content = reaggregate_ptools_columns(
                        csv_text=file_content,
                        target_n_tp=target_n_tp,
                        source_n_tp=PTOOLS_CANONICAL_N_TP,
                        mode=ptools_aggregation_mode(module_name),
                    )
                results.append(
                    TsvOutputFile(
                        filename=filename,
                        content=file_content,
                        variant=metadata.get("variant", 0),
                        lineage_seed=metadata.get("lineage_seed"),
                        generation=metadata.get("generation"),
                    )
                )
        else:
            analysis_request_cache.mkdir(parents=True, exist_ok=True)
            async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
                jobname, jobid, config = await analysis_service.dispatch_analysis(
                    request=request,
                    logger=logger,
                    analysis_name=analysis_name,
                    ssh=ssh,
                    simulator_hash=simulator.git_commit_hash,
                )
                yield format_sse_event(
                    "status",
                    {"phase": "dispatched", "job_id": jobid, "job_name": jobname},
                )
                dto: ExperimentAnalysisDTO = await db_service.insert_analysis(
                    name=analysis_name,
                    config=config,
                    last_updated=timestamp(),
                    job_name=jobname,
                    job_id=jobid,
                )
                # Inline the poll loop so we can yield per-iteration status events.
                # Mirrors AnalysisServiceSlurm.poll_status (analysis_service.py:327)
                # but is interrupted by SSE emissions between status fetches.
                if dto.job_id is None:
                    raise ValueError("No job id associated with the analysis record")  # noqa: TRY301
                run: AnalysisRun = await analysis_service.get_analysis_status(
                    job_id=dto.job_id, db_id=dto.database_id, ssh=ssh
                )
                while run.status.lower() not in ("completed", "failed"):
                    yield format_sse_event("status", {"phase": "running", "slurm_status": run.status})
                    await asyncio.sleep(poll_interval)
                    run = await analysis_service.get_analysis_status(job_id=dto.job_id, db_id=dto.database_id, ssh=ssh)
                if run.status.lower() == "failed":
                    error_log = await analysis_service._fetch_job_log(job_name=dto.job_name, ssh=ssh)
                    run.error_log = error_log
                    raise AnalysisJobFailedException(run=run)  # noqa: TRY301

            yield format_sse_event("status", {"phase": "downloading"})
            remote_analysis_outdir = HPCFilePath(remote_path=Path(config.analysis_options.outdir))  # type: ignore[attr-defined]
            available_paths: list[HPCFilePath] = await analysis_service.get_available_output_paths(
                remote_analysis_outdir=remote_analysis_outdir
            )
            for remote_path in available_paths:
                output_i: TsvOutputFile = await analysis_service.download_analysis_output(
                    local_dir=analysis_request_cache,
                    remote_path=remote_path,
                    target_n_tp_by_module=target_n_tp_by_module,
                )
                results.append(output_i)

        yield format_sse_event("result", results)
        yield format_sse_event("end", {})
    except AnalysisJobFailedException as exc:
        # Build the error payload from to_dict() but force the exception type into ``error``
        # so SSE consumers can branch on a stable Python-side discriminator.
        payload = exc.to_dict()
        payload["error"] = "AnalysisJobFailedException"
        yield format_sse_event("error", payload)
        yield format_sse_event("end", {})
    except Exception as exc:
        logger.exception("SSE analysis run failed")
        yield format_sse_event(
            "error",
            {"error": type(exc).__name__, "message": str(exc)},
        )
        yield format_sse_event("end", {})


_PTOOLS_DOMAINS = ("single", "multidaughter", "multigeneration", "multiseed")


def _collect_target_n_tp(request: ExperimentAnalysisRequest) -> dict[str, int]:
    """Build a ``{module_name: requested_n_tp}`` map across all ptools domains in the request.

    If the same module name appears in multiple domains with different n_tp values,
    the last one wins. In practice, ptools requests stick to one domain per module.
    """
    target: dict[str, int] = {}
    for domain in _PTOOLS_DOMAINS:
        modules = getattr(request, domain, None)
        if not modules:
            continue
        for module in modules:
            if isinstance(module, PtoolsAnalysisConfig):
                target[module.name] = module.n_tp
    return target


def _module_name_from_cached_filename(filename: str) -> str:
    """Strip the partition suffix (_vX_sY_gZ) and the file extension to recover the module name."""
    stem = Path(filename).stem
    return _CACHED_PARTITION_SUFFIX_RE.sub("", stem)


_CACHED_PARTITION_SUFFIX_RE = re.compile(r"_v\d+(?:_s\d+)?(?:_g\d+)?$")


# Regex for cached filename metadata: module_vX_sY_gZ.tsv
_CACHED_META_RE = re.compile(r"_v(\d+)(?:_s(\d+))?(?:_g(\d+))?(?:\.\w+)$")


def _parse_cached_filename_metadata(filename: str) -> dict[str, int]:
    """Parse variant/lineage_seed/generation from cached filenames like ptools_rna_v0_s0_g5.tsv."""
    metadata: dict[str, int] = {}
    m = _CACHED_META_RE.search(filename)
    if m:
        metadata["variant"] = int(m.group(1))
        if m.group(2) is not None:
            metadata["lineage_seed"] = int(m.group(2))
        if m.group(3) is not None:
            metadata["generation"] = int(m.group(3))
    return metadata


# Tracks in-flight Path-D background tasks to avoid double-dispatching when
# get_simulation_status() is polled rapidly across the completion transition.
# Keyed by experiment_id; entry is removed when the materialization task ends.
_inflight_materialize_tasks: dict[str, asyncio.Task[object]] = {}


def schedule_canonical_ptools_materialization(
    experiment_id: str,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceSlurm,
    db_service: DatabaseService,
    parent_logger: logging.Logger,
) -> asyncio.Task[object] | None:
    """Path D — fire-and-forget pre-warm of the canonical ptools cache.

    Called at the moment a simulation transitions to COMPLETED. Returns:
      * ``None`` if the deployment/simulator combo is not eligible (non-RKE, non-fork).
      * ``None`` if the canonical cache for this experiment is already populated.
      * ``None`` if a materialization for this experiment is already in flight.
      * Otherwise, the scheduled ``asyncio.Task`` (returned mainly for tests).

    The task runs ``handle_run_analysis_slurm`` against a canonical-resolution
    request; that handler dispatches SLURM, polls, and downloads outputs into
    the analysis cache directory. By the time a user-facing
    ``POST /api/v1/analyses`` request lands, the cache is already populated and
    the response is served without dispatching a fresh job.
    """
    if not should_eagerly_materialize_ptools(simulator, analysis_service.env):
        return None

    cache_dir = canonical_ptools_cache_dir(env=analysis_service.env, experiment_id=experiment_id)
    if cache_dir.exists() and any(cache_dir.iterdir()):
        return None

    if experiment_id in _inflight_materialize_tasks:
        return None

    request = build_canonical_ptools_request(experiment_id=experiment_id)
    coro = handle_run_analysis_slurm(
        request=request,
        simulator=simulator,
        analysis_service=analysis_service,
        logger=parent_logger,
        db_service=db_service,
        _request=None,
    )
    task: asyncio.Task[object] = asyncio.create_task(coro, name=f"ptools-materialize-{experiment_id}")
    _inflight_materialize_tasks[experiment_id] = task

    def _on_done(t: asyncio.Task[object], *, _eid: str = experiment_id) -> None:
        _inflight_materialize_tasks.pop(_eid, None)
        exc = t.exception() if not t.cancelled() else None
        if exc is not None:
            parent_logger.warning(
                "Path D ptools materialization failed for experiment %s: %s: %s",
                _eid,
                type(exc).__name__,
                exc,
            )
        else:
            parent_logger.info("Path D ptools materialization completed for experiment %s", _eid)

    task.add_done_callback(_on_done)
    return task


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
    async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
        return await analysis_service.get_analysis_status(
            job_id=analysis_record.job_id, db_id=analysis_record.database_id, ssh=ssh
        )


async def handle_get_analysis_log(db_service: DatabaseService, id: int) -> str:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurm_logfile = get_settings().slurm_log_base_path / f"{analysis_record.job_name}.out"

    async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
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

    async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
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
