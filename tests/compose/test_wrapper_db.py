"""Tests for WrapperDatabaseService (SQLite in-memory, no mocks for DB layer)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

import pytest
import pytest_asyncio
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from sms_api.compose.database_service import WrapperORMExecutor
from sms_api.compose.models import WrapperStatus
from sms_api.compose.tables_orm import ComposeBase, ORMPbgWrapper

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SOURCE_URL = "https://github.com/vivarium-collective/mem3dg"
_TOOL_NAME = "mem3dg"


@pytest_asyncio.fixture()
async def sqlite_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    tables: list[Table] = [cast(Table, ORMPbgWrapper.__table__)]
    async with engine.begin() as conn:
        await conn.run_sync(ComposeBase.metadata.create_all, tables=tables)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def wrapper_db(sqlite_engine: AsyncEngine) -> AsyncGenerator[WrapperORMExecutor]:
    session_maker = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    yield WrapperORMExecutor(session_maker)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWrapperDB:
    @pytest.mark.asyncio
    async def test_insert_wrapper_defaults(self, wrapper_db: WrapperORMExecutor) -> None:
        record = await wrapper_db.insert_wrapper(
            tool_name=_TOOL_NAME,
            source_repo_url=_SOURCE_URL,
            source_ref="main",
        )
        assert record.wrapper_id > 0
        assert record.tool_name == _TOOL_NAME
        assert record.source_repo_url == _SOURCE_URL
        assert record.source_ref == "main"
        assert record.status == WrapperStatus.GENERATING
        assert record.simulator_id is None
        assert record.storage_uri is None
        assert record.error_message is None
        assert record.created_at is not None

    @pytest.mark.asyncio
    async def test_get_wrapper(self, wrapper_db: WrapperORMExecutor) -> None:
        inserted = await wrapper_db.insert_wrapper(_TOOL_NAME, _SOURCE_URL, "main")
        fetched = await wrapper_db.get_wrapper(inserted.wrapper_id)
        assert fetched is not None
        assert fetched.wrapper_id == inserted.wrapper_id
        assert fetched.tool_name == _TOOL_NAME
        assert fetched.status == WrapperStatus.GENERATING

    @pytest.mark.asyncio
    async def test_get_wrapper_not_found(self, wrapper_db: WrapperORMExecutor) -> None:
        result = await wrapper_db.get_wrapper(99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_wrapper_status_to_ready(self, wrapper_db: WrapperORMExecutor) -> None:
        inserted = await wrapper_db.insert_wrapper(_TOOL_NAME, _SOURCE_URL, "main")
        updated = await wrapper_db.update_wrapper_status(
            wrapper_id=inserted.wrapper_id,
            status=WrapperStatus.READY,
            storage_uri="pbg-wrappers/1/pbg-mem3dg.tar.gz",
        )
        assert updated.status == WrapperStatus.READY
        assert updated.storage_uri == "pbg-wrappers/1/pbg-mem3dg.tar.gz"
        assert updated.error_message is None

    @pytest.mark.asyncio
    async def test_update_wrapper_status_to_failed(self, wrapper_db: WrapperORMExecutor) -> None:
        inserted = await wrapper_db.insert_wrapper(_TOOL_NAME, _SOURCE_URL, "main")
        updated = await wrapper_db.update_wrapper_status(
            wrapper_id=inserted.wrapper_id,
            status=WrapperStatus.FAILED,
            error_message="Agent timeout after 120s",
        )
        assert updated.status == WrapperStatus.FAILED
        assert updated.error_message == "Agent timeout after 120s"

    @pytest.mark.asyncio
    async def test_update_wrapper_status_not_found_raises(self, wrapper_db: WrapperORMExecutor) -> None:
        with pytest.raises(LookupError, match="not found"):
            await wrapper_db.update_wrapper_status(99999, WrapperStatus.READY)

    @pytest.mark.asyncio
    async def test_update_wrapper_simulator_id_sets_building(self, wrapper_db: WrapperORMExecutor) -> None:
        inserted = await wrapper_db.insert_wrapper(_TOOL_NAME, _SOURCE_URL, "main")
        await wrapper_db.update_wrapper_status(inserted.wrapper_id, WrapperStatus.READY)
        updated = await wrapper_db.update_wrapper_simulator_id(
            wrapper_id=inserted.wrapper_id,
            simulator_id=42,
        )
        assert updated.simulator_id == 42
        assert updated.status == WrapperStatus.BUILDING

    @pytest.mark.asyncio
    async def test_update_wrapper_simulator_id_not_found_raises(self, wrapper_db: WrapperORMExecutor) -> None:
        with pytest.raises(LookupError, match="not found"):
            await wrapper_db.update_wrapper_simulator_id(99999, simulator_id=1)

    @pytest.mark.asyncio
    async def test_list_wrappers_no_filter(self, wrapper_db: WrapperORMExecutor) -> None:
        await wrapper_db.insert_wrapper("mem3dg", _SOURCE_URL, "main")
        await wrapper_db.insert_wrapper("cobra", "https://github.com/opencobra/cobrapy", "main")
        all_wrappers = await wrapper_db.list_wrappers()
        assert len(all_wrappers) == 2

    @pytest.mark.asyncio
    async def test_list_wrappers_status_filter(self, wrapper_db: WrapperORMExecutor) -> None:
        r1 = await wrapper_db.insert_wrapper("mem3dg", _SOURCE_URL, "main")
        r2 = await wrapper_db.insert_wrapper("cobra", "https://github.com/opencobra/cobrapy", "main")
        await wrapper_db.update_wrapper_status(r1.wrapper_id, WrapperStatus.AVAILABLE)

        available = await wrapper_db.list_wrappers(status=WrapperStatus.AVAILABLE)
        assert len(available) == 1
        assert available[0].tool_name == "mem3dg"

        generating = await wrapper_db.list_wrappers(status=WrapperStatus.GENERATING)
        assert len(generating) == 1
        assert generating[0].wrapper_id == r2.wrapper_id

    @pytest.mark.asyncio
    async def test_custom_source_ref(self, wrapper_db: WrapperORMExecutor) -> None:
        record = await wrapper_db.insert_wrapper(_TOOL_NAME, _SOURCE_URL, source_ref="v1.2.3")
        assert record.source_ref == "v1.2.3"
