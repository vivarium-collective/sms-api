"""A refused dispatch is a 400, not a 500 (viva-api#455).

The guard added in #452 worked and produced the right message, but reached the
caller as `Server returned 500` -- a caller error reported as a server fault.
The route caught only bare `Exception`, so every `ValueError` raised below it
became a 500, and 500 is the one status worth paging on.

The mapping is on `DispatchValidationError` rather than on `ValueError`,
deliberately: not every ValueError raised down that path is the caller's fault,
and widening it would relabel genuine server faults as bad requests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from viva_api.api.main import app
from viva_api.common.dispatch_validation import DispatchValidationError


async def _post(exc: Exception) -> tuple[int, str]:
    """POST /api/v1/simulations with the handler raising `exc`."""
    with (
        patch("viva_api.api.routers.sms.get_simulation_service", return_value=MagicMock()),
        patch("viva_api.api.routers.sms.get_database_service", return_value=MagicMock()),
        patch(
            "viva_api.common.handlers.simulations.run_simulation_workflow",
            new=AsyncMock(side_effect=exc),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/api/v1/simulations", params={"simulator_id": 153})
    return r.status_code, r.text


@pytest.mark.asyncio
async def test_a_refused_dispatch_is_a_400() -> None:
    detail = "nextflow_dispatch.resume needs resume_from: the experiment_id of the run ..."
    status, body = await _post(DispatchValidationError(detail))
    assert status == 400, body
    assert "resume_from" in body, "the message the caller needs must survive the mapping"


@pytest.mark.asyncio
async def test_a_genuine_failure_is_still_a_500() -> None:
    """The narrow mapping's whole point. A blanket ValueError -> 400 would report
    a server fault as the caller's mistake, which is the mirror of the bug."""
    status, _ = await _post(RuntimeError("the cluster is on fire"))
    assert status == 500


@pytest.mark.asyncio
async def test_an_unrelated_value_error_is_not_relabelled_as_a_bad_request() -> None:
    """`DispatchValidationError` IS a ValueError, so the two clauses could not be
    ordered the other way -- but a plain ValueError must not take the 400 path."""
    status, _ = await _post(ValueError("simulator 999 not found"))
    assert status == 500
    assert issubclass(DispatchValidationError, ValueError)
