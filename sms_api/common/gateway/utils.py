import datetime
import json
import warnings
from collections.abc import Awaitable
from pathlib import Path
from typing import Any, Callable, TypeVar

from fastapi import APIRouter

from sms_api.common.gateway.models import RouterConfig
from sms_api.common.ssh.ssh_service import SSHServiceManaged
from sms_api.config import get_settings
from sms_api.data.models import (
    AnalysisConfig,
    ExperimentAnalysisRequest,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import HpcRun, JobType, SimulatorVersion

REPO_DIR = Path(__file__).parent.parent.parent.parent.absolute()
PINNED_OUTDIR = REPO_DIR / "out" / "sms_single"
CURRENT_API_VERSION = "v1"


def router_config(prefix: str, api_version: str | None = None) -> RouterConfig:
    return RouterConfig(
        router=APIRouter(prefix=f"/{prefix}"), prefix=f"/{api_version or CURRENT_API_VERSION}", dependencies=[]
    )


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


def get_remote_outdir(experiment_id: str) -> Path:
    return Path(f"/home/FCAM/svc_vivarium/{get_settings().namespace}/sims/{experiment_id}")


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


def get_simulator() -> SimulatorVersion:
    return SimulatorVersion(
        git_commit_hash="079c43c",
        git_repo_url="https://github.com/CovertLab/vEcoli",
        git_branch="master",
        database_id=2,
        created_at=datetime.datetime.fromisoformat("2025-08-26T00:49:30"),
    )


def slurmjob_name_prefix() -> str:
    return f"sms-{get_simulator().git_commit_hash}"


def get_analysis_request_config(request: ExperimentAnalysisRequest, analysis_name: str) -> AnalysisConfig:
    return request.to_config(analysis_name=analysis_name)


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def connect_ssh(func: F) -> Any:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        instance = args[0]
        ssh_service: SSHServiceManaged = (
            kwargs.get("ssh_service") if not getattr(instance, "ssh_service", None) else instance.ssh_service  # type: ignore[assignment]
        )
        # ssh_service = kwargs.get('ssh_service', get_ssh_service_managed())
        try:
            print(f"Connecting ssh for function: {func.__name__}!")
            await ssh_service.connect()
            print(f"Connected: {ssh_service.connected}")
            return await func(*args, **kwargs)
        finally:
            print(f"Disconnecting ssh for function: {func.__name__}!")
            await ssh_service.disconnect()
            print(f"Connected: {ssh_service.connected}")

    return wrapper


def missing_experiment_error(exp_id: str) -> None:
    raise Exception(f"There is no experiment with an id of: {exp_id} in the database yet!")
