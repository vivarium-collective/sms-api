"""Tests for PackageDatabaseService (SQLite in-memory)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

import pytest
import pytest_asyncio
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from sms_api.compose.database_service import PackageORMExecutor
from sms_api.compose.models import (
    BiGraphComputeOutline,
    BiGraphComputeType,
    PackageOutline,
    PackageType,
)
from sms_api.compose.tables_orm import (
    ComposeBase,
    ORMComposeBiGraphCompute,
    ORMComposePackage,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def sqlite_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    tables: list[Table] = [
        cast(Table, ORMComposePackage.__table__),
        cast(Table, ORMComposeBiGraphCompute.__table__),
    ]
    async with engine.begin() as conn:
        await conn.run_sync(ComposeBase.metadata.create_all, tables=tables)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def pkg_db(sqlite_engine: AsyncEngine) -> AsyncGenerator[PackageORMExecutor]:
    session_maker = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    yield PackageORMExecutor(session_maker)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPackageDB:
    @pytest.mark.asyncio
    async def test_insert_and_list_packages(self, pkg_db: PackageORMExecutor) -> None:
        outline = PackageOutline(
            package_type=PackageType.PYPI,
            name="test-pkg",
            compute=[
                BiGraphComputeOutline(
                    module="test_pkg.module",
                    name="TestProcess",
                    compute_type=BiGraphComputeType.PROCESS,
                    inputs="{}",
                    outputs="{}",
                ),
                BiGraphComputeOutline(
                    module="test_pkg.module",
                    name="TestStep",
                    compute_type=BiGraphComputeType.STEP,
                    inputs="{}",
                    outputs="{}",
                ),
            ],
        )
        registered = await pkg_db.insert_package(outline)
        assert registered.database_id > 0
        assert registered.name == "test-pkg"
        assert len(registered.processes) == 1
        assert len(registered.steps) == 1
        assert registered.processes[0].name == "TestProcess"
        assert registered.steps[0].name == "TestStep"

        packages = await pkg_db.list_all_packages()
        assert len(packages) == 1
        assert packages[0].name == "test-pkg"

    @pytest.mark.asyncio
    async def test_get_package_by_id(self, pkg_db: PackageORMExecutor) -> None:
        outline = PackageOutline(
            package_type=PackageType.PYPI,
            name="get-test-pkg",
            compute=[
                BiGraphComputeOutline(
                    module="get_test.module",
                    name="GetProcess",
                    compute_type=BiGraphComputeType.PROCESS,
                    inputs="{}",
                    outputs="{}",
                ),
            ],
        )
        registered = await pkg_db.insert_package(outline)
        fetched = await pkg_db.get_package(registered.database_id)
        assert fetched is not None
        assert fetched.name == "get-test-pkg"
        assert len(fetched.processes) == 1

    @pytest.mark.asyncio
    async def test_get_package_not_found(self, pkg_db: PackageORMExecutor) -> None:
        fetched = await pkg_db.get_package(9999)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_get_package_by_name(self, pkg_db: PackageORMExecutor) -> None:
        outline = PackageOutline(
            package_type=PackageType.PYPI,
            name="name-lookup-pkg",
            compute=[],
        )
        registered = await pkg_db.insert_package(outline)
        fetched = await pkg_db.get_package_by_name("name-lookup-pkg")
        assert fetched is not None
        assert fetched.database_id == registered.database_id

    @pytest.mark.asyncio
    async def test_get_package_by_name_not_found(self, pkg_db: PackageORMExecutor) -> None:
        fetched = await pkg_db.get_package_by_name("nonexistent-pkg")
        assert fetched is None

    @pytest.mark.asyncio
    async def test_duplicate_package_name_raises(self, pkg_db: PackageORMExecutor) -> None:
        outline = PackageOutline(
            package_type=PackageType.PYPI,
            name="dup-pkg",
            compute=[],
        )
        await pkg_db.insert_package(outline)
        with pytest.raises(Exception, match="UNIQUE constraint"):  # IntegrityError
            await pkg_db.insert_package(outline)

    @pytest.mark.asyncio
    async def test_empty_list_when_no_packages(self, pkg_db: PackageORMExecutor) -> None:
        packages = await pkg_db.list_all_packages()
        assert packages == []

    @pytest.mark.asyncio
    async def test_insert_package_with_no_compute(self, pkg_db: PackageORMExecutor) -> None:
        outline = PackageOutline(
            package_type=PackageType.PYPI,
            name="empty-pkg",
            compute=[],
        )
        registered = await pkg_db.insert_package(outline)
        assert registered.database_id > 0
        assert len(registered.processes) == 0
        assert len(registered.steps) == 0
