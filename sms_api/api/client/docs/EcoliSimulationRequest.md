# EcoliSimulationRequest

## Properties

| Name                 | Type                                              | Description | Notes |
| -------------------- | ------------------------------------------------- | ----------- | ----- |
| **simulator**        | [**SimulatorVersion**](SimulatorVersion.md)       |             |
| **parca_dataset_id** | **int**                                           |             |
| **variant_config**   | **Dict[str, Dict[str, VariantConfigValueValue]]** |             |

## Example

```python
from sms_api.api.client.models.ecoli_simulation_request import EcoliSimulationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of EcoliSimulationRequest from a JSON string
ecoli_simulation_request_instance = EcoliSimulationRequest.from_json(json)
# print the JSON string representation of the object
print(EcoliSimulationRequest.to_json())

# convert the object into a dict
ecoli_simulation_request_dict = ecoli_simulation_request_instance.to_dict()
# create an instance of EcoliSimulationRequest from a dict
ecoli_simulation_request_from_dict = EcoliSimulationRequest.from_dict(ecoli_simulation_request_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
