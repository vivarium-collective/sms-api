# Simulation

## Properties

| Name            | Type                                                              | Description | Notes      |
| --------------- | ----------------------------------------------------------------- | ----------- | ---------- |
| **database_id** | **int**                                                           |             |
| **sim_request** | [**AntibioticSimulationRequest**](AntibioticSimulationRequest.md) |             |
| **slurmjob_id** | **int**                                                           |             | [optional] |

## Example

```python
from sms_api.api.client.models.simulation import Simulation

# TODO update the JSON string below
json = "{}"
# create an instance of Simulation from a JSON string
simulation_instance = Simulation.from_json(json)
# print the JSON string representation of the object
print(Simulation.to_json())

# convert the object into a dict
simulation_dict = simulation_instance.to_dict()
# create an instance of Simulation from a dict
simulation_from_dict = Simulation.from_dict(simulation_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
