"""``analysis_options`` on the compose run request (task 1 of the
compose-results chain): carried in on both compose transports and persisted on
the ``ComposeSimulation`` DB row so a later task can chain an analysis job.

This task only threads and persists the field -- it does NOT submit an
analysis job.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from viva_api.compose.container_def import ContainerizationFileRepr
from viva_api.compose.database_service import SimulatorORMExecutor
from viva_api.compose.models import ComposeSimulationRequest, SimulationFileType
from viva_api.compose.tables_orm import ORMComposeSimulation, create_compose_db

_ANALYSIS_OPTIONS = {"report_cards": ["mass_conservation"], "seeds": [1, 2, 3]}


# ---------------------------------------------------------------------------
# Request round-trip: onto the constructed ComposeSimulationRequest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_simulation_threads_analysis_options(fastapi_app: object) -> None:
    """Upload transport (/simulation/run): analysis_options arrives as a Form
    field carrying a JSON string, and must round-trip onto the constructed
    ComposeSimulationRequest as a parsed dict."""
    captured: dict[str, Any] = {}

    async def _fake_run(**kwargs: Any) -> Any:
        captured.update(kwargs)
        from viva_api.compose.models import ComposeSimulationExperiment

        return ComposeSimulationExperiment(simulation_database_id=1, simulator_database_id=1)

    fake_db = MagicMock()
    fake_db.get_allow_list_db.return_value.list_allow_list = AsyncMock(return_value=["pypi::cobra"])

    with ExitStack() as stack:
        stack.enter_context(patch("viva_api.api.routers.compose.run_compose_simulation", _fake_run))
        stack.enter_context(patch("viva_api.api.routers.compose._require_db", return_value=fake_db))
        stack.enter_context(patch("viva_api.api.routers.compose._require_sim", return_value=MagicMock()))
        stack.enter_context(patch("viva_api.api.routers.compose._require_monitor", return_value=MagicMock()))
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://testserver") as client:  # type: ignore[arg-type]
            response = await client.post(
                "/compose/v1/simulation/run",
                data={"analysis_options": json.dumps(_ANALYSIS_OPTIONS)},
                files={"uploaded_file": ("m.pbg", b'{"state": {}}', "application/json")},
            )

    assert response.status_code == 200
    assert captured["simulation_request"].analysis_options == _ANALYSIS_OPTIONS


@pytest.mark.asyncio
async def test_submit_simulation_omits_analysis_options_by_default(fastapi_app: object) -> None:
    """No analysis_options sent -> None on the request, byte-for-byte today's
    exact behavior for every caller that doesn't know this field exists yet."""
    captured: dict[str, Any] = {}

    async def _fake_run(**kwargs: Any) -> Any:
        captured.update(kwargs)
        from viva_api.compose.models import ComposeSimulationExperiment

        return ComposeSimulationExperiment(simulation_database_id=1, simulator_database_id=1)

    fake_db = MagicMock()
    fake_db.get_allow_list_db.return_value.list_allow_list = AsyncMock(return_value=["pypi::cobra"])

    with ExitStack() as stack:
        stack.enter_context(patch("viva_api.api.routers.compose.run_compose_simulation", _fake_run))
        stack.enter_context(patch("viva_api.api.routers.compose._require_db", return_value=fake_db))
        stack.enter_context(patch("viva_api.api.routers.compose._require_sim", return_value=MagicMock()))
        stack.enter_context(patch("viva_api.api.routers.compose._require_monitor", return_value=MagicMock()))
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://testserver") as client:  # type: ignore[arg-type]
            response = await client.post(
                "/compose/v1/simulation/run",
                files={"uploaded_file": ("m.pbg", b'{"state": {}}', "application/json")},
            )

    assert response.status_code == 200
    assert captured["simulation_request"].analysis_options is None


@pytest.mark.asyncio
async def test_submit_simulation_rejects_invalid_analysis_options_json(fastapi_app: object) -> None:
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://testserver") as client:  # type: ignore[arg-type]
        response = await client.post(
            "/compose/v1/simulation/run",
            data={"analysis_options": "{not-json"},
            files={"uploaded_file": ("m.pbg", b'{"state": {}}', "application/json")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_simulation_document_threads_analysis_options(fastapi_app: object) -> None:
    """JSON-body transport (/simulation/run-document): analysis_options arrives
    as a native JSON dict on the body and must round-trip onto the constructed
    ComposeSimulationRequest."""
    captured: dict[str, Any] = {}

    async def _fake_run(**kwargs: Any) -> Any:
        captured.update(kwargs)
        from viva_api.compose.models import ComposeSimulationExperiment

        return ComposeSimulationExperiment(simulation_database_id=1, simulator_database_id=1)

    fake_db = MagicMock()
    fake_db.get_allow_list_db.return_value.list_allow_list = AsyncMock(return_value=["pypi::cobra"])

    with ExitStack() as stack:
        stack.enter_context(patch("viva_api.api.routers.compose.run_compose_simulation", _fake_run))
        stack.enter_context(patch("viva_api.api.routers.compose._require_db", return_value=fake_db))
        stack.enter_context(patch("viva_api.api.routers.compose._require_sim", return_value=MagicMock()))
        stack.enter_context(patch("viva_api.api.routers.compose._require_monitor", return_value=MagicMock()))
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://testserver") as client:  # type: ignore[arg-type]
            response = await client.post(
                "/compose/v1/simulation/run-document",
                json={"document": {"state": {}}, "analysis_options": _ANALYSIS_OPTIONS},
            )

    assert response.status_code == 200
    assert captured["simulation_request"].analysis_options == _ANALYSIS_OPTIONS


@pytest.mark.asyncio
async def test_submit_simulation_document_omits_analysis_options_by_default(fastapi_app: object) -> None:
    captured: dict[str, Any] = {}

    async def _fake_run(**kwargs: Any) -> Any:
        captured.update(kwargs)
        from viva_api.compose.models import ComposeSimulationExperiment

        return ComposeSimulationExperiment(simulation_database_id=1, simulator_database_id=1)

    fake_db = MagicMock()
    fake_db.get_allow_list_db.return_value.list_allow_list = AsyncMock(return_value=["pypi::cobra"])

    with ExitStack() as stack:
        stack.enter_context(patch("viva_api.api.routers.compose.run_compose_simulation", _fake_run))
        stack.enter_context(patch("viva_api.api.routers.compose._require_db", return_value=fake_db))
        stack.enter_context(patch("viva_api.api.routers.compose._require_sim", return_value=MagicMock()))
        stack.enter_context(patch("viva_api.api.routers.compose._require_monitor", return_value=MagicMock()))
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://testserver") as client:  # type: ignore[arg-type]
            response = await client.post(
                "/compose/v1/simulation/run-document",
                json={"document": {"state": {}}},
            )

    assert response.status_code == 200
    assert captured["simulation_request"].analysis_options is None


# ---------------------------------------------------------------------------
# Persistence: onto the ComposeSimulation DB row
#
# The two DB-backed tests below (real Postgres via testcontainers) are the
# primary check and match this dir's existing convention (see
# test_env_worker_tasks.py's task_db fixture). This one is a docker-free
# supplement covering the same wiring -- insert_simulation must construct the
# ORM row with analysis_options -- so the persistence path stays verified even
# when a docker daemon isn't reachable.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_simulation_constructs_orm_row_with_analysis_options() -> None:
    from viva_api.compose.database_service import SimulatorORMExecutor
    from viva_api.compose.models import ComposeSimulatorVersion
    from viva_api.compose.tables_orm import ORMComposeSimulation

    captured_orm: dict[str, Any] = {}

    class _FakeSession:
        def add(self, orm: Any) -> None:
            captured_orm["orm"] = orm

        async def flush(self) -> None:
            captured_orm["orm"].id = 99

        def begin(self) -> Any:
            return self

        async def __aenter__(self) -> _FakeSession:
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

    class _FakeSessionMaker:
        def __call__(self) -> _FakeSession:
            return _FakeSession()

    executor = SimulatorORMExecutor(_FakeSessionMaker())  # type: ignore[arg-type]
    simulator_version = ComposeSimulatorVersion(
        singularity_def=ContainerizationFileRepr(representation="x"),
        singularity_def_hash="hash",
        packages=None,
        database_id=1,
    )
    sim_request = ComposeSimulationRequest(
        request_file_path=Path("does-not-matter.pbg"),
        simulation_file_type=SimulationFileType.PBG,
        is_batch=False,
        analysis_options=_ANALYSIS_OPTIONS,
    )

    await executor.insert_simulation(
        sim_request=sim_request,
        experiment_id="exp-mock-1",
        simulator_version=simulator_version,
        document="{}",
        analysis_options=sim_request.analysis_options,
    )

    orm = captured_orm["orm"]
    assert isinstance(orm, ORMComposeSimulation)
    assert orm.analysis_options == _ANALYSIS_OPTIONS


@pytest_asyncio.fixture
async def simulator_db(postgres_url: str) -> AsyncGenerator[SimulatorORMExecutor]:
    engine: AsyncEngine = create_async_engine(postgres_url, echo=False)
    await create_compose_db(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield SimulatorORMExecutor(maker)
    await engine.dispose()


@pytest.mark.asyncio
async def test_insert_simulation_persists_analysis_options(simulator_db: SimulatorORMExecutor) -> None:
    simulator_version = await simulator_db.insert_simulator(
        ContainerizationFileRepr(representation="Bootstrap: docker\nFrom: ubuntu\n")
    )
    sim_request = ComposeSimulationRequest(
        request_file_path=Path("does-not-matter.pbg"),
        simulation_file_type=SimulationFileType.PBG,
        is_batch=False,
        analysis_options=_ANALYSIS_OPTIONS,
    )

    simulation = await simulator_db.insert_simulation(
        sim_request=sim_request,
        experiment_id="exp-analysis-options-1",
        simulator_version=simulator_version,
        document="{}",
        analysis_options=sim_request.analysis_options,
    )

    async with simulator_db.async_session_maker() as session:
        stmt = select(ORMComposeSimulation).where(ORMComposeSimulation.id == simulation.database_id)
        orm = (await session.execute(stmt)).scalars().one()
        assert orm.analysis_options == _ANALYSIS_OPTIONS


@pytest.mark.asyncio
async def test_insert_simulation_persists_none_analysis_options_by_default(
    simulator_db: SimulatorORMExecutor,
) -> None:
    simulator_version = await simulator_db.insert_simulator(
        ContainerizationFileRepr(representation="Bootstrap: docker\nFrom: ubuntu\nv2\n")
    )
    sim_request = ComposeSimulationRequest(
        request_file_path=Path("does-not-matter-2.pbg"),
        simulation_file_type=SimulationFileType.PBG,
        is_batch=False,
    )

    simulation = await simulator_db.insert_simulation(
        sim_request=sim_request,
        experiment_id="exp-analysis-options-2",
        simulator_version=simulator_version,
        document="{}",
    )

    async with simulator_db.async_session_maker() as session:
        stmt = select(ORMComposeSimulation).where(ORMComposeSimulation.id == simulation.database_id)
        orm = (await session.execute(stmt)).scalars().one()
        assert orm.analysis_options is None
