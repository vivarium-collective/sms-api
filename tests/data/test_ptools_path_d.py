"""Tests for Path D: eagerly materialize canonical ptools cache at simulation completion.

Covers:
- ``is_fork_simulator`` / ``should_eagerly_materialize_ptools`` gating.
- ``build_canonical_ptools_request`` builds the right shape.
- ``canonical_ptools_cache_dir`` agrees with the user-facing handler's cache key.
- ``schedule_canonical_ptools_materialization`` is a no-op when gated off,
  idempotent under concurrent calls, and skips when cache already populated.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from sms_api.analysis.analysis_service import (
    AnalysisServiceSlurm,
    RequestPayload,
    build_canonical_ptools_request,
    canonical_ptools_cache_dir,
    is_fork_simulator,
    should_eagerly_materialize_ptools,
)
from sms_api.analysis.models import (
    PTOOLS_CANONICAL_N_TP,
    PtoolsAnalysisConfig,
    PtoolsAnalysisType,
)
from sms_api.common.handlers import analyses as analyses_module
from sms_api.common.handlers.analyses import schedule_canonical_ptools_materialization
from sms_api.config import Settings
from sms_api.simulation.models import SimulatorVersion


def _simulator(branch: str = "api-support") -> SimulatorVersion:
    return SimulatorVersion(
        database_id=1,
        git_commit_hash="abc1234",
        git_repo_url="https://github.com/vivarium-collective/vEcoli",
        git_branch=branch,
        created_at=datetime.datetime(2026, 6, 1),
    )


def _settings(tmp_path: Path, namespace: str) -> Settings:
    return Settings(deployment_namespace=namespace, cache_dir=str(tmp_path))


# ---- predicates --------------------------------------------------------


def test_is_fork_simulator_true_only_for_api_support_branch() -> None:
    assert is_fork_simulator(_simulator(branch="api-support")) is True
    assert is_fork_simulator(_simulator(branch="master")) is False
    assert is_fork_simulator(_simulator(branch="main")) is False
    assert is_fork_simulator(_simulator(branch="some-feature")) is False


@pytest.mark.parametrize(
    ("branch", "namespace", "expected"),
    [
        ("api-support", "sms-api-rke", True),
        ("api-support", "sms-api-rke-dev", True),
        ("api-support", "sms-api-stanford", False),
        ("api-support", "sms-api-stanford-test", False),
        ("api-support", "", False),
        ("master", "sms-api-rke", False),
        ("main", "sms-api-rke-dev", False),
    ],
)
def test_should_eagerly_materialize_ptools_gating(
    branch: str,
    namespace: str,
    expected: bool,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, namespace)
    assert should_eagerly_materialize_ptools(_simulator(branch=branch), settings) is expected


# ---- request shape -----------------------------------------------------


def test_build_canonical_ptools_request_has_all_three_modules_at_canonical_n_tp() -> None:
    request = build_canonical_ptools_request(experiment_id="exp-d-1")
    assert request.experiment_id == "exp-d-1"
    assert request.single is not None
    names = [m.name for m in request.single if isinstance(m, PtoolsAnalysisConfig)]
    assert sorted(names) == sorted([
        PtoolsAnalysisType.REACTIONS.value,
        PtoolsAnalysisType.RNA.value,
        PtoolsAnalysisType.PROTEINS.value,
    ])
    for m in request.single:
        assert isinstance(m, PtoolsAnalysisConfig)
        assert m.n_tp == PTOOLS_CANONICAL_N_TP


def test_canonical_cache_dir_matches_user_request_hash_for_same_experiment(tmp_path: Path) -> None:
    """The whole point of Path D: when the user later asks for the same experiment's
    ptools modules (at any divisor n_tp), they must hit the cache directory Path D pre-warmed."""
    settings = _settings(tmp_path, "sms-api-rke")

    eager = canonical_ptools_cache_dir(env=settings, experiment_id="exp-d-2")

    user_request = build_canonical_ptools_request(experiment_id="exp-d-2")
    # Simulate a user request at a smaller n_tp — Phase B1 strips n_tp from the cache key.
    if user_request.single is not None:
        for m in user_request.single:
            if isinstance(m, PtoolsAnalysisConfig):
                m.n_tp = 8
    user_hash = RequestPayload(data=user_request.model_dump()).hash()
    assert eager == Path(settings.cache_dir) / user_hash


# ---- scheduling --------------------------------------------------------


def _service(settings: Settings) -> AnalysisServiceSlurm:
    return AnalysisServiceSlurm(env=settings)


@pytest.fixture(autouse=True)
def _clear_inflight() -> Any:
    analyses_module._inflight_materialize_tasks.clear()
    yield
    analyses_module._inflight_materialize_tasks.clear()


@pytest.mark.asyncio
async def test_schedule_returns_none_when_gated_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, "sms-api-stanford")  # not RKE
    called = False

    async def _should_not_run(*a: Any, **kw: Any) -> Any:
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(analyses_module, "handle_run_analysis_slurm", _should_not_run)

    task = schedule_canonical_ptools_materialization(
        experiment_id="exp-d-3",
        simulator=_simulator("api-support"),
        analysis_service=_service(settings),
        db_service=MagicMock(),
        parent_logger=logging.getLogger("test"),
    )
    assert task is None
    assert called is False


@pytest.mark.asyncio
async def test_schedule_returns_none_when_simulator_is_not_fork(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, "sms-api-rke")
    called = False

    async def _should_not_run(*a: Any, **kw: Any) -> Any:
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(analyses_module, "handle_run_analysis_slurm", _should_not_run)

    task = schedule_canonical_ptools_materialization(
        experiment_id="exp-d-4",
        simulator=_simulator("master"),
        analysis_service=_service(settings),
        db_service=MagicMock(),
        parent_logger=logging.getLogger("test"),
    )
    assert task is None
    assert called is False


@pytest.mark.asyncio
async def test_schedule_skips_when_cache_already_populated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, "sms-api-rke")
    # Pre-populate the canonical cache directory.
    cache_dir = canonical_ptools_cache_dir(env=settings, experiment_id="exp-d-5")
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "ptools_rxns_v0_s0_g0.tsv").write_text("dummy\n")

    called = False

    async def _should_not_run(*a: Any, **kw: Any) -> Any:
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(analyses_module, "handle_run_analysis_slurm", _should_not_run)

    task = schedule_canonical_ptools_materialization(
        experiment_id="exp-d-5",
        simulator=_simulator("api-support"),
        analysis_service=_service(settings),
        db_service=MagicMock(),
        parent_logger=logging.getLogger("test"),
    )
    assert task is None
    assert called is False


@pytest.mark.asyncio
async def test_schedule_dispatches_once_and_is_idempotent_concurrently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, "sms-api-rke")
    dispatched: list[str] = []
    release_event = asyncio.Event()

    async def _fake_handle(*, request: Any, **kw: Any) -> list[Any]:
        dispatched.append(request.experiment_id)
        await release_event.wait()
        return []

    monkeypatch.setattr(analyses_module, "handle_run_analysis_slurm", _fake_handle)

    sim = _simulator("api-support")
    svc = _service(settings)

    first = schedule_canonical_ptools_materialization(
        experiment_id="exp-d-6",
        simulator=sim,
        analysis_service=svc,
        db_service=MagicMock(),
        parent_logger=logging.getLogger("test"),
    )
    assert first is not None

    # Second call while first is still in flight must be a no-op.
    second = schedule_canonical_ptools_materialization(
        experiment_id="exp-d-6",
        simulator=sim,
        analysis_service=svc,
        db_service=MagicMock(),
        parent_logger=logging.getLogger("test"),
    )
    assert second is None

    release_event.set()
    await first
    assert dispatched == ["exp-d-6"]


@pytest.mark.asyncio
async def test_schedule_logs_failures_but_does_not_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    settings = _settings(tmp_path, "sms-api-rke")

    async def _fail(*a: Any, **kw: Any) -> list[Any]:
        raise RuntimeError("slurm submit refused")

    monkeypatch.setattr(analyses_module, "handle_run_analysis_slurm", _fail)

    log = logging.getLogger("test-path-d")
    log.setLevel(logging.WARNING)
    caplog.set_level(logging.WARNING, logger="test-path-d")

    task = schedule_canonical_ptools_materialization(
        experiment_id="exp-d-7",
        simulator=_simulator("api-support"),
        analysis_service=_service(settings),
        db_service=MagicMock(),
        parent_logger=log,
    )
    assert task is not None
    # The task will raise; gather with return_exceptions so we don't propagate it.
    # The done-callback is scheduled via call_soon and runs on the next loop tick.
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)
    assert "exp-d-7" not in analyses_module._inflight_materialize_tasks
    assert any("Path D ptools materialization failed" in rec.message for rec in caplog.records)
