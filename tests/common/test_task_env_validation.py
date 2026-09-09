"""`task_env`: the per-dispatch environment passthrough (sms-ecoli#166).

Why it exists: v2ecoli#758 changed a file in ``cache_version.INPUT_FILES`` and
re-keyed every ParCa cache in S3 with the biology unchanged; the team chose
v2ecoli's documented escape hatch (``V2ECOLI_SKIP_CACHE_VERIFY=1``) over a
rebuild, and nothing in this API could set an env var on a Batch task from a
request. These pin the boundary rules: reject, never coerce.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from viva_api.common.dispatch_validation import (
    TASK_ENV_MAX_ENTRIES,
    DispatchValidationError,
    resolve_task_env,
    task_env_as_batch_list,
    validate_dispatch_task_envs,
    validate_nextflow_dispatch,
    validate_task_env,
)


def test_the_motivating_case_is_accepted_verbatim() -> None:
    assert validate_task_env({"V2ECOLI_SKIP_CACHE_VERIFY": "1"}) == {"V2ECOLI_SKIP_CACHE_VERIFY": "1"}


def test_absent_is_empty_not_an_error() -> None:
    assert validate_task_env(None) == {}
    assert validate_task_env({}) == {}


@pytest.mark.parametrize("bad", [["A=1"], "A=1", 1])
def test_non_object_is_refused(bad: object) -> None:
    with pytest.raises(DispatchValidationError, match="must be an object"):
        validate_task_env(bad)


@pytest.mark.parametrize("name", ["1BAD", "A-B", "A B", "", "A.B"])
def test_a_name_that_is_not_an_env_var_name_is_refused(name: str) -> None:
    with pytest.raises(DispatchValidationError, match="not a valid environment variable name"):
        validate_task_env({name: "x"})


@pytest.mark.parametrize(
    "name",
    ["PYTHONPATH", "V2E_ROOT", "LINEAGE_DEBUG_DIVISION", "AWS_REGION", "RAY_JOB_CMD", "CONTAINER_JOB_CMD", "NXF_HOME"],
)
def test_names_the_service_sets_itself_are_refused_not_shadowed(name: str) -> None:
    """A request must not be able to silently override the contract the
    entrypoints and executors rely on."""
    with pytest.raises(DispatchValidationError, match="set by the service itself"):
        validate_task_env({name: "x"})


@pytest.mark.parametrize("value", [1, True, None, ["1"]])
def test_a_non_string_value_is_refused_not_coerced(value: object) -> None:
    with pytest.raises(DispatchValidationError, match="must be a string"):
        validate_task_env({"X": value})


@pytest.mark.parametrize("value", ["a b", "a\tb", 'a"b', "a'b", "a$b", "a\\b"])
def test_a_value_the_nextflow_renderer_cannot_emit_is_refused_on_every_path(value: str) -> None:
    """The awsbatch profile renders each entry into a docker `--env` argument
    inside a Groovy string; process-bigraph refuses these characters there. The
    same rule everywhere means a request that works on one path works on all."""
    with pytest.raises(DispatchValidationError, match="may not contain"):
        validate_task_env({"X": value})


def test_too_many_entries_are_refused() -> None:
    with pytest.raises(DispatchValidationError, match="at most"):
        validate_task_env({f"K{i}": "v" for i in range(TASK_ENV_MAX_ENTRIES + 1)})


def test_the_message_names_the_request_field() -> None:
    with pytest.raises(DispatchValidationError, match=r"mbp_dispatch\.task_env\['X'\]"):
        validate_task_env({"X": 1}, where="mbp_dispatch.task_env")


def test_boundary_check_covers_the_top_level_and_every_dispatch_block() -> None:
    validate_dispatch_task_envs({"task_env": {"A": "1"}, "nextflow_dispatch": {"composite_id": "c"}})
    for block in ("nextflow_dispatch", "multi_node_dispatch", "mbp_dispatch"):
        with pytest.raises(DispatchValidationError, match=f"{block}.task_env"):
            validate_dispatch_task_envs({block: {"task_env": {"PYTHONPATH": "x"}}})
    with pytest.raises(DispatchValidationError, match="^task_env"):
        validate_dispatch_task_envs({"task_env": {"X": 1}})


def test_validate_nextflow_dispatch_checks_its_own_task_env() -> None:
    """The service re-validates the block on the direct entry point too."""
    with pytest.raises(DispatchValidationError, match="nextflow_dispatch.task_env"):
        validate_nextflow_dispatch({"composite_id": "c", "task_env": {"AWS_X": "1"}})


def test_resolve_merges_the_block_over_the_config_top_level() -> None:
    """A block's entry wins on a shared name; the rest of both survive."""
    config = SimpleNamespace(task_env={"A": "top", "B": "top"})
    assert resolve_task_env(config, {"task_env": {"B": "block", "C": "block"}}) == {
        "A": "top",
        "B": "block",
        "C": "block",
    }
    assert resolve_task_env(config, None) == {"A": "top", "B": "top"}
    assert resolve_task_env(SimpleNamespace(), {"composite_id": "c"}) == {}


def test_batch_list_shape() -> None:
    assert task_env_as_batch_list({"A": "1", "B": "2"}) == [{"name": "A", "value": "1"}, {"name": "B", "value": "2"}]
    assert task_env_as_batch_list(None) == []
