# EcoliSimulation

## Properties

| Name            | Type                                                    | Description | Notes      |
| --------------- | ------------------------------------------------------- | ----------- | ---------- |
| **database_id** | **int**                                                 |             |
| **sim_request** | [**EcoliSimulationRequest**](EcoliSimulationRequest.md) |             |
| **slurmjob_id** | **int**                                                 |             | [optional] |

## Example

```python
from sms_api.api.client.models.ecoli_simulation import EcoliSimulation

# TODO update the JSON string below
json = "{}"
# create an instance of EcoliSimulation from a JSON string
ecoli_simulation_instance = EcoliSimulation.from_json(json)
# print the JSON string representation of the object
print(EcoliSimulation.to_json())

# convert the object into a dict
ecoli_simulation_dict = ecoli_simulation_instance.to_dict()
# create an instance of EcoliSimulation from a dict
ecoli_simulation_from_dict = EcoliSimulation.from_dict(ecoli_simulation_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
