"""Unit tests for the compose package-registration handler helpers.

Tests the private ``_handle_register_*``, ``_build_outline_from_audit``,
``_raise_if_audit_failed``, and ``_raise_if_package_exists`` functions in
``sms_api/api/routers/compose.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from sms_api.compose.models import (
    BiGraphComputeOutline,
    BiGraphComputeType,
    PackageOutline,
    PackageType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_AUDIT_REPORT_PASS: Any = MagicMock()
_AUDIT_REPORT_PASS.checks = [
    MagicMock(name="pyproject.toml", status="PASS", detail="found"),
    MagicMock(name="bigraph-schema dep", status="PASS", detail="bigraph-schema>=0.0.60"),
    MagicMock(name="process-bigraph dep", status="PASS", detail="process-bigraph>=0.0.66"),
]
_AUDIT_REPORT_PASS.fixes = []

_AUDIT_REPORT_FAIL: Any = MagicMock()
_AUDIT_REPORT_FAIL.checks = [
    MagicMock(name="pyproject.toml", status="FAIL", detail="missing"),
    MagicMock(name="bigraph-schema dep", status="FAIL", detail="not found"),
]
_AUDIT_REPORT_FAIL.fixes = ["Create pyproject.toml"]

_REGISTERED_PACKAGE: Any = MagicMock()
_REGISTERED_PACKAGE.database_id = 42
_REGISTERED_PACKAGE.package_type = MagicMock()
_REGISTERED_PACKAGE.package_type.value = "pypi"
_REGISTERED_PACKAGE.name = "test-pkg"
_REGISTERED_PACKAGE.processes = [
    MagicMock(name="TestProcess", module="test_pkg.module", compute_type="process", inputs="{}", outputs="{}"),
]
_REGISTERED_PACKAGE.steps = []


# ---------------------------------------------------------------------------
# _handle_register_repo_url
# ---------------------------------------------------------------------------


class TestHandleRegisterRepoUrl:
    @pytest.mark.asyncio
    async def test_url_cloned_audited_and_inserted(self, tmp_path: Path) -> None:
        from sms_api.api.routers.compose import _handle_register_repo_url

        repo_dir = tmp_path / "cloned-repo"
        repo_dir.mkdir()
        (repo_dir / "pyproject.toml").write_text("""[project]
name = "pbg-test"
version = "0.1.0"
""")

        request = MagicMock()
        request.kind = "repo_url"
        request.url = "https://github.com/vivarium-collective/pbg-test"
        request.ref = "main"
        request.path = None
        request.outline = None

        pkg_db = AsyncMock()
        pkg_db.insert_package = AsyncMock(return_value=_REGISTERED_PACKAGE)
        pkg_db.get_package_by_name = AsyncMock(return_value=None)

        with (
            patch("sms_api.compose.package_audit.clone_repo", return_value=repo_dir),
            patch("sms_api.compose.package_audit.audit_repo", return_value=_AUDIT_REPORT_PASS),
        ):
            result = await _handle_register_repo_url(request, pkg_db)

        assert result.database_id == 42
        pkg_db.insert_package.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_audit_failure_raises_400(self) -> None:
        from sms_api.api.routers.compose import _handle_register_repo_url

        request = MagicMock()
        request.kind = "repo_url"
        request.url = "https://github.com/vivarium-collective/pbg-test"
        request.ref = None
        request.path = None
        request.outline = None

        pkg_db = AsyncMock()

        with (
            patch("sms_api.compose.package_audit.clone_repo", return_value=Path("/mock/cloned-repo")),
            patch("sms_api.compose.package_audit.audit_repo", return_value=_AUDIT_REPORT_FAIL),
        ):
            with pytest.raises(HTTPException) as exc:
                await _handle_register_repo_url(request, pkg_db)
            assert exc.value.status_code == 400
            assert "FAILED" in exc.value.detail

    @pytest.mark.asyncio
    async def test_missing_url_raises_400(self) -> None:
        from sms_api.api.routers.compose import _handle_register_repo_url

        request = MagicMock()
        request.kind = "repo_url"
        request.url = None

        pkg_db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await _handle_register_repo_url(request, pkg_db)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_duplicate_package_raises_409(self, tmp_path: Path) -> None:
        from sms_api.api.routers.compose import _handle_register_repo_url

        repo_dir = tmp_path / "cloned-repo"
        repo_dir.mkdir()
        (repo_dir / "pyproject.toml").write_text("""[project]
name = "pbg-test"
version = "0.1.0"
""")

        request = MagicMock()
        request.kind = "repo_url"
        request.url = "https://github.com/vivarium-collective/pbg-test"
        request.ref = None
        request.path = None
        request.outline = None

        existing = MagicMock()
        existing.database_id = 1
        pkg_db = AsyncMock()
        pkg_db.get_package_by_name = AsyncMock(return_value=existing)

        with (
            patch("sms_api.compose.package_audit.clone_repo", return_value=repo_dir),
            patch("sms_api.compose.package_audit.audit_repo", return_value=_AUDIT_REPORT_PASS),
        ):
            with pytest.raises(HTTPException) as exc:
                await _handle_register_repo_url(request, pkg_db)
            assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# _handle_register_local_path
# ---------------------------------------------------------------------------


class TestHandleRegisterLocalPath:
    @pytest.mark.asyncio
    async def test_path_audited_and_inserted(self, tmp_path: Path) -> None:
        from sms_api.api.routers.compose import _handle_register_local_path

        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "pyproject.toml").write_text("""[project]
name = "test-pkg"
version = "0.1.0"
""")

        request = MagicMock()
        request.kind = "local_path"
        request.path = str(repo_dir)
        request.url = None
        request.ref = None
        request.outline = None

        pkg_db = AsyncMock()
        pkg_db.insert_package = AsyncMock(return_value=_REGISTERED_PACKAGE)
        pkg_db.get_package_by_name = AsyncMock(return_value=None)

        with (
            patch("sms_api.compose.package_audit.audit_repo", return_value=_AUDIT_REPORT_PASS),
        ):
            result = await _handle_register_local_path(request, pkg_db)
        assert result.database_id == 42
        pkg_db.insert_package.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_path_not_found_raises_404(self) -> None:
        from sms_api.api.routers.compose import _handle_register_local_path

        request = MagicMock()
        request.kind = "local_path"
        request.path = "/nonexistent"
        request.url = None
        request.ref = None
        request.outline = None

        pkg_db = AsyncMock()
        with (
            patch("pathlib.Path.exists", return_value=False),
        ):
            with pytest.raises(HTTPException) as exc:
                await _handle_register_local_path(request, pkg_db)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_audit_failure_raises_400(self) -> None:
        from sms_api.api.routers.compose import _handle_register_local_path

        request = MagicMock()
        request.kind = "local_path"
        request.path = "/mock/test-repo"
        request.url = None
        request.ref = None
        request.outline = None

        pkg_db = AsyncMock()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("sms_api.compose.package_audit.audit_repo", return_value=_AUDIT_REPORT_FAIL),
        ):
            with pytest.raises(HTTPException) as exc:
                await _handle_register_local_path(request, pkg_db)
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_path_raises_400(self) -> None:
        from sms_api.api.routers.compose import _handle_register_local_path

        request = MagicMock()
        request.kind = "local_path"
        request.path = None

        pkg_db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await _handle_register_local_path(request, pkg_db)
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# _handle_register_outline
# ---------------------------------------------------------------------------


class TestHandleRegisterOutline:
    @pytest.mark.asyncio
    async def test_outline_inserted(self) -> None:
        from sms_api.api.routers.compose import _handle_register_outline

        outline = PackageOutline(
            package_type=PackageType.PYPI,
            name="inline-pkg",
            compute=[
                BiGraphComputeOutline(
                    module="inline.module",
                    name="InlineProcess",
                    compute_type=BiGraphComputeType.PROCESS,
                    inputs="{}",
                    outputs="{}",
                ),
            ],
        )
        request = MagicMock()
        request.kind = "outline"
        request.outline = outline
        request.url = None
        request.path = None
        request.ref = None

        pkg_db = AsyncMock()
        pkg_db.insert_package = AsyncMock(return_value=_REGISTERED_PACKAGE)
        pkg_db.get_package_by_name = AsyncMock(return_value=None)

        result = await _handle_register_outline(request, pkg_db)
        assert result.database_id == 42
        pkg_db.insert_package.assert_awaited_once_with(outline)

    @pytest.mark.asyncio
    async def test_missing_outline_raises_400(self) -> None:
        from sms_api.api.routers.compose import _handle_register_outline

        request = MagicMock()
        request.kind = "outline"
        request.outline = None

        pkg_db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await _handle_register_outline(request, pkg_db)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_duplicate_raises_409(self) -> None:
        from sms_api.api.routers.compose import _handle_register_outline

        outline = PackageOutline(package_type=PackageType.PYPI, name="dup-pkg", compute=[])
        request = MagicMock()
        request.kind = "outline"
        request.outline = outline

        existing = MagicMock()
        existing.database_id = 1
        pkg_db = AsyncMock()
        pkg_db.get_package_by_name = AsyncMock(return_value=existing)

        with pytest.raises(HTTPException) as exc:
            await _handle_register_outline(request, pkg_db)
        assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# _raise_if_audit_failed
# ---------------------------------------------------------------------------


class TestRaiseIfAuditFailed:
    def test_all_pass_no_op(self) -> None:
        from sms_api.api.routers.compose import _raise_if_audit_failed

        _raise_if_audit_failed(_AUDIT_REPORT_PASS, "test-label")  # no error

    def test_fail_raises_400(self) -> None:
        from sms_api.api.routers.compose import _raise_if_audit_failed

        with pytest.raises(HTTPException) as exc:
            _raise_if_audit_failed(_AUDIT_REPORT_FAIL, "test-path")
        assert exc.value.status_code == 400
        assert "FAILED" in exc.value.detail


# ---------------------------------------------------------------------------
# _raise_if_package_exists
# ---------------------------------------------------------------------------


class TestRaiseIfPackageExists:
    @pytest.mark.asyncio
    async def test_not_found_no_op(self) -> None:
        from sms_api.api.routers.compose import _raise_if_package_exists

        pkg_db = AsyncMock()
        pkg_db.get_package_by_name = AsyncMock(return_value=None)
        await _raise_if_package_exists(pkg_db, "nonexistent")  # no error

    @pytest.mark.asyncio
    async def test_found_raises_409(self) -> None:
        from sms_api.api.routers.compose import _raise_if_package_exists

        existing = MagicMock()
        existing.database_id = 1
        pkg_db = AsyncMock()
        pkg_db.get_package_by_name = AsyncMock(return_value=existing)

        with pytest.raises(HTTPException) as exc:
            await _raise_if_package_exists(pkg_db, "existing-pkg")
        assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# _build_outline_from_audit
# ---------------------------------------------------------------------------


class TestBuildOutlineFromAudit:
    def test_basic(self, tmp_path: Path) -> None:
        from sms_api.api.routers.compose import _build_outline_from_audit

        pkg_dir = tmp_path / "pbg-test-build"
        pkg_dir.mkdir()
        (pkg_dir / "pyproject.toml").write_text("""[project]
name = "pbg-test-build"
version = "0.1.0"
""")
        src = pkg_dir / "src"
        src.mkdir()
        (src / "__init__.py").write_text("")
        (src / "processes.py").write_text("""
class MyProcess(Process):
    pass

class MyStep(Step):
    pass
""")

        report = MagicMock()
        report.target = str(pkg_dir)
        report.checks = []
        report.fixes = []

        outline = _build_outline_from_audit(report, pkg_dir)
        assert outline.name == "pbg-test-build"
        assert outline.package_type == PackageType.PYPI
        assert len(outline.compute) == 2
        compute_names = {c.name for c in outline.compute}
        assert "MyProcess" in compute_names
        assert "MyStep" in compute_names

    def test_no_compute_classes(self, tmp_path: Path) -> None:
        from sms_api.api.routers.compose import _build_outline_from_audit

        pkg_dir = tmp_path / "pbg-empty"
        pkg_dir.mkdir()
        (pkg_dir / "pyproject.toml").write_text("""[project]
name = "pbg-empty"
version = "0.1.0"
""")
        src = pkg_dir / "src"
        src.mkdir()
        (src / "__init__.py").write_text("")

        report = MagicMock()
        report.target = str(pkg_dir)
        report.checks = []
        report.fixes = []

        outline = _build_outline_from_audit(report, pkg_dir)
        assert outline.name == "pbg-empty"
        assert outline.compute == []

    def test_fallback_name_from_dir(self, tmp_path: Path) -> None:
        from sms_api.api.routers.compose import _build_outline_from_audit

        pkg_dir = tmp_path / "repo-from-dirname"
        pkg_dir.mkdir()
        (pkg_dir / "pyproject.toml").write_text("""[project]
version = "0.1.0"
""")

        report = MagicMock()
        report.target = str(pkg_dir)
        report.checks = []
        report.fixes = []

        outline = _build_outline_from_audit(report, pkg_dir)
        assert outline.name == "repo-from-dirname"
