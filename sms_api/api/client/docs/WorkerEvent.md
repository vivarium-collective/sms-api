# WorkerEvent

## Properties

| Name                | Type                   | Description | Notes      |
| ------------------- | ---------------------- | ----------- | ---------- |
| **database_id**     | **int**                |             | [optional] |
| **created_at**      | **str**                |             | [optional] |
| **hpcrun_id**       | **int**                |             |
| **sequence_number** | **int**                |             |
| **sim_data**        | **List[List[object]]** |             |
| **global_time**     | **float**              |             | [optional] |
| **error_message**   | **str**                |             | [optional] |

## Example

```python
from sms_api.api.client.models.worker_event import WorkerEvent

# TODO update the JSON string below
json = "{}"
# create an instance of WorkerEvent from a JSON string
worker_event_instance = WorkerEvent.from_json(json)
# print the JSON string representation of the object
print(WorkerEvent.to_json())

# convert the object into a dict
worker_event_dict = worker_event_instance.to_dict()
# create an instance of WorkerEvent from a dict
worker_event_from_dict = WorkerEvent.from_dict(worker_event_dict)
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
