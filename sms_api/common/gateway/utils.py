from pathlib import Path

import numpy as np
from fastapi import APIRouter

from sms_api.analysis.models import (
    AnalysisDomain,
    ExperimentAnalysisRequest,
    PtoolsAnalysisConfig,
    PtoolsAnalysisType,
)
from sms_api.common.gateway.models import RouterConfig
from sms_api.common.utils import get_data_id
from sms_api.config import get_settings

REPO_DIR = Path(__file__).parent.parent.parent.parent.absolute()
PINNED_OUTDIR = REPO_DIR / "out" / "sms_single"
CURRENT_API_VERSION = "v1"


def get_router_config(prefix: str, api_version: str | None = None, version_major: bool = True) -> RouterConfig:
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
    """Return remote path for experiment output directory (for SSH commands)."""
    return get_settings().hpc_sim_base_path.remote_path / experiment_id


def missing_experiment_error(exp_id: str) -> None:
    raise Exception(f"There is no experiment with an id of: {exp_id} in the database yet!")


def generate_analysis_request(
    experiment_id: str,
    analysis_name: str | None = None,
    requested_configs: list[str | AnalysisDomain] | None = None,
    truncated: bool = True,
    n_tp: int | None = None,
    n_tp_max: int | None = None,
) -> ExperimentAnalysisRequest:
    req_configs = requested_configs or AnalysisDomain.to_list(sort=True)
    requested: dict[str, list[PtoolsAnalysisConfig] | str] = dict(zip(req_configs, [r for r in req_configs]))
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
    requested["analysis_name"] = analysis_name or (get_data_id(scope="analysis"))

    if not truncated:
        return ExperimentAnalysisRequest(**requested)  # type: ignore[arg-type]

    return ExperimentAnalysisRequest(
        experiment_id=requested["experiment_id"],  # type: ignore[arg-type]
        multiseed=requested["multiseed"],  # type: ignore[arg-type]
        multigeneration=requested["multigeneration"],  # type: ignore[arg-type]
    )
