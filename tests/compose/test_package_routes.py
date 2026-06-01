"""Tests for the compose package registry routes (todo:57 Part B)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, cast

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

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


@pytest.fixture()
def client(sqlite_engine: AsyncEngine) -> TestClient:  # type: ignore[misc]
    from sms_api.api.routers import compose as compose_module
    from sms_api.compose.database_service import ComposeDatabaseService

    session_maker = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    db = ComposeDatabaseService(session_maker)

    # Wire the real DB into the module-level singleton
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(compose_module, "_compose_db_service", db)

    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(compose_module.router, prefix="/compose/v1")
    client = TestClient(app)

    yield client

    monkeypatch.undo()


class TestPackageRoutes:
    def test_list_packages_empty(self, client: TestClient) -> None:
        resp = client.get("/compose/v1/packages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_packages_after_insert(self, client: TestClient) -> None:
        """Insert inline outline then verify it appears in list."""
        resp = client.post(
            "/compose/v1/packages",
            json={
                "kind": "outline",
                "outline": {
                    "package_type": "pypi",
                    "name": "route-test-pkg",
                    "compute": [
                        {
                            "module": "route_test.module",
                            "name": "RouteProcess",
                            "compute_type": "process",
                            "inputs": "{}",
                            "outputs": "{}",
                        },
                    ],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "route-test-pkg"

        # Verify it appears in list
        resp = client.get("/compose/v1/packages")
        assert resp.status_code == 200
        packages = resp.json()
        assert len(packages) == 1
        assert packages[0]["name"] == "route-test-pkg"
        assert packages[0]["num_processes"] == 1
        assert packages[0]["num_steps"] == 0

    def test_get_package_by_id(self, client: TestClient) -> None:
        # Insert first
        resp = client.post(
            "/compose/v1/packages",
            json={
                "kind": "outline",
                "outline": {
                    "package_type": "pypi",
                    "name": "get-by-id-pkg",
                    "compute": [],
                },
            },
        )
        pkg_id = resp.json()["database_id"]

        # Get by id
        resp = client.get(f"/compose/v1/packages/{pkg_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "get-by-id-pkg"

    def test_get_package_not_found(self, client: TestClient) -> None:
        resp = client.get("/compose/v1/packages/9999")
        assert resp.status_code == 404

    def test_register_package_invalid_kind(self, client: TestClient) -> None:
        resp = client.post(
            "/compose/v1/packages",
            json={"kind": "invalid_kind"},
        )
        assert resp.status_code == 400

    def test_register_package_missing_url(self, client: TestClient) -> None:
        resp = client.post(
            "/compose/v1/packages",
            json={"kind": "repo_url"},
        )
        assert resp.status_code == 400

    def test_register_package_duplicate_name(self, client: TestClient) -> None:
        client.post(
            "/compose/v1/packages",
            json={
                "kind": "outline",
                "outline": {
                    "package_type": "pypi",
                    "name": "dup-pkg",
                    "compute": [],
                },
            },
        )
        resp = client.post(
            "/compose/v1/packages",
            json={
                "kind": "outline",
                "outline": {
                    "package_type": "pypi",
                    "name": "dup-pkg",
                    "compute": [],
                },
            },
        )
        assert resp.status_code == 409

    def test_audit_package_nonexistent_path(self, client: TestClient) -> None:
        resp = client.post(
            "/compose/v1/packages/audit",
            json={"target": "/nonexistent/path/to/repo"},
        )
        assert resp.status_code == 404

    def test_audit_package_local_path(self, client: TestClient, tmp_path: Any) -> None:
        """Audit a real local pyproject.toml created in tmp_path."""
        pkg_dir = tmp_path / "pbg-test-audit"
        pkg_dir.mkdir()
        pyproject = pkg_dir / "pyproject.toml"
        pyproject.write_text("""[project]
name = "pbg-test-audit"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["bigraph-schema>=0.0.60", "process-bigraph>=0.0.66"]
""")

        resp = client.post(
            "/compose/v1/packages/audit",
            json={"target": str(pkg_dir), "run_install": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["target"] == str(pkg_dir)
        checks = data["checks"]
        # Should have at minimum: pyproject.toml, bigraph-schema dep, process-bigraph dep
        check_names = {c["name"] for c in checks}
        assert "pyproject.toml" in check_names
        assert "bigraph-schema dep" in check_names
        assert "process-bigraph dep" in check_names
        # All should pass
        assert all(c["status"] != "FAIL" for c in checks)

    def test_processes_db_source(self, client: TestClient) -> None:
        """Insert a package and verify it shows up in /processes?source=db."""
        client.post(
            "/compose/v1/packages",
            json={
                "kind": "outline",
                "outline": {
                    "package_type": "pypi",
                    "name": "db-proc-test",
                    "compute": [
                        {
                            "module": "db_proc.module",
                            "name": "DbProcess",
                            "compute_type": "process",
                            "inputs": "{}",
                            "outputs": "{}",
                        },
                    ],
                },
            },
        )
        resp = client.get("/compose/v1/processes?source=db")
        assert resp.status_code == 200
        data = resp.json()
        names = {entry["name"] for entry in data}
        assert "DbProcess" in names
