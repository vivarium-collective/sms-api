# AntibioticSimulation

## Properties

| Name            | Type                                                              | Description | Notes      |
| --------------- | ----------------------------------------------------------------- | ----------- | ---------- |
| **database_id** | **int**                                                           |             |
| **sim_request** | [**AntibioticSimulationRequest**](AntibioticSimulationRequest.md) |             |
| **slurmjob_id** | **int**                                                           |             | [optional] |

## Example

```python
from sms_api.api.client.models.antibiotic_simulation import AntibioticSimulation

# TODO update the JSON string below
json = "{}"
# create an instance of AntibioticSimulation from a JSON string
antibiotic_simulation_instance = AntibioticSimulation.from_json(json)
# print the JSON string representation of the object
print(AntibioticSimulation.to_json())

# convert the object into a dict
antibiotic_simulation_dict = antibiotic_simulation_instance.to_dict()
# create an instance of AntibioticSimulation from a dict
antibiotic_simulation_from_dict = AntibioticSimulation.from_dict(antibiotic_simulation_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
