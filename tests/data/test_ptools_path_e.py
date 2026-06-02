"""Tests for Path E: SSE streaming of the analysis run.

Covers the event sequence emitted by ``handle_run_analysis_sse``:
- Cold path: ``received`` → ``dispatched`` → ``running`` x N → ``downloading`` → ``result`` → ``end``.
- Cache hit:  ``received`` → ``cache-hit`` → ``result`` → ``end``.
- Failure:    ``received`` → (...) → ``error`` → ``end``.

All HPC / SSH / DB calls are mocked. We exercise the generator directly
to avoid spinning up FastAPI for what is fundamentally a coroutine-shaping test.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sms_api.analysis.models import (
    AnalysisConfig,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    PtoolsAnalysisConfig,
    PtoolsAnalysisType,
    TsvOutputFile,
)
from sms_api.common.handlers.analyses import handle_run_analysis_sse
from sms_api.common.models import JobStatus
from sms_api.config import Settings
from sms_api.simulation.models import SimulatorVersion


def _simulator() -> SimulatorVersion:
    return SimulatorVersion(
        database_id=1,
        git_commit_hash="abc1234",
        git_repo_url="https://github.com/vivarium-collective/vEcoli",
        git_branch="api-support",
        created_at=datetime.datetime(2026, 6, 1),
    )


def _request() -> ExperimentAnalysisRequest:
    return ExperimentAnalysisRequest(
        experiment_id="exp-e-1",
        single=[
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA.value, n_tp=8),
        ],
    )


def _parse_sse_events(raw: bytes) -> list[tuple[str, Any]]:
    """Split an SSE byte stream into a list of (event_name, data_payload) tuples."""
    out: list[tuple[str, Any]] = []
    for block in raw.split(b"\n\n"):
        if not block.strip():
            continue
        text = block.decode("utf-8")
        name = ""
        data = ""
        for line in text.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: ") :]
            elif line.startswith("data: "):
                data = line[len("data: ") :]
        out.append((name, json.loads(data) if data else None))
    return out


async def _collect(gen) -> bytes:  # type: ignore[no-untyped-def]
    return b"".join([chunk async for chunk in gen])


def _service(tmp_path: Path) -> Any:
    """Build a minimal AnalysisServiceSlurm-shaped mock anchored at tmp_path for cache_dir."""
    from sms_api.analysis.analysis_service import AnalysisServiceSlurm

    settings = Settings(deployment_namespace="sms-api-rke", cache_dir=str(tmp_path))
    service = AnalysisServiceSlurm(env=settings)
    return service


# ---- cache hit --------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_cache_hit_emits_received_cachehit_result_end(tmp_path: Path) -> None:
    from sms_api.analysis.analysis_service import RequestPayload

    request = _request()
    settings = Settings(deployment_namespace="sms-api-rke", cache_dir=str(tmp_path))
    payload_hash = RequestPayload(data=request.model_dump()).hash()
    cache_dir = Path(settings.cache_dir) / payload_hash
    cache_dir.mkdir(parents=True)
    (cache_dir / "ptools_rna_v0_s0_g0.tsv").write_text("idx\tt0\nrow1\t0.5\n")

    db_service = MagicMock()
    service = _service(tmp_path)

    raw = await _collect(
        handle_run_analysis_sse(
            request=request,
            simulator=_simulator(),
            analysis_service=service,
            logger=logging.getLogger("test"),
            db_service=db_service,
            poll_interval=0.0,
        )
    )
    events = _parse_sse_events(raw)
    names = [e[0] for e in events]
    assert names[0] == "status" and events[0][1]["phase"] == "received"
    assert names[1] == "status" and events[1][1]["phase"] == "cache-hit"
    assert names[-2] == "result"
    assert names[-1] == "end"
    # Result event carries inline TsvOutputFile array.
    result_payload = next(p for n, p in events if n == "result")
    assert isinstance(result_payload, list)
    assert result_payload[0]["filename"] == "ptools_rna_v0_s0_g0.tsv"


# ---- cold path with mocked HPC ----------------------------------------


@pytest.mark.asyncio
async def test_sse_cold_path_emits_full_event_sequence(tmp_path: Path) -> None:
    request = _request()
    service = _service(tmp_path)
    db_service = MagicMock()
    db_service.insert_analysis = AsyncMock(
        return_value=ExperimentAnalysisDTO(
            database_id=99,
            name="ana-99",
            job_id=12345,
            job_name="ana-job-99",
            last_updated="2026-06-02T12:00:00",
            config=AnalysisConfig.model_validate({
                "analysis_options": {"experiment_id": ["exp-e-1"], "outdir": "/remote/analyses/ana-99"}
            }),
        )
    )

    # Simulate one running iteration then completed.
    status_results = [
        AnalysisRun(id=99, status=JobStatus.RUNNING, job_id=12345),
        AnalysisRun(id=99, status=JobStatus.COMPLETED, job_id=12345),
    ]
    status_calls = iter(status_results)

    async def _get_analysis_status(**kw: Any) -> AnalysisRun:
        return next(status_calls)

    async def _dispatch(**kw: Any) -> tuple[str, int, MagicMock]:
        config = MagicMock()
        config.analysis_options.outdir = "/remote/analyses/ana-99"
        return ("ana-job-99", 12345, config)

    async def _avail_paths(**kw: Any) -> list[Any]:
        from sms_api.common.storage.file_paths import HPCFilePath

        return [HPCFilePath(remote_path=Path("/remote/analyses/ana-99/ptools_rna.tsv"))]

    async def _download(**kw: Any) -> TsvOutputFile:
        return TsvOutputFile(filename="ptools_rna.tsv", content="idx\tt0\nrow1\t0.5\n", variant=0)

    # Patch the service methods + the SSH session context manager.
    service.dispatch_analysis = AsyncMock(side_effect=_dispatch)
    service.get_analysis_status = AsyncMock(side_effect=_get_analysis_status)
    service.get_available_output_paths = AsyncMock(side_effect=_avail_paths)
    service.download_analysis_output = AsyncMock(side_effect=_download)

    class _FakeSession:
        async def __aenter__(self) -> Any:
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

    class _FakeSvc:
        def session(self) -> _FakeSession:
            return _FakeSession()

    with patch("sms_api.common.handlers.analyses.get_ssh_session_service", return_value=_FakeSvc()):
        raw = await _collect(
            handle_run_analysis_sse(
                request=request,
                simulator=_simulator(),
                analysis_service=service,
                logger=logging.getLogger("test"),
                db_service=db_service,
                poll_interval=0.0,
            )
        )

    events = _parse_sse_events(raw)
    names = [e[0] for e in events]
    phases = [e[1].get("phase") for e in events if e[0] == "status"]

    assert "received" in phases
    assert "dispatched" in phases
    assert "running" in phases
    assert "downloading" in phases
    assert names.count("result") == 1
    assert names[-1] == "end"
    # dispatched event carries job_id + job_name
    dispatched = next(e[1] for e in events if e[1] and e[1].get("phase") == "dispatched")
    assert dispatched["job_id"] == 12345
    assert dispatched["job_name"] == "ana-job-99"


# ---- failure -----------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_failure_path_emits_error_then_end(tmp_path: Path) -> None:
    request = _request()
    service = _service(tmp_path)
    db_service = MagicMock()
    db_service.insert_analysis = AsyncMock(
        return_value=ExperimentAnalysisDTO(
            database_id=99,
            name="ana-99",
            job_id=12345,
            job_name="ana-job-99",
            last_updated="2026-06-02T12:00:00",
            config=AnalysisConfig.model_validate({
                "analysis_options": {"experiment_id": ["exp-e-1"], "outdir": "/remote/analyses/ana-99"}
            }),
        )
    )

    failed_run = AnalysisRun(id=99, status=JobStatus.FAILED, job_id=12345, error_log="boom in vEcoli")

    async def _dispatch(**kw: Any) -> tuple[str, int, MagicMock]:
        config = MagicMock()
        config.analysis_options.outdir = "/remote/analyses/ana-99"
        return ("ana-job-99", 12345, config)

    async def _get_analysis_status(**kw: Any) -> AnalysisRun:
        return failed_run

    async def _fetch_job_log(**kw: Any) -> str:
        return "boom in vEcoli"

    service.dispatch_analysis = AsyncMock(side_effect=_dispatch)
    service.get_analysis_status = AsyncMock(side_effect=_get_analysis_status)
    service._fetch_job_log = AsyncMock(side_effect=_fetch_job_log)

    class _FakeSession:
        async def __aenter__(self) -> Any:
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

    class _FakeSvc:
        def session(self) -> _FakeSession:
            return _FakeSession()

    with patch("sms_api.common.handlers.analyses.get_ssh_session_service", return_value=_FakeSvc()):
        raw = await _collect(
            handle_run_analysis_sse(
                request=request,
                simulator=_simulator(),
                analysis_service=service,
                logger=logging.getLogger("test"),
                db_service=db_service,
                poll_interval=0.0,
            )
        )

    events = _parse_sse_events(raw)
    names = [e[0] for e in events]
    assert "error" in names
    assert names[-1] == "end"
    err = next(e[1] for e in events if e[0] == "error")
    assert err["error"] == "AnalysisJobFailedException"
    assert err["job_id"] == 12345
    assert "boom" in err.get("error_log", "")


@pytest.mark.asyncio
async def test_sse_unexpected_exception_is_emitted_as_error(tmp_path: Path) -> None:
    request = _request()
    service = _service(tmp_path)
    db_service = MagicMock()

    async def _boom(**kw: Any) -> Any:
        raise RuntimeError("unexpected")

    service.dispatch_analysis = AsyncMock(side_effect=_boom)

    class _FakeSession:
        async def __aenter__(self) -> Any:
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

    class _FakeSvc:
        def session(self) -> _FakeSession:
            return _FakeSession()

    with patch("sms_api.common.handlers.analyses.get_ssh_session_service", return_value=_FakeSvc()):
        raw = await _collect(
            handle_run_analysis_sse(
                request=request,
                simulator=_simulator(),
                analysis_service=service,
                logger=logging.getLogger("test"),
                db_service=db_service,
                poll_interval=0.0,
            )
        )

    events = _parse_sse_events(raw)
    err = next(e[1] for e in events if e[0] == "error")
    assert err["error"] == "RuntimeError"
    assert err["message"] == "unexpected"
    assert events[-1][0] == "end"
