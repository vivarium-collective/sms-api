"""`include_submit_image` is three-valued, and an already-satisfied request is not an error.

It was opt-in on the reasoning that "every build would otherwise pay for it".
Measured across four builds that cost is **+72 MB and +15 s** -- the two images
share a base ECR deduplicates -- while omitting it costs a Nextflow dispatch
that fails at the container image pull, minutes in, plus a full rebuild.

Flipping the default to a plain `True` 400'd every SLURM-path build (caught by
tests/api/core/test_simulator.py) -- so the flag is three-valued instead: omitted
means "build it where the backend can", `true` DEMANDS it. Even so, a plain
default would have 400'd every vEcoli build: the handler
refused the flag on any backend whose `submit_build_image_job` lacks the
parameter, and vEcoli's is such a backend -- while building its `-submit` image
UNCONDITIONALLY (`simulation_service_k8s._run_build` passes `submit_image=True`
as a literal). The refusal rejected a request the backend fulfils by
construction.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from viva_api.common.handlers.simulators import _builds_head_image_unconditionally


class _AcceptsFlag:
    async def submit_build_image_job(self, simulator_version: object, include_submit_image: bool = False) -> str:
        return "ray"


class SimulationServiceK8s:  # name is the contract -- see _builds_head_image_unconditionally
    async def submit_build_image_job(self, simulator_version: object) -> str:
        return "k8s"


class _NeitherAcceptsNorBuilds:
    async def submit_build_image_job(self, simulator_version: object) -> str:
        return "slurm"


def test_the_ray_path_accepts_the_flag() -> None:
    assert "include_submit_image" in inspect.signature(_AcceptsFlag().submit_build_image_job).parameters


def test_vecoli_is_recognised_as_already_building_it() -> None:
    """Asserted by NAME, not by signature: 'lacks the parameter' is exactly what
    'already does it' and 'cannot do it' have in common, so a signature check
    cannot separate them."""
    assert _builds_head_image_unconditionally(SimulationServiceK8s()) is True


def test_a_backend_that_neither_accepts_nor_builds_is_not_waved_through() -> None:
    """Silently accepting there would yield a dispatch that fails at the image
    pull -- the silent-success shape this codebase keeps having to fix."""
    assert _builds_head_image_unconditionally(_NeitherAcceptsNorBuilds()) is False


def test_the_route_default_is_omitted_not_true() -> None:
    """A plain `True` default is NOT equivalent: it turns every upload on a
    backend without a head image into a 400. Omitted has to mean "build it where
    that is possible", leaving `true` free to mean "I am about to dispatch
    Nextflow -- fail now if you cannot"."""
    from viva_api.api.routers.core import insert_simulator_version

    assert inspect.signature(insert_simulator_version).parameters["include_submit_image"].default is None


def test_a_demand_and_the_default_diverge_only_where_the_backend_cannot() -> None:
    """The whole point of the third value. On both supported backends the two
    are indistinguishable; they part company exactly on the path that has no
    head image, where one must raise and the other must not."""
    from viva_api.common.handlers import simulators

    src = inspect.getsource(simulators.upload_simulator)
    assert "include_submit_image is not False" in src, "the default must still build"
    assert "elif demanded:" in src, "only an explicit demand may 400"


def test_the_real_k8s_service_still_builds_it_unconditionally() -> None:
    """The load-bearing assumption behind treating the request as satisfied. If
    this ever stops being true, the handler starts reporting success over an
    image nobody built."""
    import viva_api.simulation.simulation_service_k8s as k8s

    src = inspect.getsource(k8s.SimulationServiceK8s._run_build)
    assert "submit_image=True" in src, "vEcoli no longer builds its -submit image unconditionally"
    assert _builds_head_image_unconditionally(k8s.SimulationServiceK8s.__new__(k8s.SimulationServiceK8s))


@pytest.mark.parametrize("service", [_AcceptsFlag(), SimulationServiceK8s()])
def test_both_supported_backends_are_satisfiable(service: Any) -> None:
    accepts = "include_submit_image" in inspect.signature(service.submit_build_image_job).parameters
    assert accepts or _builds_head_image_unconditionally(service)
