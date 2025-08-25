"""
API for funcs in this module:

Names: <ROUTER_NAME>_<ENDPOINT_NAME/PATHS>()

For example:

For the endpoint: /core/simulation/workflow: core_simulation_workflow
For the endpoint: /core/simulator/versions: core_simulator_versions

Then, add that func to the list within the examples dict comprehension below!
"""

import json

from sms_api.simulation.models import EcoliWorkflowRequest


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


examples = {func.__name__: func() for func in [core_simulation_workflow]}
