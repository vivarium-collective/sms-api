"""The boundary checks themselves (viva-api#455).

What belongs here is exactly what is answerable from the REQUEST -- that is the
property that lets these run before `run_simulation_workflow` writes a
parca-dataset row and a simulation row. A check needing settings, the database
or the cluster cannot move to the boundary and keeps its 500.
"""

from __future__ import annotations

import pytest

from viva_api.common.dispatch_validation import DispatchValidationError, validate_nextflow_dispatch


def test_resume_without_resume_from_is_refused() -> None:
    """Nextflow does not treat a missing session as an error -- it warns and
    re-runs the whole campaign at full cost, exit 0. Measured: 19m54s instead of
    the 73s a real resume takes."""
    with pytest.raises(DispatchValidationError, match="resume_from"):
        validate_nextflow_dispatch({"composite_id": "c", "resume": True})


def test_resume_with_resume_from_is_accepted() -> None:
    validate_nextflow_dispatch({"composite_id": "c", "resume": True, "resume_from": "sim1-x-0000"})


def test_resume_from_alone_is_accepted() -> None:
    """The CLI sends `resume: true` alongside it, but the API must not require a
    redundant field to state the same intent."""
    validate_nextflow_dispatch({"composite_id": "c", "resume_from": "sim1-x-0000"})


def test_a_missing_composite_id_is_refused() -> None:
    """Also a caller error, and it had the same 500-plus-orphan-rows shape."""
    with pytest.raises(DispatchValidationError, match="composite_id"):
        validate_nextflow_dispatch({"resume_from": "sim1-x-0000"})


@pytest.mark.parametrize("bad", [None, "workflow_nf", 42, ["composite_id"]])
def test_a_non_object_dispatch_is_refused(bad: object) -> None:
    """`--params '"x"'` and similar reach here as a bare scalar. Without this the
    first `.get` raises AttributeError, which is a 500 and says nothing useful."""
    with pytest.raises(DispatchValidationError, match="must be an object"):
        validate_nextflow_dispatch(bad)


def test_the_error_is_a_value_error() -> None:
    """The service layer keeps raising and catching plain ValueError; only the
    router needs to tell the two apart."""
    assert issubclass(DispatchValidationError, ValueError)


def test_the_messages_say_what_to_do() -> None:
    """These are the only thing a caller sees. The composite_id one carries the
    doubled tail, which cost a full build-and-dispatch cycle to discover."""
    with pytest.raises(DispatchValidationError) as missing_id:
        validate_nextflow_dispatch({})
    assert "workflow_nf.workflow_nf" in str(missing_id.value)

    with pytest.raises(DispatchValidationError) as bad_resume:
        validate_nextflow_dispatch({"composite_id": "c", "resume": True})
    assert "experiment_id" in str(bad_resume.value)
