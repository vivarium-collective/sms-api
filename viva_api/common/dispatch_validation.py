"""Request-shape checks for the dispatch payloads, done at the API boundary.

These are the checks answerable from the REQUEST ALONE -- no database, no
cluster, no settings. That is what lets them run before anything is written.

Why it matters that they run early (viva-api#455): ``run_simulation_workflow``
inserts a parca-dataset row and a simulation row *before* it submits, so a
dispatch-time raise leaves two rows describing a run that never started. A
malformed ``nextflow_dispatch`` is an ordinary typo, not an infrastructure
failure, so it must not cost durable state.

Server-side facts stay OUT of here. ``_awsbatch_nf_params``' missing-settings
check is a deployment error, not a caller error: it deserves its 500 and cannot
be answered from the request anyway.
"""

from __future__ import annotations

from typing import Any


class DispatchValidationError(ValueError):
    """A dispatch request the caller can fix. Maps to 400, never 500.

    A subclass of ValueError so the service layer can keep raising and catching
    plain ValueError, while the router can tell "your request is wrong" apart
    from "something broke" -- a distinction a blanket ValueError -> 400 would
    lose, since not every ValueError raised down there is the caller's fault.
    """


def validate_nextflow_dispatch(nf_dispatch: Any) -> None:
    """Check a ``nextflow_dispatch`` block, or raise DispatchValidationError."""
    if not isinstance(nf_dispatch, dict):
        raise DispatchValidationError(
            f"nextflow_dispatch must be an object, got {type(nf_dispatch).__name__}"
        )

    if not nf_dispatch.get("composite_id"):
        raise DispatchValidationError(
            "nextflow_dispatch.composite_id is required: the registered composite to compile "
            "into a Nextflow workflow (e.g. 'v2ecoli.composites.workflow_nf.workflow_nf' -- "
            "note the doubled tail; this generator has no bare-module alias)."
        )

    if nf_dispatch.get("resume") and not nf_dispatch.get("resume_from"):
        raise DispatchValidationError(
            "nextflow_dispatch.resume needs resume_from: the experiment_id of the run whose "
            "work dir and session cache to continue. Each dispatch gets its own work dir "
            "(viva-api#452), so a resume without one would find no session -- and Nextflow "
            "does not treat that as an error, it warns and silently re-runs the whole "
            "campaign at full cost."
        )
