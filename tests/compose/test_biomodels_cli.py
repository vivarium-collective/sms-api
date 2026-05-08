"""CLI tests for biomodels-* commands in app.cli."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from app.cli import cli as cli_app

runner = CliRunner()


def _mock_data_service(method_results: dict[str, object]) -> MagicMock:
    svc = MagicMock()
    for method, return_value in method_results.items():
        getattr(svc, method).return_value = return_value
    return svc


# ---------------------------------------------------------------------------
# biomodels-ids
# ---------------------------------------------------------------------------


class TestBiomodelsIds:
    def test_invokes_identifiers(self) -> None:
        svc = _mock_data_service({"compose_biomodels_identifiers": ["BIOMD001", "BIOMD002"]})
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-ids", "--n", "2"])
        assert result.exit_code == 0
        svc.compose_biomodels_identifiers.assert_called_once_with(n=2)


# ---------------------------------------------------------------------------
# biomodels-meta
# ---------------------------------------------------------------------------


class TestBiomodelsMeta:
    def test_invokes_metadata(self) -> None:
        svc = _mock_data_service({"compose_biomodels_metadata": {"name": "HH"}})
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-meta", "BIOMD001"])
        assert result.exit_code == 0
        svc.compose_biomodels_metadata.assert_called_once_with(biomodel_id="BIOMD001")


# ---------------------------------------------------------------------------
# biomodels-run
# ---------------------------------------------------------------------------


class TestBiomodelsRun:
    def test_default_simulator(self) -> None:
        svc = _mock_data_service({"compose_biomodels_run": {"simulation_database_id": 1, "simulator_database_id": 1}})
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-run", "BIOMD001"])
        assert result.exit_code == 0
        svc.compose_biomodels_run.assert_called_once_with(biomodel_id="BIOMD001", simulator="copasi")

    def test_tellurium_simulator(self) -> None:
        svc = _mock_data_service({"compose_biomodels_run": {"simulation_database_id": 2, "simulator_database_id": 1}})
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-run", "BIOMD001", "--simulator", "tellurium"])
        assert result.exit_code == 0
        svc.compose_biomodels_run.assert_called_once_with(biomodel_id="BIOMD001", simulator="tellurium")


# ---------------------------------------------------------------------------
# biomodels-batch
# ---------------------------------------------------------------------------


class TestBiomodelsBatch:
    def test_default(self) -> None:
        svc = _mock_data_service({"compose_biomodels_batch": {"submitted": [], "failed": []}})
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-batch"])
        assert result.exit_code == 0
        svc.compose_biomodels_batch.assert_called_once()

    def test_with_ids(self) -> None:
        svc = _mock_data_service({"compose_biomodels_batch": {"submitted": [], "failed": []}})
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-batch", "--ids", "BIOMD001,BIOMD002"])
        assert result.exit_code == 0
        call_kwargs = svc.compose_biomodels_batch.call_args
        assert call_kwargs.kwargs.get("model_ids") == ["BIOMD001", "BIOMD002"]


# ---------------------------------------------------------------------------
# biomodels-audit
# ---------------------------------------------------------------------------


class TestBiomodelsAudit:
    def test_default_simulators(self) -> None:
        svc = _mock_data_service({
            "compose_biomodels_audit": {
                "experiment": {"simulation_database_id": 10, "simulator_database_id": 1},
                "simulators_used": ["copasi", "tellurium"],
            }
        })
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-audit", "BIOMD001"])
        assert result.exit_code == 0
        svc.compose_biomodels_audit.assert_called_once_with(biomodel_id="BIOMD001", simulators=["copasi", "tellurium"])

    def test_custom_simulators(self) -> None:
        svc = _mock_data_service({
            "compose_biomodels_audit": {
                "experiment": {"simulation_database_id": 11, "simulator_database_id": 1},
                "simulators_used": ["copasi"],
            }
        })
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-audit", "BIOMD001", "--simulators", "copasi"])
        assert result.exit_code == 0
        svc.compose_biomodels_audit.assert_called_once_with(biomodel_id="BIOMD001", simulators=["copasi"])


# ---------------------------------------------------------------------------
# biomodels-regression
# ---------------------------------------------------------------------------


class TestBiomodelsRegression:
    def test_default(self) -> None:
        svc = _mock_data_service({
            "compose_biomodels_regression": {"submitted": [], "failed": [], "total_requested": 10}
        })
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-regression"])
        assert result.exit_code == 0
        svc.compose_biomodels_regression.assert_called_once()

    def test_custom_n(self) -> None:
        svc = _mock_data_service({
            "compose_biomodels_regression": {"submitted": [], "failed": [], "total_requested": 3}
        })
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-regression", "--n", "3"])
        assert result.exit_code == 0
        call_kwargs = svc.compose_biomodels_regression.call_args
        assert call_kwargs.kwargs.get("n_models") == 3

    def test_with_ids(self) -> None:
        svc = _mock_data_service({
            "compose_biomodels_regression": {"submitted": [], "failed": [], "total_requested": 2}
        })
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-regression", "--ids", "BIOMD001,BIOMD002"])
        assert result.exit_code == 0
        call_kwargs = svc.compose_biomodels_regression.call_args
        assert call_kwargs.kwargs.get("model_ids") == ["BIOMD001", "BIOMD002"]

    def test_output_shows_counts(self) -> None:
        svc = _mock_data_service({
            "compose_biomodels_regression": {
                "submitted": [{"simulation_database_id": 1, "simulator_database_id": 1}],
                "failed": ["BIOMD003"],
                "total_requested": 2,
            }
        })
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["compose", "biomodels-regression", "--n", "2"])
        assert result.exit_code == 0
        # Output contains ANSI codes; check unambiguous literals only
        assert "BIOMD003" in result.output
        assert "total_requested" in result.output
