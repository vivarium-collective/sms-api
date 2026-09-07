"""Tests for the shared Batch analysis-DAG-node submitter (viva_api.common.analysis_dag).

Two things this module must get right, both load-bearing for Task 2:

1. The submit-then-record orchestration (``submit_analysis_dag_node``) is
   backend-agnostic and reusable -- exercised here with a mocked "Batch client"
   (a plain ``submit_container`` callable) and a fake database service, with NO
   real AWS/Batch/Postgres dependency.
2. The emitted argv actually matches the REAL v2ecoli-analyze CLI surface
   (positional ``sweep_dir`` + ``--config``, nothing else) -- a contract test
   parses it against v2ecoli's own argparse parser when importable, falling
   back to a local minimal copy otherwise (v2ecoli PR #724 not merged yet).
"""

from __future__ import annotations

import argparse
import json
import shlex
from typing import Any

import pytest

from viva_api.common import analysis_dag
from viva_api.simulation.tables_orm import AnalysisStatusDB

STALE_FLAGS = (
    "--out-uri",
    "--n-seeds",
    "--n-generations",
    "--modules",
    "--analysis-name",
    "--experiment-id",
    "--out-dir",
)


class _FakeDatabaseService:
    """Duck-typed stand-in for DatabaseService -- only record_analysis is called."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def record_analysis(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


def _fake_submit_container(captured: dict[str, Any], job_id: str = "analysis-batch-1") -> Any:
    def _submit(**kwargs: Any) -> str:
        captured.update(kwargs)
        return job_id

    return _submit


def _final_segment(cmd: str) -> str:
    """The last ``&&``-chained shell segment -- the actual v2ecoli-analyze invocation."""
    return cmd.rsplit(" && ", 1)[-1]


def _config_json_from(cmd: str) -> dict[str, Any]:
    echo_segment = next(s.strip() for s in cmd.split(" && ") if s.strip().startswith("echo "))
    quoted = echo_segment[len("echo ") :].rsplit(" > ", 1)[0]
    return dict(json.loads(shlex.split(quoted)[0]))


def _submit_kwargs(**overrides: Any) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    db = _FakeDatabaseService()
    defaults: dict[str, Any] = {
        "sweep_dir": "s3://mybucket/vecoli-output/exp-1",
        "analysis_options": {"multiseed": {"cd1_fluxomics": {}}},
        "sim_data_uri": "s3://mybucket/ray-parca-cache/deadbeef/simData.cPickle",
        "result_out_dir": "s3://mybucket/vecoli-output/exp-1/analyses/analysis-exp-1-abc",
        "v2ecoli_dir": "/app/v2ecoli",
        "submit_container": _fake_submit_container(captured),
        "job_definition": "smscdk-ray-container-deadbeef",
        "job_name": "ray-analysis-exp-1-abc",
        "out_s3": "s3://mybucket/vecoli-output/exp-1/",
        "container_out_dir": "/app/v2ecoli/.pbg/runs/analysis",
        "depends_on_job_id": "parent-job-42",
        "depends_type": "SEQUENTIAL",
        "tags": {"Phase": "analysis"},
        "database_service": db,
        "experiment_id": "exp-1",
        "analysis_name": "analysis-exp-1-abc",
        "simulation_id": 7,
        "backend": "ray",
        "db_config": {"trigger": "test"},
        "result_uri": "s3://mybucket/vecoli-output/exp-1/analyses/analysis-exp-1-abc",
    }
    defaults.update(overrides)
    return {"kwargs": defaults, "captured": captured, "db": db}


@pytest.mark.asyncio
class TestSubmitAnalysisDagNode:
    """submit_analysis_dag_node -- the reusable, backend-agnostic submitter."""

    async def test_submits_positional_sweep_dir_and_config_form(self) -> None:
        rig = _submit_kwargs()
        job_id = await analysis_dag.submit_analysis_dag_node(**rig["kwargs"])
        assert job_id == "analysis-batch-1"

        cmd = rig["captured"]["job_cmd"]
        final = _final_segment(cmd)
        tokens = shlex.split(final)
        assert tokens[0] == "v2ecoli-analyze"
        assert tokens[1] == "s3://mybucket/vecoli-output/exp-1"  # positional sweep_dir
        assert tokens[2] == "--config"
        for stale in STALE_FLAGS:
            assert stale not in cmd

    async def test_dependson_the_given_parent_job_id(self) -> None:
        rig = _submit_kwargs(depends_on_job_id="parent-job-42")
        await analysis_dag.submit_analysis_dag_node(**rig["kwargs"])
        assert rig["captured"]["depends_on"] == ["parent-job-42"]
        assert rig["captured"]["depends_type"] == "SEQUENTIAL"

    async def test_no_dependency_when_parent_job_id_is_none(self) -> None:
        rig = _submit_kwargs(depends_on_job_id=None)
        await analysis_dag.submit_analysis_dag_node(**rig["kwargs"])
        assert rig["captured"]["depends_on"] is None

    async def test_config_points_sim_data_at_the_given_cache_not_a_stock_path(self) -> None:
        rig = _submit_kwargs(sim_data_uri="s3://mybucket/ray-parca-cache/c0ffee/simData.cPickle")
        await analysis_dag.submit_analysis_dag_node(**rig["kwargs"])
        config = _config_json_from(rig["captured"]["job_cmd"])
        assert config["sim_data_path"] == "s3://mybucket/ray-parca-cache/c0ffee/simData.cPickle"
        # Never a hardcoded/default per-commit path (viva-api#448) -- it round-trips
        # exactly the caller-given value, nothing else.
        assert "sim_data_path" in config

    async def test_config_carries_out_dir_and_analyses(self) -> None:
        rig = _submit_kwargs(
            result_out_dir="s3://mybucket/vecoli-output/exp-1/analyses/analysis-exp-1-abc",
            analysis_options={"multiseed": {"cd1_fluxomics": {"generation_lower_bound": 5}}},
        )
        await analysis_dag.submit_analysis_dag_node(**rig["kwargs"])
        config = _config_json_from(rig["captured"]["job_cmd"])
        assert config["out_dir"] == "s3://mybucket/vecoli-output/exp-1/analyses/analysis-exp-1-abc"
        assert config["analysis_options"] == {"multiseed": {"cd1_fluxomics": {"generation_lower_bound": 5}}}

    async def test_success_records_a_computing_row_with_the_batch_job_id(self) -> None:
        rig = _submit_kwargs()
        job_id = await analysis_dag.submit_analysis_dag_node(**rig["kwargs"])
        db = rig["db"]
        assert len(db.calls) == 1
        assert db.calls[0]["status"] == AnalysisStatusDB.COMPUTING
        assert db.calls[0]["job_id_ext"] == str(job_id)
        assert db.calls[0]["config"] == {"trigger": "test"}

    async def test_a_failed_submission_records_a_failed_row_instead_of_raising(self) -> None:
        def _boom(**kwargs: Any) -> str:
            raise RuntimeError("Batch said no")

        rig = _submit_kwargs(submit_container=_boom)
        result = await analysis_dag.submit_analysis_dag_node(**rig["kwargs"])
        assert result is None
        db = rig["db"]
        assert len(db.calls) == 1
        assert db.calls[0]["status"] == AnalysisStatusDB.FAILED
        assert "Batch said no" in db.calls[0]["error_message"]


def _analysis_arg_parser() -> argparse.ArgumentParser:
    """The real v2ecoli argv parser when importable, else a local minimal copy.

    TODO(compose-results-p0): swap to
    ``v2ecoli.workflow.analysis_runner.build_analysis_arg_parser`` once
    v2ecoli#724 is merged + pinned; drop this local parser copy. Until then, the
    pin doesn't resolve the import (confirmed: v2ecoli isn't even installed in
    this repo's venv today), so this always takes the fallback branch.
    """
    try:
        from v2ecoli.workflow.analysis_runner import build_analysis_arg_parser

        return build_analysis_arg_parser()  # type: ignore[no-any-return]
    except ImportError:
        parser = argparse.ArgumentParser()
        parser.add_argument("sweep_dir")
        parser.add_argument("--config", default=None)
        return parser


class TestArgvContract:
    """Parses the emitted argv against the REAL v2ecoli parser (see
    _analysis_arg_parser's docstring for the fallback + swap-over plan)."""

    def _cmd(self) -> str:
        config = {
            "analysis_options": "applicable",
            "out_dir": "s3://mybucket/vecoli-output/exp-1/analyses/analysis-exp-1-abc",
            "sim_data_path": "s3://mybucket/ray-parca-cache/deadbeef/simData.cPickle",
        }
        return analysis_dag.analysis_dag_command(
            v2ecoli_dir="/app/v2ecoli",
            sweep_dir="s3://mybucket/vecoli-output/exp-1",
            sim_data_uri="s3://mybucket/ray-parca-cache/deadbeef/simData.cPickle",
            config=config,
        )

    def test_emitted_argv_parses_clean(self) -> None:
        parser = _analysis_arg_parser()
        final = _final_segment(self._cmd())
        args = parser.parse_args(shlex.split(final)[1:])
        assert args.sweep_dir == "s3://mybucket/vecoli-output/exp-1"
        assert args.config == "$tmp_config"

    def test_stale_argv_is_rejected_by_the_same_parser(self) -> None:
        parser = _analysis_arg_parser()
        stale = (
            "v2ecoli-analyze s3://mybucket/vecoli-output/exp-1 "
            "--out-uri s3://mybucket/vecoli-output/exp-1 --n-seeds 4 "
            "--modules '{}' --analysis-name analysis-exp-1-abc"
        )
        with pytest.raises(SystemExit):
            parser.parse_args(shlex.split(stale)[1:])

    def test_experiment_id_and_out_dir_flags_are_also_rejected(self) -> None:
        """The plan's own originally-stated (also wrong) --experiment-id/--out-dir
        form must fail exactly the same way as the --out-uri/--modules form."""
        parser = _analysis_arg_parser()
        stale = "v2ecoli-analyze s3://mybucket/vecoli-output/exp-1 --experiment-id exp-1 --out-dir s3://x"
        with pytest.raises(SystemExit):
            parser.parse_args(shlex.split(stale)[1:])
