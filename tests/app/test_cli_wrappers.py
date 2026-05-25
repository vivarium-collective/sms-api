"""CLI tests for `atlantis compose wrapper-*` commands.

Tests use Typer's CliRunner with a mocked E2EDataService so they run
offline — no live API, no Docker, no SSH required.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from app.cli import cli

runner = CliRunner()

# ---------------------------------------------------------------------------
# Shared mock fixture
# ---------------------------------------------------------------------------

_WRAPPER_RECORD: dict[str, Any] = {
    "wrapper_id": 7,
    "tool_name": "mem3dg",
    "source_repo_url": "https://github.com/vivarium-collective/mem3dg",
    "source_ref": "main",
    "status": "generating",
    "simulator_id": None,
    "storage_uri": None,
    "error_message": None,
    "created_at": "2026-05-11T00:00:00",
}

_WRAPPER_AVAILABLE: dict[str, Any] = {**_WRAPPER_RECORD, "status": "available", "simulator_id": 42}


def _mock_svc(**overrides: Any) -> MagicMock:
    svc = MagicMock()
    svc.compose_create_wrapper.return_value = _WRAPPER_RECORD
    svc.compose_get_wrapper_status.return_value = _WRAPPER_AVAILABLE
    svc.compose_list_wrappers.return_value = [_WRAPPER_AVAILABLE]
    for attr, val in overrides.items():
        setattr(svc, attr, val)
    return svc


# ---------------------------------------------------------------------------
# wrapper-create
# ---------------------------------------------------------------------------


class TestWrapperCreate:
    def test_create_exits_zero(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(
                cli,
                ["compose", "wrapper-create", "https://github.com/vivarium-collective/mem3dg"],
            )
        assert result.exit_code == 0, result.output

    def test_create_prints_wrapper_id(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(
                cli,
                ["compose", "wrapper-create", "https://github.com/vivarium-collective/mem3dg"],
            )
        assert "7" in result.output

    def test_create_passes_repo_url(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            runner.invoke(
                cli,
                ["compose", "wrapper-create", "https://github.com/vivarium-collective/mem3dg"],
            )
        mock_svc.compose_create_wrapper.assert_called_once()
        call_kwargs = mock_svc.compose_create_wrapper.call_args
        assert call_kwargs.kwargs["source_repo_url"] == "https://github.com/vivarium-collective/mem3dg"

    def test_create_with_tool_name_override(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            runner.invoke(
                cli,
                [
                    "compose",
                    "wrapper-create",
                    "https://github.com/vivarium-collective/mem3dg",
                    "--tool-name",
                    "mymesh",
                ],
            )
        call_kwargs = mock_svc.compose_create_wrapper.call_args
        assert call_kwargs.kwargs["tool_name"] == "mymesh"

    def test_create_with_ref_option(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            runner.invoke(
                cli,
                [
                    "compose",
                    "wrapper-create",
                    "https://github.com/vivarium-collective/mem3dg",
                    "--ref",
                    "dev",
                ],
            )
        call_kwargs = mock_svc.compose_create_wrapper.call_args
        assert call_kwargs.kwargs["source_ref"] == "dev"

    def test_create_with_instructions(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            runner.invoke(
                cli,
                [
                    "compose",
                    "wrapper-create",
                    "https://github.com/vivarium-collective/mem3dg",
                    "--instructions",
                    "focus on the membrane model",
                ],
            )
        call_kwargs = mock_svc.compose_create_wrapper.call_args
        assert call_kwargs.kwargs["extra_instructions"] == "focus on the membrane model"

    def test_create_poll_terminates_on_available(self) -> None:
        """--poll should stop the loop once status == 'available'."""
        mock_svc = _mock_svc()
        # First call returns 'generating', second returns 'available'
        import time

        mock_svc.compose_get_wrapper_status.side_effect = [
            {**_WRAPPER_RECORD, "status": "available"},
        ]
        with patch("app.cli.get_data_service", return_value=mock_svc), patch.object(time, "sleep"):
            result = runner.invoke(
                cli,
                [
                    "compose",
                    "wrapper-create",
                    "https://github.com/vivarium-collective/mem3dg",
                    "--poll",
                ],
            )
        assert result.exit_code == 0
        assert "AVAILABLE" in result.output

    def test_create_service_error_exits_nonzero(self) -> None:
        mock_svc = _mock_svc()
        mock_svc.compose_create_wrapper.side_effect = RuntimeError("connection refused")
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(
                cli,
                ["compose", "wrapper-create", "https://github.com/vivarium-collective/mem3dg"],
            )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# wrapper-status
# ---------------------------------------------------------------------------


class TestWrapperStatus:
    def test_status_exits_zero(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(cli, ["compose", "wrapper-status", "7"])
        assert result.exit_code == 0, result.output

    def test_status_prints_status_badge(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(cli, ["compose", "wrapper-status", "7"])
        assert "AVAILABLE" in result.output

    def test_status_passes_wrapper_id(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            runner.invoke(cli, ["compose", "wrapper-status", "42"])
        mock_svc.compose_get_wrapper_status.assert_called_once_with(wrapper_id=42)

    def test_status_service_error_exits_nonzero(self) -> None:
        mock_svc = _mock_svc()
        mock_svc.compose_get_wrapper_status.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(cli, ["compose", "wrapper-status", "99"])
        assert result.exit_code != 0

    def test_status_requires_wrapper_id(self) -> None:
        result = runner.invoke(cli, ["compose", "wrapper-status"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# wrapper-list
# ---------------------------------------------------------------------------


class TestWrapperList:
    def test_list_exits_zero(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(cli, ["compose", "wrapper-list"])
        assert result.exit_code == 0, result.output

    def test_list_prints_wrapper_data(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(cli, ["compose", "wrapper-list"])
        assert "mem3dg" in result.output

    def test_list_empty_prints_no_wrappers_message(self) -> None:
        mock_svc = _mock_svc()
        mock_svc.compose_list_wrappers.return_value = []
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(cli, ["compose", "wrapper-list"])
        assert result.exit_code == 0
        assert "No wrappers found" in result.output

    def test_list_passes_status_filter(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            runner.invoke(cli, ["compose", "wrapper-list", "--status", "available"])
        mock_svc.compose_list_wrappers.assert_called_once_with(status="available")

    def test_list_no_status_filter_passes_none(self) -> None:
        mock_svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=mock_svc):
            runner.invoke(cli, ["compose", "wrapper-list"])
        mock_svc.compose_list_wrappers.assert_called_once_with(status=None)

    def test_list_service_error_exits_nonzero(self) -> None:
        mock_svc = _mock_svc()
        mock_svc.compose_list_wrappers.side_effect = RuntimeError("db error")
        with patch("app.cli.get_data_service", return_value=mock_svc):
            result = runner.invoke(cli, ["compose", "wrapper-list"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Help smoke tests
# ---------------------------------------------------------------------------


class TestWrapperHelp:
    @pytest.mark.parametrize("cmd", ["wrapper-create", "wrapper-status", "wrapper-list"])
    def test_help_exits_zero(self, cmd: str) -> None:
        result = runner.invoke(cli, ["compose", cmd, "--help"])
        assert result.exit_code == 0

    def test_wrapper_create_help_mentions_repo_url(self) -> None:
        result = runner.invoke(cli, ["compose", "wrapper-create", "--help"])
        assert "repo-url" in result.output.lower() or "github" in result.output.lower()

    def test_wrapper_status_help_mentions_wrapper_id(self) -> None:
        result = runner.invoke(cli, ["compose", "wrapper-status", "--help"])
        assert "wrapper" in result.output.lower()

    def test_wrapper_list_help_mentions_status_filter(self) -> None:
        result = runner.invoke(cli, ["compose", "wrapper-list", "--help"])
        assert "status" in result.output.lower()
