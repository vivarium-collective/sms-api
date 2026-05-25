"""Tests for ProcessRegistryDatabaseService (SQLite in-memory, no mocks for DB layer)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

import pytest
import pytest_asyncio
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from sms_api.compose.database_service import ProcessRegistryORMExecutor
from sms_api.compose.models import ProcessInstanceStatus
from sms_api.compose.tables_orm import ComposeBase, ORMProcessInstance, ORMProcessUpdate

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def sqlite_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    # Only create the two new process-registry tables (other compose tables use bare JSONB,
    # which can't render on SQLite — those tables are tested against PostgreSQL elsewhere).
    tables: list[Table] = [cast(Table, ORMProcessInstance.__table__), cast(Table, ORMProcessUpdate.__table__)]
    async with engine.begin() as conn:
        await conn.run_sync(ComposeBase.metadata.create_all, tables=tables)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def process_registry_db(sqlite_engine: AsyncEngine) -> AsyncGenerator[ProcessRegistryORMExecutor]:
    session_maker = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    yield ProcessRegistryORMExecutor(session_maker)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProcessRegistryDB:
    @pytest.mark.asyncio
    async def test_insert_process_instance(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        process_id = "test-uuid-001"
        record = await process_registry_db.insert_process_instance(
            process_id=process_id,
            process_name="CopasiUTCStep",
            config={"model_file": "/models/model.xml"},
        )
        assert record.process_id == process_id
        assert record.process_name == "CopasiUTCStep"
        assert record.config == {"model_file": "/models/model.xml"}
        assert record.status == ProcessInstanceStatus.ACTIVE
        assert record.ended_at is None
        assert record.database_id > 0

    @pytest.mark.asyncio
    async def test_get_process_instance(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        process_id = "test-uuid-002"
        await process_registry_db.insert_process_instance(process_id, "TestStep", {})
        record = await process_registry_db.get_process_instance(process_id)
        assert record is not None
        assert record.process_id == process_id

    @pytest.mark.asyncio
    async def test_get_process_instance_not_found(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        record = await process_registry_db.get_process_instance("does-not-exist")
        assert record is None

    @pytest.mark.asyncio
    async def test_end_process_instance(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        process_id = "test-uuid-003"
        await process_registry_db.insert_process_instance(process_id, "TestStep", {})
        ended = await process_registry_db.end_process_instance(process_id)
        assert ended.status == ProcessInstanceStatus.ENDED
        assert ended.ended_at is not None

    @pytest.mark.asyncio
    async def test_end_nonexistent_raises(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        with pytest.raises(LookupError, match="not found"):
            await process_registry_db.end_process_instance("nonexistent-uuid")

    @pytest.mark.asyncio
    async def test_list_process_instances_active_filter(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        await process_registry_db.insert_process_instance("uuid-a", "StepA", {})
        await process_registry_db.insert_process_instance("uuid-b", "StepB", {})
        await process_registry_db.end_process_instance("uuid-b")

        active = await process_registry_db.list_process_instances(status=ProcessInstanceStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].process_id == "uuid-a"

        ended = await process_registry_db.list_process_instances(status=ProcessInstanceStatus.ENDED)
        assert len(ended) == 1
        assert ended[0].process_id == "uuid-b"

        all_instances = await process_registry_db.list_process_instances()
        assert len(all_instances) == 2

    @pytest.mark.asyncio
    async def test_insert_process_update(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        process_id = "test-uuid-004"
        await process_registry_db.insert_process_instance(process_id, "TestStep", {})
        update = await process_registry_db.insert_process_update(
            process_id=process_id,
            state={"time": 0.0, "mass": 1.0},
            interval=1.0,
            result={"output": 42.0},
        )
        assert update.process_instance_id > 0
        assert update.interval == 1.0
        assert update.state == {"time": 0.0, "mass": 1.0}
        assert update.result == {"output": 42.0}

    @pytest.mark.asyncio
    async def test_insert_process_update_non_dict_result(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        process_id = "test-uuid-005"
        await process_registry_db.insert_process_instance(process_id, "TestStep", {})
        update = await process_registry_db.insert_process_update(
            process_id=process_id,
            state={},
            interval=1.0,
            result=None,
        )
        assert update.result is None

    @pytest.mark.asyncio
    async def test_list_process_updates(self, process_registry_db: ProcessRegistryORMExecutor) -> None:
        process_id = "test-uuid-006"
        await process_registry_db.insert_process_instance(process_id, "TestStep", {})
        await process_registry_db.insert_process_update(process_id, {"t": 0}, 1.0, None)
        await process_registry_db.insert_process_update(process_id, {"t": 1}, 1.0, {"x": 1})
        await process_registry_db.insert_process_update(process_id, {"t": 2}, 1.0, {"x": 2})

        updates = await process_registry_db.list_process_updates(process_id)
        assert len(updates) == 3
        assert all(isinstance(u.database_id, int) for u in updates)

    @pytest.mark.asyncio
    async def test_list_process_updates_unknown_process_raises(
        self, process_registry_db: ProcessRegistryORMExecutor
    ) -> None:
        with pytest.raises(LookupError, match="not found"):
            await process_registry_db.list_process_updates("nonexistent-uuid")
