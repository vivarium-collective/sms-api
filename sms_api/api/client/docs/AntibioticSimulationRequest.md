# AntibioticSimulationRequest

## Properties

| Name                   | Type                                              | Description | Notes      |
| ---------------------- | ------------------------------------------------- | ----------- | ---------- |
| **simulator**          | [**SimulatorVersion**](SimulatorVersion.md)       |             |
| **parca_dataset_id**   | **int**                                           |             |
| **variant_config**     | **Dict[str, Dict[str, VariantConfigValueValue]]** |             |
| **antibiotics_config** | **Dict[str, Dict[str, VariantConfigValueValue]]** |             | [optional] |

## Example

```python
from sms_api.api.client.models.antibiotic_simulation_request import AntibioticSimulationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of AntibioticSimulationRequest from a JSON string
antibiotic_simulation_request_instance = AntibioticSimulationRequest.from_json(json)
# print the JSON string representation of the object
print(AntibioticSimulationRequest.to_json())

# convert the object into a dict
antibiotic_simulation_request_dict = antibiotic_simulation_request_instance.to_dict()
# create an instance of AntibioticSimulationRequest from a dict
antibiotic_simulation_request_from_dict = AntibioticSimulationRequest.from_dict(antibiotic_simulation_request_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
