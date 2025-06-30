# EcoliSimulationRun


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**job_id** | **int** |  | 
**simulation** | [**EcoliSimulation**](EcoliSimulation.md) |  | 
**last_update** | **str** |  | [optional] 

## Example

```python
from sms_api.api.client.models.ecoli_simulation_run import EcoliSimulationRun

# TODO update the JSON string below
json = "{}"
# create an instance of EcoliSimulationRun from a JSON string
ecoli_simulation_run_instance = EcoliSimulationRun.from_json(json)
# print the JSON string representation of the object
print(EcoliSimulationRun.to_json())

# convert the object into a dict
ecoli_simulation_run_dict = ecoli_simulation_run_instance.to_dict()
# create an instance of EcoliSimulationRun from a dict
ecoli_simulation_run_from_dict = EcoliSimulationRun.from_dict(ecoli_simulation_run_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


