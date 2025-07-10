# RegisteredSimulators

## Properties

| Name          | Type                                              | Description | Notes      |
| ------------- | ------------------------------------------------- | ----------- | ---------- |
| **versions**  | [**List[SimulatorVersion]**](SimulatorVersion.md) |             |
| **timestamp** | **datetime**                                      |             | [optional] |

## Example

```python
from sms_api.api.client.models.registered_simulators import RegisteredSimulators

# TODO update the JSON string below
json = "{}"
# create an instance of RegisteredSimulators from a JSON string
registered_simulators_instance = RegisteredSimulators.from_json(json)
# print the JSON string representation of the object
print(RegisteredSimulators.to_json())

# convert the object into a dict
registered_simulators_dict = registered_simulators_instance.to_dict()
# create an instance of RegisteredSimulators from a dict
registered_simulators_from_dict = RegisteredSimulators.from_dict(registered_simulators_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
