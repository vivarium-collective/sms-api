import datetime
import functools
import json
import warnings
from collections.abc import Awaitable
from pathlib import Path
from typing import Any, Callable, TypeVar

import numpy as np
from fastapi import APIRouter

from sms_api.common.gateway.models import RouterConfig
from sms_api.common.ssh.ssh_service import SSHServiceManaged
from sms_api.config import get_settings
from sms_api.data.models import (
    AnalysisConfig,
    AnalysisDomain,
    ExperimentAnalysisRequest,
    PtoolsAnalysisConfig,
    PtoolsAnalysisType,
)
from sms_api.simulation.models import SimulatorVersion

REPO_DIR = Path(__file__).parent.parent.parent.parent.absolute()
PINNED_OUTDIR = REPO_DIR / "out" / "sms_single"
CURRENT_API_VERSION = "v1"


def router_config(prefix: str, api_version: str | None = None, version_major: bool = True) -> RouterConfig:
    version = f"/{api_version or CURRENT_API_VERSION}"
    pref = f"/{prefix}"
    config = (
        RouterConfig(router=APIRouter(prefix=version), prefix=pref, dependencies=[])
        if not version_major
        else RouterConfig(router=APIRouter(prefix=pref), prefix=version, dependencies=[])
    )
    return config


def format_version(major: int) -> str:
    return f"v{major}"


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
    @functools.wraps(func)
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


def generate_analysis_request(
    experiment_id: str,
    requested_configs: list[str | AnalysisDomain] | None = None,
    truncated: bool = True,
    n_tp: int | None = None,
    n_tp_max: int | None = None,
) -> ExperimentAnalysisRequest:
    req_configs = requested_configs or AnalysisDomain.to_list(sort=True)
    requested: dict[str, list[PtoolsAnalysisConfig]] = dict(zip(req_configs, [r for r in req_configs]))
    for conf_domain in requested:
        configs = list(
            map(
                lambda a_type: PtoolsAnalysisConfig(
                    name=a_type, n_tp=np.random.randint(2, n_tp_max or 10) if n_tp is None else n_tp
                ),
                PtoolsAnalysisType.to_list(),
            )
        )
        requested[conf_domain] = configs

    requested["experiment_id"] = experiment_id

    if not truncated:
        return ExperimentAnalysisRequest(**requested)

    return ExperimentAnalysisRequest(
        experiment_id=requested["experiment_id"],
        multiseed=requested["multiseed"],
        multigeneration=requested["multigeneration"],
    )
