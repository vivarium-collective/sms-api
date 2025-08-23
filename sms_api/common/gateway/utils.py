import json
import warnings
from pathlib import Path
from typing import Any

from sms_api.common.gateway.models import Namespace
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import HpcRun, JobType

REPO_DIR = Path(__file__).parent.parent.parent.parent.absolute()
PINNED_OUTDIR = REPO_DIR / "out" / "sms_single"


def get_pinned_outdir() -> Path:
    return get_remote_simulation_outdir(experiment_id="sms_single")


def get_remote_simulation_outdir(
    experiment_id: str, group: str | None = None, user: str | None = None, namespace: Namespace | str | None = None
) -> Path:
    """Meant to be used modularly based on the given HPC configuration of a given deployment.
    For example, we use uchc specifics by default (user = svc_vivarium, etc). So it should be whatever
    is expected by your HPC.

    :param experiment_id: the experiment ID used to index the saved simulations on disk.
    :param group: the HPC's group
    :param user: the HPC's user (defaults to ``svc_vivarium`` for UCHC)
    :param namespace: the deployment's namespace. See ``sms_api.common.gateway.models.Namespace`` for
        more details. Defaults to ``Namespace.PRODUCTION``.
    """
    return Path(
        f"/home/{group or 'FCAM'}/{user or 'svc_vivarium'}/{namespace or Namespace.PRODUCTION}/sims/{experiment_id}"
    )


def get_local_simulation_outdir(experiment_id: str) -> Path:
    """To really ONLY be used for local dev: that is, without access or attachment to the HPC mount"""
    return REPO_DIR / "home/FCAM/svc_vivarium/prod/sims" / experiment_id


def get_simulation_outdir(experiment_id: str, remote: bool = True, **kwargs: str) -> Path | None:
    """
    :param experiment_id: Simulation experiment id.
    :param remote: If ``True``, use the base path of `/home/<GROUP>/<USER>`. Defaults to ``True``.
    :param kwargs: ``"group", "user", "deployment"``
    :return: Path to the simulation outdir.
    """
    outdir = (
        get_remote_simulation_outdir(experiment_id=experiment_id, **kwargs)
        if remote
        else get_local_simulation_outdir(experiment_id=experiment_id)
    )
    if not outdir.exists():
        warnings.warn(f"{outdir} does not exist. Defaulting to {REPO_DIR}/home/...etc", stacklevel=2)
        return None
    return outdir


def format_version(major: int) -> str:
    return f"v{major}"


def root_prefix(major: int) -> str:
    return f"/api/{format_version(major)}"


async def get_simulation_hpcrun(simulation_id: int, db_service: DatabaseService) -> HpcRun | None:
    hpcrun = await db_service.get_hpcrun_by_ref(ref_id=simulation_id, job_type=JobType.SIMULATION)
    return hpcrun


def format_marimo_appname(appname: str) -> str:
    """Capitalizes and separates appnames(module names) if needed."""
    if "_" in appname:
        return appname.replace("_", " ").title()
    else:
        return appname.replace(appname[0], appname[0].upper())


def get_remote_outdir(experiment_id: str, namespace: Namespace | None = None) -> Path:
    return Path(f"/home/FCAM/svc_vivarium/{namespace or Namespace.PRODUCTION}/sims/{experiment_id}")


def write_remote_config(
    config: dict[str, Any] | str | Any,
    fname: str,
    simulator_hash: str | None = None,
    **overrides: Any,
) -> tuple[int, Path | None]:
    if isinstance(config, str):
        config = json.loads(config)
    if simulator_hash is None:
        saved_latest = Path("assets/simulation/model/latest_commit.txt")
        try:
            with open(str(saved_latest)) as f:
                simulator_hash = f.readline().strip()
        except FileNotFoundError as e:
            warnings.warn(f"The hardcoded file doesnt exist in this repo: {e}", stacklevel=2)
            return (1, None)
    fpath = Path(f"/home/FCAM/svc_vivarium/prod/repos/{simulator_hash}/vEcoli/configs/{fname}.json")
    if overrides:
        config.update(overrides)
    with open(fpath, "w") as f:
        json.dump(config, f, indent=1)
    return (0, fpath)
