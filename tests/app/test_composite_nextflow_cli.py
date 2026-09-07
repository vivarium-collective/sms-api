"""CLI tests for `atlantis composite nextflow`.

The Nextflow dispatch had **no CLI surface**: `composite run` sends
`multi_node_dispatch` and nothing sent `nextflow_dispatch`, so every dispatch
during Phase 4's verification ladder was a hand-written `curl`. CLAUDE.md is
explicit that end-user paths are exercised through `atlantis`, not curl.

These pin the WIRING rather than the values, because the failure mode is a flag
that never leaves the CLI.
"""

from __future__ import annotations

import json
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


def _dispatch(*args: str) -> dict[str, Any]:
    svc, captured = _svc()
    with patch("app.cli.get_data_service", return_value=svc):
        result = runner.invoke(cli_app, ["composite", "nextflow", "exp", "153", *args])
    assert result.exit_code == 0, result.output
    dispatch: dict[str, Any] = captured["extra_params"]["nextflow_dispatch"]
    return dispatch


def test_it_sends_nextflow_dispatch_not_multi_node() -> None:
    """The server picks the mechanism on which key is present -- this is the
    entire difference between the two composite subcommands."""
    svc, captured = _svc()
    with patch("app.cli.get_data_service", return_value=svc):
        runner.invoke(cli_app, ["composite", "nextflow", "exp", "153"])
    assert "nextflow_dispatch" in captured["extra_params"]
    assert "multi_node_dispatch" not in captured["extra_params"]


def test_the_default_composite_id_carries_the_doubled_tail() -> None:
    """`workflow_nf` registers as '<module>.<name>' and, unlike
    lineage_ray_batch, has NO bare-module alias. The shortened form does not
    resolve -- which cost a full build-and-dispatch cycle to discover."""
    assert _dispatch()["composite_id"] == "v2ecoli.composites.workflow_nf.workflow_nf"


def test_named_flags_land_in_the_generator_params() -> None:
    d = _dispatch("--seeds", "4", "--generations", "2", "--include-analysis")
    assert d["params"] == {"n_seeds": 4, "n_generations": 2, "include_analysis": True}


def test_raw_params_merge_over_the_named_flags() -> None:
    d = _dispatch("--seeds", "1", "--params", '{"n_seeds": 9, "variants": [{"variant_name": "a"}]}')
    assert d["params"]["n_seeds"] == 9
    assert d["params"]["variants"] == [{"variant_name": "a"}]


def test_resume_and_nextflow_args_reach_the_dispatch() -> None:
    """`-dump-hashes` is the only way to see WHY a --resume did not match; it
    must be reachable without hand-writing the request."""
    d = _dispatch("--resume", "--nextflow-arg", "-dump-hashes", "--nextflow-arg", "-ansi-log")
    assert d["resume"] is True
    assert d["nextflow_args"] == ["-dump-hashes", "-ansi-log"]


def test_resume_from_reaches_the_dispatch_and_implies_resume() -> None:
    """Since #450 each dispatch has its own work dir, so a resume must name the
    run it continues -- the server refuses one that does not (viva-api#452).
    Naming a run and then not resuming it is never what was meant."""
    d = _dispatch("--resume-from", "sim143-nf-ladder-e2-7f3a")
    assert d["resume_from"] == "sim143-nf-ladder-e2-7f3a"
    assert d["resume"] is True


def test_resume_from_is_absent_unless_given() -> None:
    """A null would reach a passthrough API as a named campaign of None."""
    assert "resume_from" not in _dispatch("--resume")


def test_absent_options_are_omitted_not_sent_as_null() -> None:
    """On a passthrough API a null is not the same as an absent key."""
    d = _dispatch()
    for key in ("resume", "work_dir", "resources", "nextflow_args", "params"):
        assert key not in d, key


def test_bad_json_fails_before_dispatching() -> None:
    for flag in ("--params", "--resources"):
        svc, captured = _svc()
        with patch("app.cli.get_data_service", return_value=svc):
            result = runner.invoke(cli_app, ["composite", "nextflow", "e", "1", flag, "{not json"])
        assert result.exit_code == 1, flag
        assert not captured, f"{flag}: dispatched despite invalid JSON"


def test_resources_reach_the_dispatch_verbatim() -> None:
    """Merged per key server-side; the CLI must not reshape them."""
    spec = {"lineage": {"time": "24 h"}, "parca": {"cpus": 16}}
    assert _dispatch("--resources", json.dumps(spec))["resources"] == spec


def test_simulation_config_is_passed_through() -> None:
    """sms-ecoli ships named configs only; without this a dispatch 404s."""
    svc, captured = _svc()
    with patch("app.cli.get_data_service", return_value=svc):
        runner.invoke(cli_app, ["composite", "nextflow", "e", "1", "--simulation-config", "mecillinam_wellmixed.json"])
    assert captured["config_filename"] == "mecillinam_wellmixed.json"


def test_simulator_latest_passes_the_head_image_flag_three_valued() -> None:
    """Omitted must reach the server as ABSENT, not as `true`. A plain `true`
    default 400s every upload on a backend with no head image; leaving it absent
    lets the server build it where it can, and keeps `--submit-image` meaning
    "fail now if you cannot" for someone about to dispatch Nextflow."""
    svc = MagicMock()
    svc.submit_get_latest_simulator.return_value = MagicMock()
    svc.submit_upload_simulator.return_value = MagicMock(database_id=1)
    # The command polls the build to completion on a 15 s real sleep; a bare
    # MagicMock status is never terminal, so without this the test never ends.
    svc.submit_get_simulator_build_status.return_value = "completed"

    for args, expected in (
        ([], None),
        (["--submit-image"], True),
        (["--no-submit-image"], False),
    ):
        with patch("app.cli.get_data_service", return_value=svc), patch("time.sleep"):
            runner.invoke(cli_app, ["simulator", "latest", *args])
        assert svc.submit_upload_simulator.call_args.kwargs["include_submit_image"] is expected, args


# --- the two capabilities the science needs, reachable without hand JSON -----


def test_independent_founders_reaches_the_generator() -> None:
    """v2ecoli#731. Without it an M-seed campaign is not M replicates: seeds
    sharing a cache share a founder cell, so the spread is downstream
    stochasticity, not cell-to-cell variability (v2ecoli#693) -- which is the
    quantity a strain ranking rests on."""
    assert _dispatch("--independent-founders")["params"]["independent_founders"] is True
    assert _dispatch("--no-independent-founders")["params"]["independent_founders"] is False


def test_cache_uri_reaches_the_generator() -> None:
    """v2ecoli#732. CD2's Run 1 uses ten pre-built per-seed founder caches and
    Run 2 the violacein bundle; a campaign that recomputes runs a different
    experiment however green it looks."""
    uri = "s3://bucket/ray-parca-cache/9f84e6b/"
    assert _dispatch("--cache-uri", uri)["params"]["cache_uri"] == uri


def test_analysis_options_reaches_the_generator_as_an_object() -> None:
    """Not a string: the gather reads it out of a staged config. Without it
    v2ecoli-analyze prints 'nothing to run', exits 0, writes no analysis/, and
    the campaign fails its LAST node -- measured twice (simulations 441, 475)."""
    d = _dispatch("--analysis-options", '{"multiseed": {"cd1_proteomics": {}}}')
    assert d["params"]["analysis_options"] == {"multiseed": {"cd1_proteomics": {}}}


def test_the_new_flags_are_absent_unless_given() -> None:
    """A passthrough API: a null would override the composite's own default with
    nothing. Absent means 'the generator decides'."""
    d = _dispatch("--seeds", "2")
    for key in ("independent_founders", "cache_uri", "analysis_options"):
        assert key not in d["params"], key


def test_raw_params_still_win_over_the_named_flags() -> None:
    """--params is the escape hatch for anything without a flag, including
    per-variant cache_uri, so it must stay last."""
    d = _dispatch("--cache-uri", "s3://b/flag/", "--params", '{"cache_uri": "s3://b/raw/"}')
    assert d["params"]["cache_uri"] == "s3://b/raw/"
