"""
API for funcs in this module:

Names: <ROUTER_NAME>_<ENDPOINT_NAME/PATHS>()

For example:

For the endpoint: /core/simulation/workflow: core_simulation_workflow
For the endpoint: /core/simulator/versions: core_simulator_versions

Then, add that func to the list within the examples dict comprehension below!
"""

import json
import uuid
from pathlib import Path

from sms_api.common.utils import unique_id
from sms_api.config import REPO_ROOT
from sms_api.data.models import AnalysisConfig, ExperimentAnalysisRequest
from sms_api.simulation.models import EcoliWorkflowRequest, ExperimentRequest, SimulationConfiguration

DEFAULT_SIMULATION_CONFIG = SimulationConfiguration.from_base()


def core_simulation_workflow() -> EcoliWorkflowRequest:
    payload = """
    {
    "simulator": {
        "git_commit_hash": "78c6310",
        "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
        "git_branch": "messages",
        "database_id": 1,
        "created_at": "2025-08-20T16:38:11"
        },
    "parca_dataset_id": 1,
    "variant_config": {
        "named_parameters": {
        "param1": 0.5,
        "param2": 0.5
        }
    },
    "config_id": "sms_single",
    "config_overrides": {
        "additionalProp1": {}
    }
    }
    """
    return EcoliWorkflowRequest(**json.loads(payload))


def core_sim_config() -> None:
    # return SimulationConfiguration()
    pass


def core_analysis_config() -> AnalysisConfig:
    fp = Path(REPO_ROOT) / "assets" / "sms_multigen_analysis.json"
    return AnalysisConfig.from_file(fp=fp)


def core_analysis_request() -> ExperimentAnalysisRequest:
    return ExperimentAnalysisRequest(experiment_id="sms_multigeneration", analysis_name=f"analysis_{uuid.uuid4()!s}")


def core_experiment_request() -> ExperimentRequest:
    expid = unique_id()
    return ExperimentRequest(experiment_id=expid)


examples = {
    func.__name__: func()
    for func in [
        core_simulation_workflow,
        core_analysis_config,
        core_sim_config,
        core_analysis_request,
        core_experiment_request,
    ]
}
