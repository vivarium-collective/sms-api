# EcoliExperiment

## Properties

| Name              | Type                            | Description | Notes      |
| ----------------- | ------------------------------- | ----------- | ---------- |
| **experiment_id** | **str**                         |             |
| **simulation**    | [**Simulation**](Simulation.md) |             |
| **last_updated**  | **str**                         |             | [optional] |
| **metadata**      | **Dict[str, str]**              |             | [optional] |

## Example

```python
from sms_api.api.client.models.ecoli_experiment import EcoliExperiment

# TODO update the JSON string below
json = "{}"
# create an instance of EcoliExperiment from a JSON string
ecoli_experiment_instance = EcoliExperiment.from_json(json)
# print the JSON string representation of the object
print(EcoliExperiment.to_json())

# convert the object into a dict
ecoli_experiment_dict = ecoli_experiment_instance.to_dict()
# create an instance of EcoliExperiment from a dict
ecoli_experiment_from_dict = EcoliExperiment.from_dict(ecoli_experiment_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
