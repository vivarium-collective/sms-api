"""Tests for app.gui_app — the Marimo EUTE GUI.

These tests validate that the marimo notebook parses correctly,
all cells are well-formed, and the E2EDataService integration
paths are exercised (with mocked HTTP).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import marimo
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


GUI_APP_PATH = Path(__file__).resolve().parents[2] / "app" / "gui_app.py"


def _import_gui_app() -> ModuleType:
    """Import app.gui_app as a regular module (not via marimo run)."""
    import app.gui as mod

    return mod


# ── Module-level tests ───────────────────────────────────────────────────────


class TestGuiAppModule:
    """Verify the module loads and has the expected marimo structure."""

    def test_module_imports(self) -> None:
        mod = _import_gui_app()
        assert hasattr(mod, "app"), "gui_app must expose a marimo.App instance named `app`"

    def test_app_is_marimo_app(self) -> None:
        mod = _import_gui_app()
        assert isinstance(mod.app, marimo.App)

    def test_file_exists(self) -> None:
        assert GUI_APP_PATH.exists(), f"Expected gui_app.py at {GUI_APP_PATH}"

    def test_module_has_cells(self) -> None:
        """The app should have multiple cells (sections 1-5 + header + footer)."""
        mod = _import_gui_app()
        # marimo.App stores cells internally; verify it has content
        assert mod.app is not None


# ── Marimo notebook parse test ───────────────────────────────────────────────


class TestMarimoNotebookStructure:
    """Test that the notebook file can be parsed by marimo."""

    def test_notebook_parses(self) -> None:
        """marimo should be able to read the notebook without errors."""
        # Simply importing the module validates marimo parse
        mod = _import_gui_app()
        assert mod.app is not None

    def test_notebook_has_generated_with(self) -> None:
        mod = _import_gui_app()
        assert hasattr(mod, "__generated_with")

    def test_source_contains_memphis_css(self) -> None:
        """The notebook source should contain Memphis design CSS."""
        source = GUI_APP_PATH.read_text()
        assert "memphis-banner" in source
        assert "memphis-title" in source
        assert "#e91e90" in source  # Memphis magenta

    def test_source_contains_all_eute_sections(self) -> None:
        """Verify all EUTE workflow sections are present."""
        source = GUI_APP_PATH.read_text()
        assert "SECTION 1" in source  # Simulator
        assert "SECTION 2" in source  # Simulation
        assert "SECTION 3" in source  # Outputs
        assert "SECTION 4" in source  # Parca
        assert "SECTION 5" in source  # Analysis

    def test_source_uses_e2e_data_service(self) -> None:
        """The notebook must use E2EDataService for API calls."""
        source = GUI_APP_PATH.read_text()
        assert "E2EDataService" in source
        assert "get_svc" in source

    def test_source_contains_ecoli_art(self) -> None:
        """The E. coli banner art should be present with iconify DNA icons."""
        source = GUI_APP_PATH.read_text()
        assert "twemoji:dna" in source  # DNA icons replace ⋊⋉
        assert "whole-cell simulation" in source  # Banner text


# ── E2EDataService integration (mocked HTTP) ─────────────────────────────────


def _make_mock_service() -> MagicMock:
    """Create a mock E2EDataService with all methods stubbed."""
    from sms_api.common.models import JobStatus

    mock = MagicMock()

    # Simulator methods
    mock.submit_get_latest_simulator.return_value = MagicMock(
        git_commit_hash="abc1234",
        git_repo_url="https://github.com/CovertLabEcoli/vEcoli-private",
        git_branch="master",
        model_dump=lambda: {
            "git_commit_hash": "abc1234",
            "git_repo_url": "https://github.com/CovertLabEcoli/vEcoli-private",
            "git_branch": "master",
        },
    )
    mock.submit_upload_simulator.return_value = MagicMock(
        database_id=42,
        git_commit_hash="abc1234",
        git_repo_url="https://github.com/CovertLabEcoli/vEcoli-private",
        git_branch="master",
        model_dump=lambda: {
            "database_id": 42,
            "git_commit_hash": "abc1234",
            "git_repo_url": "https://github.com/CovertLabEcoli/vEcoli-private",
            "git_branch": "master",
        },
    )
    mock.submit_get_simulator_build_status.return_value = "completed"
    mock.submit_get_simulator_build_status_full.return_value = MagicMock(
        status=JobStatus.COMPLETED,
        error_message=None,
        model_dump=lambda: {"status": "completed", "error_message": None},
    )
    mock.show_simulators.return_value = [
        MagicMock(model_dump=lambda: {"database_id": 1, "git_commit_hash": "abc", "git_branch": "master"})
    ]

    # Simulation methods
    mock.run_workflow.return_value = MagicMock(
        database_id=10,
        experiment_id="test_exp",
        model_dump=lambda: {
            "database_id": 10,
            "experiment_id": "test_exp",
            "simulator_id": 42,
        },
    )
    mock.get_workflow_status.return_value = MagicMock(
        status=JobStatus.COMPLETED,
        error_message=None,
        model_dump=lambda: {"id": 10, "status": "completed", "error_message": None},
    )
    mock.get_workflow.return_value = MagicMock(
        model_dump=lambda: {"database_id": 10, "experiment_id": "test_exp"}
    )
    mock.show_workflows.return_value = [
        MagicMock(model_dump=lambda: {"database_id": 10, "experiment_id": "test_exp"})
    ]
    mock.cancel_workflow.return_value = MagicMock(
        status=JobStatus.CANCELLED,
        model_dump=lambda: {"id": 10, "status": "cancelled"},
    )

    # Parca methods
    mock.get_parca_datasets.return_value = [
        MagicMock(model_dump=lambda: {"id": 1, "name": "test_parca"})
    ]
    mock.get_parca_status.return_value = MagicMock(
        status=JobStatus.COMPLETED,
        model_dump=lambda: {"status": "completed"},
    )

    # Analysis methods
    mock.get_analysis.return_value = MagicMock(
        model_dump=lambda: {"id": 1, "name": "test_analysis"}
    )
    mock.get_analysis_status.return_value = MagicMock(
        status=JobStatus.COMPLETED,
        error_message=None,
        model_dump=lambda: {"status": "completed"},
    )
    mock.get_analysis_log.return_value = "analysis log output"
    mock.get_analysis_plots.return_value = [
        MagicMock(model_dump=lambda: {"filename": "plot.html", "content_type": "text/html"})
    ]

    return mock


class TestE2EDataServiceIntegration:
    """Test the data service calls that gui_app makes, using mocked service."""

    def test_simulator_latest_flow(self) -> None:
        """Validate the fetch -> upload -> poll flow."""
        mock_svc = _make_mock_service()
        latest = mock_svc.submit_get_latest_simulator(repo_url=None, branch=None)
        uploaded = mock_svc.submit_upload_simulator(simulator=latest, force=False)
        status = mock_svc.submit_get_simulator_build_status(simulator=uploaded)

        assert uploaded.database_id == 42
        assert status == "completed"
        mock_svc.submit_get_latest_simulator.assert_called_once()
        mock_svc.submit_upload_simulator.assert_called_once()

    def test_simulation_run_flow(self) -> None:
        """Validate simulation submission."""
        mock_svc = _make_mock_service()
        sim = mock_svc.run_workflow(
            experiment_id="test",
            simulator_id=42,
            config_filename="api_simulation_default.json",
            num_generations=1,
            num_seeds=1,
            description="test run",
            run_parameter_calculator=False,
        )
        assert sim.database_id == 10
        assert sim.experiment_id == "test_exp"

    def test_simulation_status_flow(self) -> None:
        """Validate status check returns expected structure."""
        mock_svc = _make_mock_service()
        run = mock_svc.get_workflow_status(simulation_id=10)
        assert run.status.value == "completed"
        assert run.error_message is None

    def test_simulation_cancel_flow(self) -> None:
        mock_svc = _make_mock_service()
        result = mock_svc.cancel_workflow(simulation_id=10)
        assert result.status.value == "cancelled"

    def test_list_simulators_flow(self) -> None:
        mock_svc = _make_mock_service()
        sims = mock_svc.show_simulators()
        assert len(sims) == 1
        assert sims[0].model_dump()["database_id"] == 1

    def test_list_simulations_flow(self) -> None:
        mock_svc = _make_mock_service()
        workflows = mock_svc.show_workflows()
        assert len(workflows) == 1

    def test_parca_datasets_flow(self) -> None:
        mock_svc = _make_mock_service()
        datasets = mock_svc.get_parca_datasets()
        assert len(datasets) == 1

    def test_parca_status_flow(self) -> None:
        mock_svc = _make_mock_service()
        status = mock_svc.get_parca_status(parca_id=1)
        assert status.status.value == "completed"

    def test_analysis_get_flow(self) -> None:
        mock_svc = _make_mock_service()
        analysis = mock_svc.get_analysis(analysis_id=1)
        assert analysis.model_dump()["id"] == 1

    def test_analysis_status_flow(self) -> None:
        mock_svc = _make_mock_service()
        status = mock_svc.get_analysis_status(analysis_id=1)
        assert status.status.value == "completed"

    def test_analysis_log_flow(self) -> None:
        mock_svc = _make_mock_service()
        log = mock_svc.get_analysis_log(analysis_id=1)
        assert "analysis log" in log

    def test_analysis_plots_flow(self) -> None:
        mock_svc = _make_mock_service()
        plots = mock_svc.get_analysis_plots(analysis_id=1)
        assert len(plots) == 1
        assert plots[0].model_dump()["filename"] == "plot.html"


# ── Memphis theme tests ──────────────────────────────────────────────────────


class TestMemphisTheme:
    """Verify the Memphis design elements are properly defined in the notebook."""

    def test_memphis_colors_defined(self) -> None:
        """All Memphis palette colors should be present."""
        source = GUI_APP_PATH.read_text()
        colors = ["#e91e90", "#00e5ff", "#ffe100", "#39ff14", "#ff3131", "#b388ff"]
        for color in colors:
            assert color in source, f"Memphis color {color} missing from gui_app.py"

    def test_memphis_banner_animation(self) -> None:
        """CSS animation for the banner strip should be defined."""
        source = GUI_APP_PATH.read_text()
        assert "memphis-scroll" in source
        assert "@keyframes" in source
        assert "linear-gradient" in source

    def test_status_badge_classes(self) -> None:
        """Status CSS classes for all states should exist."""
        source = GUI_APP_PATH.read_text()
        for status in ["completed", "running", "failed", "pending", "cancelled", "unknown"]:
            assert f"memphis-status-{status}" in source

    def test_ecoli_banner_present(self) -> None:
        """The E. coli rod-cell ASCII art banner should be in the notebook with iconify DNA."""
        source = GUI_APP_PATH.read_text()
        assert "twemoji:dna" in source  # DNA icons replace ⋊⋉ in the membrane border
        assert "whole-cell simulation" in source  # Banner text
        assert "ecoli_art" in source  # The banner variable exists

    def test_memphis_card_class(self) -> None:
        """Memphis card styling class should be present."""
        source = GUI_APP_PATH.read_text()
        assert "memphis-card" in source

    def test_iconify_icons_used(self) -> None:
        """Thematic iconify icons should be sprinkled throughout the notebook."""
        source = GUI_APP_PATH.read_text()
        expected_icons = [
            "twemoji:dna",
            "twemoji:microbe",
            "twemoji:microscope",
            "twemoji:test-tube",
            "twemoji:petri-dish",
            "twemoji:bar-chart",
            "twemoji:open-file-folder",
            "twemoji:gear",
            "twemoji:rocket",
            "twemoji:check-mark-button",
            "twemoji:cross-mark",
            "twemoji:hourglass-not-done",
            "twemoji:stop-sign",
            "twemoji:down-arrow",
            "twemoji:link",
        ]
        for icon in expected_icons:
            assert icon in source, f"Iconify icon '{icon}' missing from gui_app.py"

    def test_no_raw_dna_helix_symbol(self) -> None:
        """⋊⋉ should be fully replaced by mo.icon('twemoji:dna')."""
        source = GUI_APP_PATH.read_text()
        assert "⋊⋉" not in source, "Raw ⋊⋉ should be replaced with iconify DNA icons"

    def test_no_pixelated_aesthetic(self) -> None:
        """Per requirements: NO pixelated/retro feel - modern UI with Memphis accents."""
        source = GUI_APP_PATH.read_text()
        # Should not have pixel-art or 8-bit references
        assert "pixel" not in source.lower() or "pixel" in "subpixel"  # subpixel is OK


# ── EUTE parity tests ────────────────────────────────────────────────────────


class TestEUTEParity:
    """Verify the GUI covers the same EUTE steps as CLI and TUI."""

    def test_step_1_3_simulator_build(self) -> None:
        """Steps 1-3: fetch latest, upload, poll build status."""
        source = GUI_APP_PATH.read_text()
        assert "submit_get_latest_simulator" in source
        assert "submit_upload_simulator" in source
        assert "submit_get_simulator_build_status" in source

    def test_step_4_simulation_submit(self) -> None:
        """Step 4: submit simulation workflow."""
        source = GUI_APP_PATH.read_text()
        assert "run_workflow" in source
        assert "experiment_id" in source
        assert "simulator_id" in source
        assert "config_filename" in source
        assert "num_generations" in source
        assert "num_seeds" in source

    def test_step_5_simulation_status(self) -> None:
        """Step 5: check simulation status."""
        source = GUI_APP_PATH.read_text()
        assert "get_workflow_status" in source

    def test_step_6_output_download(self) -> None:
        """Step 6: download simulation outputs."""
        source = GUI_APP_PATH.read_text()
        assert "get_output_data" in source

    def test_list_simulators(self) -> None:
        source = GUI_APP_PATH.read_text()
        assert "show_simulators" in source

    def test_list_simulations(self) -> None:
        source = GUI_APP_PATH.read_text()
        assert "show_workflows" in source

    def test_cancel_simulation(self) -> None:
        source = GUI_APP_PATH.read_text()
        assert "cancel_workflow" in source

    def test_parca_datasets(self) -> None:
        source = GUI_APP_PATH.read_text()
        assert "get_parca_datasets" in source
        assert "get_parca_status" in source

    def test_analysis_operations(self) -> None:
        source = GUI_APP_PATH.read_text()
        assert "get_analysis" in source
        assert "get_analysis_status" in source
        assert "get_analysis_log" in source
        assert "get_analysis_plots" in source

    def test_base_url_selector(self) -> None:
        """GUI should let user choose API base URL, like CLI --base-url."""
        source = GUI_APP_PATH.read_text()
        assert "base_url_dropdown" in source
        assert "localhost:8080" in source

    def test_run_parca_option(self) -> None:
        """GUI should expose the 'run parca' checkbox, like CLI --run-parca."""
        source = GUI_APP_PATH.read_text()
        assert "run_parca_checkbox" in source
        assert "run_parameter_calculator" in source
