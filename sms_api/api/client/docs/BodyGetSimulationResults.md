# BodyGetSimulationResults

## Properties

| Name                 | Type                                                | Description | Notes      |
| -------------------- | --------------------------------------------------- | ----------- | ---------- |
| **observable_names** | [**RequestedObservables**](RequestedObservables.md) |             |
| **settings**         | [**Settings**](Settings.md)                         |             | [optional] |

## Example

```python
from sms_api.api.client.models.body_get_simulation_results import BodyGetSimulationResults

# TODO update the JSON string below
json = "{}"
# create an instance of BodyGetSimulationResults from a JSON string
body_get_simulation_results_instance = BodyGetSimulationResults.from_json(json)
# print the JSON string representation of the object
print(BodyGetSimulationResults.to_json())

# convert the object into a dict
body_get_simulation_results_dict = body_get_simulation_results_instance.to_dict()
# create an instance of BodyGetSimulationResults from a dict
body_get_simulation_results_from_dict = BodyGetSimulationResults.from_dict(body_get_simulation_results_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
