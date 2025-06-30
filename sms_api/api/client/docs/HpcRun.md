# HpcRun


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**database_id** | **int** |  | 
**slurmjobid** | **int** |  | [optional] 
**status** | [**JobStatus**](JobStatus.md) |  | [optional] 
**start_time** | **str** |  | [optional] 
**end_time** | **str** |  | [optional] 
**error_message** | **str** |  | [optional] 

## Example

```python
from sms_api.api.client.models.hpc_run import HpcRun

# TODO update the JSON string below
json = "{}"
# create an instance of HpcRun from a JSON string
hpc_run_instance = HpcRun.from_json(json)
# print the JSON string representation of the object
print(HpcRun.to_json())

# convert the object into a dict
hpc_run_dict = hpc_run_instance.to_dict()
# create an instance of HpcRun from a dict
hpc_run_from_dict = HpcRun.from_dict(hpc_run_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


