import json

from sms_api.dependencies import get_database_service

from sms_api.simulation.simulation_service import SimulationServiceHpc

from sms_api.simulation.database_service import DatabaseServiceSQL, DatabaseService

from sms_api.simulation.models import EcoliWorkflowRequest

EXAMPLE_WF_PAYLOAD = """
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


def example_workflow_request() -> EcoliWorkflowRequest:
    return EcoliWorkflowRequest(**json.loads(EXAMPLE_WF_PAYLOAD))


async def test():
    request = example_workflow_request()
    service = SimulationServiceHpc()
    database_service: DatabaseService = get_database_service()
    correlation_id: str = '1'




if __name__ == "__main__":
