"""CLI tests for all `atlantis` command groups.

Tests use Typer's CliRunner with a mocked E2EDataService so they run
offline — no live API, no Docker, no SSH required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from app.cli import cli

runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared mock factory
# ---------------------------------------------------------------------------


def _make_simulator() -> MagicMock:
    m = MagicMock()
    m.git_commit_hash = "abc1234"
    m.git_repo_url = "https://github.com/CovertLabEcoli/vEcoli-private"
    m.git_branch = "master"
    m.model_dump.return_value = {
        "git_commit_hash": "abc1234",
        "git_repo_url": "https://github.com/CovertLabEcoli/vEcoli-private",
        "git_branch": "master",
    }
    return m


def _make_simulator_version(database_id: int = 42) -> MagicMock:
    m = MagicMock()
    m.database_id = database_id
    m.git_commit_hash = "abc1234"
    m.git_repo_url = "https://github.com/CovertLabEcoli/vEcoli-private"
    m.git_branch = "master"
    m.model_dump.return_value = {
        "database_id": database_id,
        "git_commit_hash": "abc1234",
        "git_repo_url": "https://github.com/CovertLabEcoli/vEcoli-private",
        "git_branch": "master",
    }
    return m


def _make_hpc_run(status: str = "completed") -> MagicMock:
    m = MagicMock()
    m.status = status
    m.error_message = None
    m.model_dump.return_value = {"status": status, "error_message": None}
    return m


def _make_simulation(database_id: int = 10, experiment_id: str = "test_exp") -> MagicMock:
    m = MagicMock()
    m.database_id = database_id
    m.experiment_id = experiment_id
    m.model_dump.return_value = {"database_id": database_id, "experiment_id": experiment_id}
    return m


def _make_simulation_run(status: str = "completed") -> MagicMock:
    m = MagicMock()
    m.status = MagicMock()
    m.status.value = status
    m.error_message = None
    m.model_dump.return_value = {"status": status, "error_message": None}
    return m


def _make_repo_discovery() -> MagicMock:
    m = MagicMock()
    m.git_repo_url = "https://github.com/CovertLabEcoli/vEcoli-private"
    m.git_commit_hash = "abc1234"
    m.config_filenames = ["api_simulation_default.json", "api_simulation_custom.json"]
    m.analysis_modules = {
        "single": ["ptools_rna", "ptools_protein"],
        "multiseed": ["ptools_multiseed"],
    }
    return m


def _make_parca_dataset(database_id: int = 5) -> MagicMock:
    m = MagicMock()
    m.database_id = database_id
    m.model_dump.return_value = {"database_id": database_id, "name": "test_parca"}
    return m


def _make_analysis_dto() -> MagicMock:
    m = MagicMock()
    m.model_dump.return_value = {"id": 1, "name": "test_analysis"}
    return m


def _make_analysis_run(status: str = "completed") -> MagicMock:
    m = MagicMock()
    m.status = MagicMock()
    m.status.value = status
    m.error_message = None
    m.model_dump.return_value = {"status": status, "error_message": None}
    return m


def _make_output_file() -> MagicMock:
    m = MagicMock()
    m.filename = "plot.html"
    m.model_dump.return_value = {"filename": "plot.html", "content_type": "text/html"}
    return m


def _mock_svc(**overrides: Any) -> MagicMock:
    svc = MagicMock()

    # Simulator
    svc.submit_get_latest_simulator.return_value = _make_simulator()
    svc.submit_upload_simulator.return_value = _make_simulator_version()
    svc.submit_get_simulator_build_status.return_value = "completed"
    svc.submit_get_simulator_build_status_full.return_value = _make_hpc_run("completed")
    svc.show_simulators.return_value = [_make_simulator_version(1), _make_simulator_version(2)]

    # Simulation
    svc.run_workflow.return_value = _make_simulation()
    svc.get_workflow.return_value = _make_simulation()
    svc.show_workflows.return_value = [_make_simulation(10), _make_simulation(11, "exp2")]
    svc.get_workflow_status.return_value = _make_simulation_run("completed")
    svc.cancel_workflow.return_value = _make_simulation_run("cancelled")
    svc.get_workflow_log.return_value = "Nextflow log output here"
    svc.run_analysis.return_value = {"analysis_id": 99, "status": "submitted"}
    svc.discover_repo.return_value = _make_repo_discovery()

    # Parca
    svc.get_parca_datasets.return_value = [_make_parca_dataset()]
    svc.get_parca_status.return_value = _make_hpc_run("completed")

    # Analysis
    svc.get_analysis.return_value = _make_analysis_dto()
    svc.get_analysis_status.return_value = _make_analysis_run("completed")
    svc.get_analysis_log.return_value = "analysis log output"
    svc.get_analysis_plots.return_value = [_make_output_file()]

    # Compose
    svc.compose_run_simulation.return_value = {
        "simulation_database_id": 20,
        "simulator_database_id": 5,
        "status": "running",
    }
    svc.compose_get_simulation_status.return_value = {"status": "completed", "simulation_database_id": 20}
    svc.compose_get_simulation_results.return_value = Path("/tmp/compose_results.zip")  # noqa: S108
    svc.compose_get_simulation_document.return_value = {"processes": {}, "topology": {}}
    svc.compose_list_simulators.return_value = [{"name": "copasi", "version": "4.0"}]
    svc.compose_list_processes.return_value = ["cobra_fba", "tellurium_ode"]
    svc.compose_list_steps.return_value = ["step1", "step2"]
    svc.compose_get_build_status.return_value = {"status": "completed"}
    svc.compose_run_v2ecoli.return_value = {"simulation_database_id": 21, "simulator_database_id": 6}
    svc.compose_run_copasi.return_value = {"simulation_database_id": 22}
    svc.compose_run_tellurium.return_value = {"simulation_database_id": 23}
    svc.compose_biomodels_identifiers.return_value = ["BIOMD0000000001", "BIOMD0000000002"]
    svc.compose_biomodels_metadata.return_value = {"id": "BIOMD0000000001", "name": "Repressilator"}
    svc.compose_biomodels_run.return_value = {"simulation_database_id": 24}
    svc.compose_biomodels_batch.return_value = {"submitted": ["BIOMD0000000001"], "failed": [], "total_requested": 1}
    svc.compose_biomodels_audit.return_value = {"experiment": {"simulation_database_id": 25}}
    svc.compose_biomodels_regression.return_value = {
        "submitted": ["BIOMD0000000001"],
        "failed": [],
        "total_requested": 1,
    }

    for attr, val in overrides.items():
        setattr(svc, attr, val)
    return svc


# ---------------------------------------------------------------------------
# Help smoke tests — every group must respond to --help
# ---------------------------------------------------------------------------


class TestHelpSmoke:
    @pytest.mark.parametrize(
        "args",
        [
            ["--help"],
            ["simulator", "--help"],
            ["simulation", "--help"],
            ["parca", "--help"],
            ["analysis", "--help"],
            ["compose", "--help"],
        ],
    )
    def test_help_exits_zero(self, args: list[str]) -> None:
        result = runner.invoke(cli, args)
        assert result.exit_code == 0, result.output

    @pytest.mark.parametrize(
        "args",
        [
            ["simulator", "latest", "--help"],
            ["simulator", "list", "--help"],
            ["simulator", "status", "--help"],
            ["simulation", "run", "--help"],
            ["simulation", "list", "--help"],
            ["simulation", "get", "--help"],
            ["simulation", "status", "--help"],
            ["simulation", "configs", "--help"],
            ["simulation", "analyses", "--help"],
            ["simulation", "cancel", "--help"],
            ["simulation", "log", "--help"],
            ["simulation", "outputs", "--help"],
            ["simulation", "analysis", "--help"],
            ["parca", "list", "--help"],
            ["parca", "status", "--help"],
            ["analysis", "get", "--help"],
            ["analysis", "status", "--help"],
            ["analysis", "log", "--help"],
            ["analysis", "plots", "--help"],
            ["compose", "run", "--help"],
            ["compose", "status", "--help"],
            ["compose", "results", "--help"],
            ["compose", "doc", "--help"],
            ["compose", "simulators", "--help"],
            ["compose", "processes", "--help"],
            ["compose", "steps", "--help"],
            ["compose", "build-status", "--help"],
            ["compose", "ecoli", "--help"],
            ["compose", "biomodels-ids", "--help"],
            ["compose", "biomodels-meta", "--help"],
            ["compose", "biomodels-run", "--help"],
            ["compose", "biomodels-batch", "--help"],
            ["compose", "biomodels-audit", "--help"],
            ["compose", "biomodels-regression", "--help"],
            ["compose", "packages", "--help"],
            ["compose", "package-get", "--help"],
            ["compose", "package-audit", "--help"],
            ["compose", "package-register", "--help"],
        ],
    )
    def test_command_help_exits_zero(self, args: list[str]) -> None:
        result = runner.invoke(cli, args)
        assert result.exit_code == 0, result.output

    @pytest.mark.parametrize("group", ["simulator", "simulation", "parca", "analysis", "compose"])
    def test_subgroup_help_command(self, group: str) -> None:
        result = runner.invoke(cli, [group, "help"])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Required-arg validation — commands must fail when required args are missing
# ---------------------------------------------------------------------------


class TestRequiredArgs:
    def test_simulator_status_requires_id(self) -> None:
        result = runner.invoke(cli, ["simulator", "status"])
        assert result.exit_code != 0

    def test_simulation_run_requires_experiment_id(self) -> None:
        result = runner.invoke(cli, ["simulation", "run"])
        assert result.exit_code != 0

    def test_simulation_run_requires_simulator_id(self) -> None:
        result = runner.invoke(cli, ["simulation", "run", "my_exp"])
        assert result.exit_code != 0

    def test_simulation_get_requires_id(self) -> None:
        result = runner.invoke(cli, ["simulation", "get"])
        assert result.exit_code != 0

    def test_simulation_status_requires_id(self) -> None:
        result = runner.invoke(cli, ["simulation", "status"])
        assert result.exit_code != 0

    def test_simulation_configs_requires_id(self) -> None:
        result = runner.invoke(cli, ["simulation", "configs"])
        assert result.exit_code != 0

    def test_simulation_analyses_requires_id(self) -> None:
        result = runner.invoke(cli, ["simulation", "analyses"])
        assert result.exit_code != 0

    def test_simulation_cancel_requires_id(self) -> None:
        result = runner.invoke(cli, ["simulation", "cancel"])
        assert result.exit_code != 0

    def test_simulation_outputs_requires_id(self) -> None:
        result = runner.invoke(cli, ["simulation", "outputs"])
        assert result.exit_code != 0

    def test_parca_status_requires_id(self) -> None:
        result = runner.invoke(cli, ["parca", "status"])
        assert result.exit_code != 0

    def test_analysis_get_requires_id(self) -> None:
        result = runner.invoke(cli, ["analysis", "get"])
        assert result.exit_code != 0

    def test_analysis_status_requires_id(self) -> None:
        result = runner.invoke(cli, ["analysis", "status"])
        assert result.exit_code != 0

    def test_analysis_log_requires_id(self) -> None:
        result = runner.invoke(cli, ["analysis", "log"])
        assert result.exit_code != 0

    def test_analysis_plots_requires_id(self) -> None:
        result = runner.invoke(cli, ["analysis", "plots"])
        assert result.exit_code != 0

    def test_compose_status_requires_id(self) -> None:
        result = runner.invoke(cli, ["compose", "status"])
        assert result.exit_code != 0

    def test_compose_results_requires_id(self) -> None:
        result = runner.invoke(cli, ["compose", "results"])
        assert result.exit_code != 0

    def test_compose_doc_requires_id(self) -> None:
        result = runner.invoke(cli, ["compose", "doc"])
        assert result.exit_code != 0

    def test_compose_build_status_requires_id(self) -> None:
        result = runner.invoke(cli, ["compose", "build-status"])
        assert result.exit_code != 0

    def test_compose_biomodels_meta_requires_id(self) -> None:
        result = runner.invoke(cli, ["compose", "biomodels-meta"])
        assert result.exit_code != 0

    def test_compose_biomodels_run_requires_id(self) -> None:
        result = runner.invoke(cli, ["compose", "biomodels-run"])
        assert result.exit_code != 0

    def test_compose_biomodels_audit_requires_id(self) -> None:
        result = runner.invoke(cli, ["compose", "biomodels-audit"])
        assert result.exit_code != 0

    def test_compose_package_get_requires_id(self) -> None:
        result = runner.invoke(cli, ["compose", "package-get"])
        assert result.exit_code != 0

    def test_compose_package_audit_requires_target(self) -> None:
        result = runner.invoke(cli, ["compose", "package-audit"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Simulator commands
# ---------------------------------------------------------------------------


class TestSimulatorLatest:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulator", "latest"])
        assert result.exit_code == 0, result.output

    def test_prints_simulator_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulator", "latest"])
        assert "42" in result.output

    def test_prints_commit_hash(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulator", "latest"])
        assert "abc1234" in result.output

    def test_calls_get_latest_simulator(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            runner.invoke(cli, ["simulator", "latest"])
        svc.submit_get_latest_simulator.assert_called_once()

    def test_calls_upload_simulator(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            runner.invoke(cli, ["simulator", "latest"])
        svc.submit_upload_simulator.assert_called_once()

    def test_passes_repo_url_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            runner.invoke(cli, ["simulator", "latest", "--repo-url", "https://github.com/test/repo"])
        call_kwargs = svc.submit_get_latest_simulator.call_args
        assert call_kwargs.kwargs["repo_url"] == "https://github.com/test/repo"

    def test_passes_branch_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            runner.invoke(cli, ["simulator", "latest", "--branch", "develop"])
        call_kwargs = svc.submit_get_latest_simulator.call_args
        assert call_kwargs.kwargs["branch"] == "develop"

    def test_polls_until_completed(self) -> None:
        svc = _mock_svc()
        svc.submit_get_simulator_build_status.side_effect = ["running", "running", "completed"]
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulator", "latest"])
        assert result.exit_code == 0, result.output
        assert svc.submit_get_simulator_build_status.call_count == 3

    def test_completed_status_shown(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulator", "latest"])
        assert "COMPLETED" in result.output.upper() or "completed" in result.output.lower()


class TestSimulatorList:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulator", "list"])
        assert result.exit_code == 0, result.output

    def test_calls_show_simulators(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulator", "list"])
        svc.show_simulators.assert_called_once()

    def test_empty_list_exits_zero(self) -> None:
        svc = _mock_svc()
        svc.show_simulators.return_value = []
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulator", "list"])
        assert result.exit_code == 0

    def test_n_option_slices_results(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulator", "list", "--n", "1"])
        assert result.exit_code == 0


class TestSimulatorStatus:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulator", "status", "42"])
        assert result.exit_code == 0, result.output

    def test_prints_status_badge(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulator", "status", "42"])
        assert "COMPLETED" in result.output.upper() or "completed" in result.output.lower()

    def test_passes_simulator_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulator", "status", "99"])
        svc.submit_get_simulator_build_status_full.assert_called_once_with(simulator_id=99)

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.submit_get_simulator_build_status_full.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulator", "status", "1"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Simulation commands
# ---------------------------------------------------------------------------


class TestSimulationRun:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42"])
        assert result.exit_code == 0, result.output

    def test_prints_simulation_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42"])
        assert "10" in result.output

    def test_passes_experiment_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "run", "myexp", "42"])
        call_kwargs = svc.run_workflow.call_args.kwargs
        assert call_kwargs["experiment_id"] == "myexp"

    def test_passes_simulator_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "run", "myexp", "42"])
        call_kwargs = svc.run_workflow.call_args.kwargs
        assert call_kwargs["simulator_id"] == 42

    def test_passes_generations_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "run", "myexp", "42", "--generations", "5"])
        call_kwargs = svc.run_workflow.call_args.kwargs
        assert call_kwargs["num_generations"] == 5

    def test_passes_seeds_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "run", "myexp", "42", "--seeds", "10"])
        call_kwargs = svc.run_workflow.call_args.kwargs
        assert call_kwargs["num_seeds"] == 10

    def test_passes_run_parca_flag(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "run", "myexp", "42", "--run-parca"])
        call_kwargs = svc.run_workflow.call_args.kwargs
        assert call_kwargs["run_parameter_calculator"] is True

    def test_passes_observables_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "run", "myexp", "42", "--observables", "bulk,listeners.mass.cell_mass"])
        call_kwargs = svc.run_workflow.call_args.kwargs
        assert call_kwargs["observables"] == ["bulk", "listeners.mass.cell_mass"]

    def test_passes_analysis_options_json(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(
                cli,
                ["simulation", "run", "myexp", "42", "--analysis-options", '{"multiseed": {"ptools_rna": {}}}'],
            )
        call_kwargs = svc.run_workflow.call_args.kwargs
        assert call_kwargs["analysis_options"] == {"multiseed": {"ptools_rna": {}}}

    def test_prints_track_progress_hint(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42"])
        assert "status" in result.output.lower() or "10" in result.output

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.run_workflow.side_effect = RuntimeError("server error")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42"])
        assert result.exit_code != 0


class TestSimulationRunPoll:
    def test_poll_exits_zero_on_completion(self) -> None:
        svc = _mock_svc()
        svc.get_workflow_status.return_value = _make_simulation_run("completed")
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42", "--poll"])
        assert result.exit_code == 0, result.output

    def test_poll_shows_final_status(self) -> None:
        svc = _mock_svc()
        svc.get_workflow_status.return_value = _make_simulation_run("completed")
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42", "--poll"])
        assert "COMPLETED" in result.output.upper() or "completed" in result.output.lower()

    def test_poll_loops_until_terminal(self) -> None:
        svc = _mock_svc()
        svc.get_workflow_status.side_effect = [
            _make_simulation_run("running"),
            _make_simulation_run("running"),
            _make_simulation_run("completed"),
        ]
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42", "--poll"])
        assert result.exit_code == 0
        assert svc.get_workflow_status.call_count == 3

    def test_poll_terminates_on_failed(self) -> None:
        svc = _mock_svc()
        svc.get_workflow_status.return_value = _make_simulation_run("failed")
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42", "--poll"])
        assert result.exit_code == 0  # command exits clean even on failed sim

    def test_poll_terminates_on_cancelled(self) -> None:
        svc = _mock_svc()
        svc.get_workflow_status.return_value = _make_simulation_run("cancelled")
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42", "--poll"])
        assert result.exit_code == 0


class TestSimulationGet:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "get", "10"])
        assert result.exit_code == 0, result.output

    def test_passes_simulation_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "get", "10"])
        svc.get_workflow.assert_called_once_with(simulation_id=10)

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.get_workflow.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "get", "999"])
        assert result.exit_code != 0


class TestSimulationList:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "list"])
        assert result.exit_code == 0, result.output

    def test_calls_show_workflows(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "list"])
        svc.show_workflows.assert_called_once()

    def test_empty_list_exits_zero(self) -> None:
        svc = _mock_svc()
        svc.show_workflows.return_value = []
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "list"])
        assert result.exit_code == 0


class TestSimulationConfigs:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "configs", "42"])
        assert result.exit_code == 0, result.output

    def test_prints_config_names(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "configs", "42"])
        assert "api_simulation_default.json" in result.output

    def test_passes_simulator_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "configs", "42"])
        svc.discover_repo.assert_called_once_with(simulator_id=42)

    def test_no_configs_prints_fallback_message(self) -> None:
        svc = _mock_svc()
        svc.discover_repo.return_value.config_filenames = []
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "configs", "42"])
        assert result.exit_code == 0
        assert "No config" in result.output or "default" in result.output


class TestSimulationAnalyses:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "analyses", "42"])
        assert result.exit_code == 0, result.output

    def test_prints_module_names(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "analyses", "42"])
        assert "ptools_rna" in result.output

    def test_prints_category_headers(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "analyses", "42"])
        assert "single" in result.output or "multiseed" in result.output

    def test_no_modules_prints_fallback_message(self) -> None:
        svc = _mock_svc()
        svc.discover_repo.return_value.analysis_modules = {}
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "analyses", "42"])
        assert result.exit_code == 0
        assert "No analysis" in result.output or "discovered" in result.output


class TestSimulationStatus:
    def test_exits_zero_no_poll(self) -> None:
        with patch("sms_api.common.handlers.simulations.workflow_log") as mock_log:
            mock_log.return_value = None
            result = runner.invoke(cli, ["simulation", "status", "10"])
        assert result.exit_code == 0, result.output

    def test_calls_workflow_log_no_poll(self) -> None:
        with patch("sms_api.common.handlers.simulations.workflow_log") as mock_log:
            mock_log.return_value = None
            runner.invoke(cli, ["simulation", "status", "10"])
        mock_log.assert_called_once()

    def test_poll_exits_zero_on_completion(self) -> None:
        svc = _mock_svc()
        svc.get_workflow_status.return_value = _make_simulation_run("completed")
        with (
            patch("app.cli.get_data_service", return_value=svc),
            patch("time.sleep"),
            patch("sms_api.common.handlers.simulations.workflow_log"),
        ):
            result = runner.invoke(cli, ["simulation", "status", "10", "--poll"])
        assert result.exit_code == 0, result.output


class TestSimulationCancel:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "cancel", "10"])
        assert result.exit_code == 0, result.output

    def test_passes_simulation_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "cancel", "10"])
        svc.cancel_workflow.assert_called_once_with(simulation_id=10)

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.cancel_workflow.side_effect = RuntimeError("already completed")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "cancel", "10"])
        assert result.exit_code != 0


class TestSimulationLog:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "log", "10"])
        assert result.exit_code == 0, result.output

    def test_prints_log_content(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "log", "10"])
        assert "Nextflow log" in result.output

    def test_passes_simulation_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "log", "10"])
        svc.get_workflow_log.assert_called_once_with(simulation_id=10, truncate=False)


class TestSimulationOutputs:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        fake_path = Path("/tmp/test_exp")  # noqa: S108
        svc.get_output_data = AsyncMock(return_value=fake_path)
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "outputs", "10"])
        assert result.exit_code == 0, result.output

    def test_prints_output_path(self) -> None:
        svc = _mock_svc()
        fake_path = Path("/tmp/test_exp")  # noqa: S108
        svc.get_output_data = AsyncMock(return_value=fake_path)
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "outputs", "10"])
        assert "test_exp" in result.output or "/tmp" in result.output  # noqa: S108

    def test_passes_simulation_id(self) -> None:
        svc = _mock_svc()
        fake_path = Path("/tmp/test_exp")  # noqa: S108
        svc.get_output_data = AsyncMock(return_value=fake_path)
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "outputs", "10"])
        svc.get_output_data.assert_called_once()
        call_kwargs = svc.get_output_data.call_args.kwargs
        assert call_kwargs["simulation_id"] == 10

    def test_dest_option_passed(self) -> None:
        svc = _mock_svc()
        fake_path = Path("/tmp/custom_dir/test_exp")  # noqa: S108
        svc.get_output_data = AsyncMock(return_value=fake_path)
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "outputs", "10", "--dest", "/tmp/custom_dir"])  # noqa: S108
        call_kwargs = svc.get_output_data.call_args.kwargs
        assert call_kwargs["dest"] == Path("/tmp/custom_dir")  # noqa: S108


class TestSimulationAnalysisCommand:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "analysis", "10"])
        assert result.exit_code == 0, result.output

    def test_passes_simulation_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["simulation", "analysis", "10"])
        svc.run_analysis.assert_called_once_with(simulation_id=10, modules=None)

    def test_passes_modules_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(
                cli,
                ["simulation", "analysis", "10", "--modules", '{"multiseed": {"ptools_rna": {}}}'],
            )
        call_kwargs = svc.run_analysis.call_args.kwargs
        assert call_kwargs["modules"] is not None

    def test_prints_analysis_submitted(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "analysis", "10"])
        assert "Analysis submitted" in result.output or "submitted" in result.output.lower()


# ---------------------------------------------------------------------------
# Parca commands
# ---------------------------------------------------------------------------


class TestParcaList:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["parca", "list"])
        assert result.exit_code == 0, result.output

    def test_calls_get_parca_datasets(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["parca", "list"])
        svc.get_parca_datasets.assert_called_once()

    def test_empty_list_exits_zero(self) -> None:
        svc = _mock_svc()
        svc.get_parca_datasets.return_value = []
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["parca", "list"])
        assert result.exit_code == 0

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.get_parca_datasets.side_effect = RuntimeError("db error")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["parca", "list"])
        assert result.exit_code != 0


class TestParcaStatus:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["parca", "status", "5"])
        assert result.exit_code == 0, result.output

    def test_passes_parca_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["parca", "status", "5"])
        svc.get_parca_status.assert_called_once_with(parca_id=5)

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.get_parca_status.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["parca", "status", "5"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Analysis commands
# ---------------------------------------------------------------------------


class TestAnalysisGet:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "get", "1"])
        assert result.exit_code == 0, result.output

    def test_passes_analysis_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["analysis", "get", "1"])
        svc.get_analysis.assert_called_once_with(analysis_id=1)

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.get_analysis.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "get", "1"])
        assert result.exit_code != 0


class TestAnalysisStatus:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "status", "1"])
        assert result.exit_code == 0, result.output

    def test_passes_analysis_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["analysis", "status", "1"])
        svc.get_analysis_status.assert_called_once_with(analysis_id=1)

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.get_analysis_status.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "status", "1"])
        assert result.exit_code != 0


class TestAnalysisLog:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "log", "1"])
        assert result.exit_code == 0, result.output

    def test_prints_log_content(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "log", "1"])
        assert "analysis log" in result.output.lower()

    def test_passes_analysis_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["analysis", "log", "1"])
        svc.get_analysis_log.assert_called_once_with(analysis_id=1)


class TestAnalysisPlots:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "plots", "1"])
        assert result.exit_code == 0, result.output

    def test_prints_plot_info(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "plots", "1"])
        assert "plot.html" in result.output

    def test_passes_analysis_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["analysis", "plots", "1"])
        svc.get_analysis_plots.assert_called_once_with(analysis_id=1)

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.get_analysis_plots.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["analysis", "plots", "1"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Compose commands (smoke tests)
# ---------------------------------------------------------------------------


class TestComposeStatus:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "status", "20"])
        assert result.exit_code == 0, result.output

    def test_prints_status_badge(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "status", "20"])
        assert "COMPLETED" in result.output.upper() or "completed" in result.output.lower()

    def test_passes_simulation_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "status", "20"])
        svc.compose_get_simulation_status.assert_called_once_with(simulation_id=20)

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_svc()
        svc.compose_get_simulation_status.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "status", "20"])
        assert result.exit_code != 0


class TestComposeResults:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "results", "20"])
        assert result.exit_code == 0, result.output

    def test_passes_simulation_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "results", "20"])
        svc.compose_get_simulation_results.assert_called_once()
        assert svc.compose_get_simulation_results.call_args.kwargs["simulation_id"] == 20


class TestComposeDoc:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "doc", "20"])
        assert result.exit_code == 0, result.output

    def test_passes_simulation_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "doc", "20"])
        svc.compose_get_simulation_document.assert_called_once_with(simulation_id=20)


class TestComposeSimulators:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "simulators"])
        assert result.exit_code == 0, result.output

    def test_calls_list_simulators(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "simulators"])
        svc.compose_list_simulators.assert_called_once()


class TestComposeProcesses:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "processes"])
        assert result.exit_code == 0, result.output

    def test_empty_prints_no_processes_message(self) -> None:
        svc = _mock_svc()
        svc.compose_list_processes.return_value = []
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "processes"])
        assert result.exit_code == 0
        assert "No processes" in result.output


class TestComposeSteps:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "steps"])
        assert result.exit_code == 0, result.output

    def test_empty_prints_no_steps_message(self) -> None:
        svc = _mock_svc()
        svc.compose_list_steps.return_value = []
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "steps"])
        assert result.exit_code == 0
        assert "No steps" in result.output


class TestComposeBuildStatus:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "build-status", "5"])
        assert result.exit_code == 0, result.output

    def test_passes_simulator_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "build-status", "5"])
        svc.compose_get_build_status.assert_called_once_with(simulator_id=5)


class TestComposeBiomodelsIds:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "biomodels-ids"])
        assert result.exit_code == 0, result.output

    def test_prints_ids(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "biomodels-ids"])
        assert "BIOMD" in result.output

    def test_passes_n_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "biomodels-ids", "--n", "5"])
        svc.compose_biomodels_identifiers.assert_called_once_with(n=5)


class TestComposeBiomodelsMeta:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "biomodels-meta", "BIOMD0000000001"])
        assert result.exit_code == 0, result.output

    def test_passes_biomodel_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "biomodels-meta", "BIOMD0000000001"])
        svc.compose_biomodels_metadata.assert_called_once_with(biomodel_id="BIOMD0000000001")


class TestComposeBiomodelsRun:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "biomodels-run", "BIOMD0000000001"])
        assert result.exit_code == 0, result.output

    def test_passes_biomodel_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "biomodels-run", "BIOMD0000000001"])
        svc.compose_biomodels_run.assert_called_once_with(biomodel_id="BIOMD0000000001", simulator="copasi")

    def test_passes_simulator_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(
                cli,
                ["compose", "biomodels-run", "BIOMD0000000001", "--simulator", "tellurium"],
            )
        svc.compose_biomodels_run.assert_called_once_with(biomodel_id="BIOMD0000000001", simulator="tellurium")


class TestComposeBiomodelsBatch:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "biomodels-batch"])
        assert result.exit_code == 0, result.output

    def test_passes_ids_option(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(
                cli,
                ["compose", "biomodels-batch", "--ids", "BIOMD0000000001,BIOMD0000000002"],
            )
        call_kwargs = svc.compose_biomodels_batch.call_args.kwargs
        assert call_kwargs["model_ids"] == ["BIOMD0000000001", "BIOMD0000000002"]


class TestComposeBiomodelsAudit:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "biomodels-audit", "BIOMD0000000001"])
        assert result.exit_code == 0, result.output

    def test_passes_biomodel_id(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "biomodels-audit", "BIOMD0000000001"])
        svc.compose_biomodels_audit.assert_called_once()
        call_kwargs = svc.compose_biomodels_audit.call_args.kwargs
        assert call_kwargs["biomodel_id"] == "BIOMD0000000001"


class TestComposeBiomodelsRegression:
    def test_exits_zero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "biomodels-regression"])
        assert result.exit_code == 0, result.output

    def test_prints_summary_line(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "biomodels-regression"])
        assert "submitted" in result.output.lower() or "Regression" in result.output


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_connection_error_exits_nonzero(self) -> None:
        import httpx

        svc = _mock_svc()
        svc.submit_get_latest_simulator.side_effect = httpx.ConnectError("Connection refused")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulator", "latest"])
        assert result.exit_code != 0

    def test_http_status_error_exits_nonzero(self) -> None:
        import httpx

        svc = _mock_svc()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = '{"detail": "Internal server error"}'
        svc.run_workflow.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["simulation", "run", "myexp", "42"])
        assert result.exit_code != 0

    def test_invalid_json_analysis_options_exits_nonzero(self) -> None:
        svc = _mock_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(
                cli,
                ["simulation", "run", "myexp", "42", "--analysis-options", "not-valid-json{{{"],
            )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Package commands
# ---------------------------------------------------------------------------


_PACKAGE_LISTING: dict[str, object] = {
    "id": 1,
    "name": "pbg-test-pkg",
    "package_type": "pypi",
    "num_processes": 2,
    "num_steps": 1,
}

_PACKAGE_FULL: dict[str, object] = {
    "database_id": 1,
    "package_type": "pypi",
    "name": "pbg-test-pkg",
    "processes": [
        {"name": "TestProcess", "module": "test.module", "compute_type": "process", "inputs": "{}", "outputs": "{}"},
    ],
    "steps": [],
}

_AUDIT_RESULT: dict[str, object] = {
    "target": "/mock/test-repo",
    "checks": [
        {"name": "pyproject.toml", "status": "PASS", "detail": "found"},
        {"name": "bigraph-schema dep", "status": "PASS", "detail": "bigraph-schema>=0.0.60"},
        {"name": "process-bigraph dep", "status": "PASS", "detail": "process-bigraph>=0.0.66"},
    ],
    "fixes": [],
    "summary": "All 3 checks passed.",
}


def _mock_pkg_svc(**overrides: object) -> MagicMock:
    svc = MagicMock()
    svc.compose_list_packages.return_value = [_PACKAGE_LISTING]
    svc.compose_get_package.return_value = _PACKAGE_FULL
    svc.compose_audit_package.return_value = _AUDIT_RESULT
    svc.compose_register_package.return_value = _PACKAGE_FULL
    for attr, val in overrides.items():
        setattr(svc, attr, val)
    return svc


class TestComposePackages:
    def test_exits_zero(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "packages"])
        assert result.exit_code == 0, result.output

    def test_calls_list_packages(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "packages"])
        svc.compose_list_packages.assert_called_once()

    def test_prints_package_name(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "packages"])
        assert "pbg-test-pkg" in result.output

    def test_empty_list_prints_no_packages_message(self) -> None:
        svc = _mock_pkg_svc()
        svc.compose_list_packages.return_value = []
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "packages"])
        assert result.exit_code == 0
        assert "No packages registered" in result.output

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_pkg_svc()
        svc.compose_list_packages.side_effect = RuntimeError("db error")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "packages"])
        assert result.exit_code != 0


class TestComposePackageGet:
    def test_exits_zero(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-get", "1"])
        assert result.exit_code == 0, result.output

    def test_calls_get_package(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "package-get", "42"])
        svc.compose_get_package.assert_called_once_with(package_id=42)

    def test_prints_package_data(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-get", "1"])
        assert "pbg-test-pkg" in result.output

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_pkg_svc()
        svc.compose_get_package.side_effect = RuntimeError("not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-get", "999"])
        assert result.exit_code != 0


class TestComposePackageAudit:
    def test_exits_zero(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-audit", "/mock/test-repo"])
        assert result.exit_code == 0, result.output

    def test_calls_audit_package(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "package-audit", "/mock/test-repo"])
        svc.compose_audit_package.assert_called_once_with(target="/mock/test-repo", ref=None, run_install=False)

    def test_passes_ref_option(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "package-audit", "/mock/test-repo", "--ref", "main"])
        svc.compose_audit_package.assert_called_once_with(target="/mock/test-repo", ref="main", run_install=False)

    def test_passes_install_option(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "package-audit", "/mock/test-repo", "--install"])
        svc.compose_audit_package.assert_called_once_with(target="/mock/test-repo", ref=None, run_install=True)

    def test_prints_checks(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-audit", "/mock/test-repo"])
        assert "PASS" in result.output
        assert "pyproject.toml" in result.output

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_pkg_svc()
        svc.compose_audit_package.side_effect = RuntimeError("path not found")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-audit", "/nonexistent"])
        assert result.exit_code != 0


class TestComposePackageRegister:
    def test_exits_zero_with_target(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-register", "/mock/test-repo", "--no-audit"])
        assert result.exit_code == 0, result.output

    def test_calls_register_local_path(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(cli, ["compose", "package-register", "/mock/test-repo", "--no-audit"])
        svc.compose_register_package.assert_called_once_with(kind="local_path", path="/mock/test-repo")

    def test_audit_then_register(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-register", "/mock/test-repo"])
        assert result.exit_code == 0, result.output
        svc.compose_audit_package.assert_called_once_with(target="/mock/test-repo", ref=None)
        svc.compose_register_package.assert_called_once_with(kind="local_path", path="/mock/test-repo")

    def test_audit_fails_aborts_register(self) -> None:
        svc = _mock_pkg_svc()
        svc.compose_audit_package.return_value = {
            "target": "/mock/fail-repo",
            "checks": [{"name": "pyproject.toml", "status": "FAIL", "detail": "missing"}],
            "fixes": ["Create pyproject.toml"],
            "summary": "1 check failed.",
        }
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-register", "/mock/fail-repo"])
        assert result.exit_code == 0  # CLI handles audit failure gracefully
        assert "FAIL" in result.output
        assert "Aborting" in result.output
        svc.compose_register_package.assert_not_called()

    def test_repo_url_registers_as_url(self) -> None:
        svc = _mock_pkg_svc()
        svc.compose_audit_package.return_value = _AUDIT_RESULT
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(
                cli,
                ["compose", "package-register", "https://github.com/vivarium-collective/pbg-test", "--no-audit"],
            )
        svc.compose_register_package.assert_called_once_with(
            kind="repo_url", url="https://github.com/vivarium-collective/pbg-test", ref=None
        )

    def test_register_with_ref(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            runner.invoke(
                cli,
                ["compose", "package-register", "/mock/test-repo", "--no-audit", "--ref", "develop"],
            )
        svc.compose_register_package.assert_called_once_with(kind="local_path", path="/mock/test-repo")

    def test_register_from_file(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        svc = _mock_pkg_svc()
        outline = {"package_type": "pypi", "name": "file-pkg", "compute": []}
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".json"))  # noqa: S306
        tmp.write_text(json.dumps(outline))
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-register", "--from-file", str(tmp)])
        assert result.exit_code == 0, result.output
        svc.compose_register_package.assert_called_once_with(kind="outline", outline=outline)
        tmp.unlink()

    def test_no_target_no_file_prints_error(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-register"])
        assert result.exit_code != 0

    def test_prints_success_message(self) -> None:
        svc = _mock_pkg_svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-register", "/mock/test-repo", "--no-audit"])
        assert "registered successfully" in result.output.lower()

    def test_service_error_exits_nonzero(self) -> None:
        svc = _mock_pkg_svc()
        svc.compose_register_package.side_effect = RuntimeError("duplicate name")
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli, ["compose", "package-register", "/mock/test-repo", "--no-audit"])
        assert result.exit_code != 0
