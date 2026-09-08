"""Requesting the private vEcoli fork be staged inside the built image at build time.

Every existing build's DooD script reaches docker/build-and-push-ecr.sh with no -s spec
at all, so it silently falls through to the Dockerfile's public vEcoli default regardless
of the simulator's own pinned commit -- a config's !ParameterSerializer[...] tag whose
value only exists in the private fork's own param_store can then never resolve on a
remote dispatch. These pin the API-surface wiring in both directions, same shape as
test_submit_image_request.py, because the failure mode of a flag nobody can reach is
silence.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from viva_api.common.handlers import simulators as handlers
from viva_api.common.models import JobId


def _services(*, supports_flag: bool) -> tuple[MagicMock, MagicMock, dict[str, Any]]:
    """A build service whose submit_build_image_job either accepts stage_private_fork
    (the Ray path) or does not (every other path). ``seen`` records what it received."""
    seen: dict[str, Any] = {"stage_private_fork": "never-called", "vecoli_private_commit": "never-called"}

    async def submit_accepting(
        *, simulator_version: Any, stage_private_fork: bool = False, vecoli_private_commit: str | None = None
    ) -> JobId:
        seen["stage_private_fork"] = stage_private_fork
        seen["vecoli_private_commit"] = vecoli_private_commit
        return JobId.local("job-1")

    async def submit_rejecting(*, simulator_version: Any) -> JobId:
        seen["stage_private_fork"] = None
        seen["vecoli_private_commit"] = None
        return JobId.local("job-1")

    svc = MagicMock()
    svc.submit_build_image_job = submit_accepting if supports_flag else submit_rejecting
    svc._local = MagicMock()

    db = MagicMock()
    db.list_simulators = AsyncMock(return_value=[])
    sim = MagicMock()
    sim.database_id = 7
    sim.git_repo_url = "https://github.com/CovertLabEcoli/sms-ecoli"
    sim.git_commit_hash = "abc1234"
    db.insert_simulator = AsyncMock(return_value=sim)
    db.get_hpcrun_by_ref = AsyncMock(return_value=None)
    db.insert_hpcrun = AsyncMock(return_value=MagicMock(database_id=1))
    return svc, db, seen


async def _upload(svc: MagicMock, db: MagicMock, **kwargs: Any) -> Any:
    with patch.object(handlers, "verify_simulator_payload", lambda *_a, **_k: None):
        return await handlers.upload_simulator(
            commit_hash="abc1234",
            git_repo_url="https://github.com/CovertLabEcoli/sms-ecoli",
            git_branch="main",
            simulation_service_slurm=svc,
            database_service=db,
            **kwargs,
        )


@pytest.mark.asyncio
async def test_flag_and_commit_reach_the_build_when_requested() -> None:
    svc, db, seen = _services(supports_flag=True)
    await _upload(svc, db, stage_private_fork=True, vecoli_private_commit="deadbee")
    assert seen["stage_private_fork"] is True
    assert seen["vecoli_private_commit"] == "deadbee"


@pytest.mark.asyncio
async def test_default_build_never_stages_the_private_fork() -> None:
    """Off by default -- identical build to before these params existed. The build IS
    still called (unlike the unsupported-path case below); it just never receives
    stage_private_fork, so the service's own False default governs."""
    svc, db, seen = _services(supports_flag=True)
    await _upload(svc, db)
    assert seen["stage_private_fork"] is False
    assert seen["vecoli_private_commit"] is None


@pytest.mark.asyncio
async def test_requesting_without_a_commit_fails_loud() -> None:
    """No 'latest' auto-resolution -- the commit is always an explicit, visible choice.
    Must fail before ever reaching the build service, not silently float to whatever
    'latest' happens to mean."""
    svc, db, seen = _services(supports_flag=True)
    with pytest.raises(HTTPException) as exc:
        await _upload(svc, db, stage_private_fork=True)
    assert exc.value.status_code == 400
    assert "vecoli_private_commit" in str(exc.value.detail)
    assert seen["stage_private_fork"] == "never-called"


@pytest.mark.asyncio
async def test_unsupported_path_refuses_loudly_rather_than_silently_ignoring() -> None:
    """Asking a build path that cannot honour it must FAIL. Silently dropping the
    request would hand back a simulator wrapping the wrong (public) fork with no
    indication -- exactly the presence-vs-effect gap this project keeps paying for."""
    svc, db, seen = _services(supports_flag=False)
    with pytest.raises(HTTPException) as exc:
        await _upload(svc, db, stage_private_fork=True, vecoli_private_commit="deadbee")
    assert exc.value.status_code == 400
    assert "stage_private_fork" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_unsupported_path_is_unaffected_when_not_asked() -> None:
    svc, db, seen = _services(supports_flag=False)
    await _upload(svc, db)
    assert seen["stage_private_fork"] is None
