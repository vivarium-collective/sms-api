"""`--task-env NAME=VALUE` on the three dispatching verbs (sms-ecoli#166).

Pins the WIRING: the flag must leave the CLI as `task_env` in the block the
server reads for that path, and be absent (not null) when not given.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from app.cli import cli as cli_app

runner = CliRunner()


def _svc() -> tuple[MagicMock, dict[str, Any]]:
    captured: dict[str, Any] = {}

    def _run_workflow(**kwargs: object) -> MagicMock:
        captured.update(kwargs)
        sim = MagicMock()
        sim.database_id = 999
        sim.model_dump.return_value = {"database_id": 999}
        return sim

    svc = MagicMock()
    svc.run_workflow = _run_workflow
    return svc, captured


def _invoke(*args: str) -> tuple[int, str, dict[str, Any]]:
    svc, captured = _svc()
    with patch("app.cli.get_data_service", return_value=svc):
        result = runner.invoke(cli_app, list(args))
    return result.exit_code, result.output, captured


def test_composite_nextflow_puts_task_env_in_the_nextflow_block() -> None:
    code, out, captured = _invoke(
        "composite", "nextflow", "exp", "185", "--task-env", "V2ECOLI_SKIP_CACHE_VERIFY=1", "--task-env", "B=x=y"
    )
    assert code == 0, out
    assert captured["extra_params"]["nextflow_dispatch"]["task_env"] == {"V2ECOLI_SKIP_CACHE_VERIFY": "1", "B": "x=y"}


def test_composite_run_puts_task_env_in_the_multi_node_block() -> None:
    code, out, captured = _invoke("composite", "run", "exp", "185", "--task-env", "V2ECOLI_SKIP_CACHE_VERIFY=1")
    assert code == 0, out
    assert captured["extra_params"]["multi_node_dispatch"]["task_env"] == {"V2ECOLI_SKIP_CACHE_VERIFY": "1"}


def test_simulation_run_puts_task_env_at_the_config_top_level() -> None:
    """Chain dispatch and mbp_dispatch read the config; the top-level key is
    what JobScheduler re-derives every tick."""
    code, out, captured = _invoke("simulation", "run", "exp", "185", "--task-env", "V2ECOLI_SKIP_CACHE_VERIFY=1")
    assert code == 0, out
    assert captured["extra_params"] == {"task_env": {"V2ECOLI_SKIP_CACHE_VERIFY": "1"}}


def test_absent_flag_sends_no_task_env_key() -> None:
    """On a passthrough API a null is not the same as an absent key."""
    _, _, nf = _invoke("composite", "nextflow", "exp", "185")
    assert "task_env" not in nf["extra_params"]["nextflow_dispatch"]
    _, _, mnp = _invoke("composite", "run", "exp", "185")
    assert "task_env" not in mnp["extra_params"]["multi_node_dispatch"]
    _, _, chain = _invoke("simulation", "run", "exp", "185")
    assert chain["extra_params"] is None


def test_an_entry_without_equals_fails_before_dispatching() -> None:
    code, out, captured = _invoke("composite", "nextflow", "exp", "185", "--task-env", "NOEQUALS")
    assert code == 1
    assert "--task-env expects" in out  # Rich splits "NAME=VALUE" with highlight codes
    assert "extra_params" not in captured
