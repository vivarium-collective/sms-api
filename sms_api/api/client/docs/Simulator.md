# Simulator

## Properties

| Name                | Type    | Description | Notes                                                                   |
| ------------------- | ------- | ----------- | ----------------------------------------------------------------------- |
| **git_commit_hash** | **str** |             |
| **git_repo_url**    | **str** |             | [optional] [default to 'https://github.com/vivarium-collective/vEcoli'] |
| **git_branch**      | **str** |             | [optional] [default to 'messages']                                      |

## Example

```python
from sms_api.api.client.models.simulator import Simulator

# TODO update the JSON string below
json = "{}"
# create an instance of Simulator from a JSON string
simulator_instance = Simulator.from_json(json)
# print the JSON string representation of the object
print(Simulator.to_json())

# convert the object into a dict
simulator_dict = simulator_instance.to_dict()
# create an instance of Simulator from a dict
simulator_from_dict = Simulator.from_dict(simulator_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
