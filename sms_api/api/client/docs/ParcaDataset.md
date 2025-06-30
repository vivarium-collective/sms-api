# ParcaDataset


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**database_id** | **int** |  | 
**parca_dataset_request** | [**ParcaDatasetRequest**](ParcaDatasetRequest.md) |  | 
**remote_archive_path** | **str** |  | [optional] 
**hpc_run** | [**HpcRun**](HpcRun.md) |  | [optional] 

## Example

```python
from sms_api.api.client.models.parca_dataset import ParcaDataset

# TODO update the JSON string below
json = "{}"
# create an instance of ParcaDataset from a JSON string
parca_dataset_instance = ParcaDataset.from_json(json)
# print the JSON string representation of the object
print(ParcaDataset.to_json())

# convert the object into a dict
parca_dataset_dict = parca_dataset_instance.to_dict()
# create an instance of ParcaDataset from a dict
parca_dataset_from_dict = ParcaDataset.from_dict(parca_dataset_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


