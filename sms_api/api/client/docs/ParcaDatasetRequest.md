# ParcaDatasetRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**simulator_version** | [**SimulatorVersion**](SimulatorVersion.md) |  | 
**parca_config** | [**Dict[str, VariantConfigValueValue]**](VariantConfigValueValue.md) |  | 

## Example

```python
from sms_api.api.client.models.parca_dataset_request import ParcaDatasetRequest

# TODO update the JSON string below
json = "{}"
# create an instance of ParcaDatasetRequest from a JSON string
parca_dataset_request_instance = ParcaDatasetRequest.from_json(json)
# print the JSON string representation of the object
print(ParcaDatasetRequest.to_json())

# convert the object into a dict
parca_dataset_request_dict = parca_dataset_request_instance.to_dict()
# create an instance of ParcaDatasetRequest from a dict
parca_dataset_request_from_dict = ParcaDatasetRequest.from_dict(parca_dataset_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


