# SimulatorVersion

## Properties

| Name                | Type         | Description | Notes                                                                   |
| ------------------- | ------------ | ----------- | ----------------------------------------------------------------------- |
| **git_commit_hash** | **str**      |             |
| **git_repo_url**    | **str**      |             | [optional] [default to 'https://github.com/vivarium-collective/vEcoli'] |
| **git_branch**      | **str**      |             | [optional] [default to 'messages']                                      |
| **database_id**     | **int**      |             |
| **created_at**      | **datetime** |             | [optional]                                                              |

## Example

```python
from sms_api.api.client.models.simulator_version import SimulatorVersion

# TODO update the JSON string below
json = "{}"
# create an instance of SimulatorVersion from a JSON string
simulator_version_instance = SimulatorVersion.from_json(json)
# print the JSON string representation of the object
print(SimulatorVersion.to_json())

# convert the object into a dict
simulator_version_dict = simulator_version_instance.to_dict()
# create an instance of SimulatorVersion from a dict
simulator_version_from_dict = SimulatorVersion.from_dict(simulator_version_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
