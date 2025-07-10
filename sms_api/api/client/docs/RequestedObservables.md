# RequestedObservables

## Properties

| Name      | Type          | Description | Notes      |
| --------- | ------------- | ----------- | ---------- |
| **items** | **List[str]** |             | [optional] |

## Example

```python
from sms_api.api.client.models.requested_observables import RequestedObservables

# TODO update the JSON string below
json = "{}"
# create an instance of RequestedObservables from a JSON string
requested_observables_instance = RequestedObservables.from_json(json)
# print the JSON string representation of the object
print(RequestedObservables.to_json())

# convert the object into a dict
requested_observables_dict = requested_observables_instance.to_dict()
# create an instance of RequestedObservables from a dict
requested_observables_from_dict = RequestedObservables.from_dict(requested_observables_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
