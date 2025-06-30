# Settings


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**storage_bucket** | **str** |  | [optional] [default to 'files.biosimulations.dev']
**storage_endpoint_url** | **str** |  | [optional] [default to 'https://storage.googleapis.com']
**storage_region** | **str** |  | [optional] [default to 'us-east4']
**storage_tensorstore_driver** | **str** |  | [optional] [default to 'zarr3']
**storage_tensorstore_kvstore_driver** | **str** |  | [optional] [default to 'gcs']
**temporal_service_url** | **str** |  | [optional] [default to 'localhost:7233']
**storage_local_cache_dir** | **str** |  | [optional] [default to './local_cache']
**storage_gcs_credentials_file** | **str** |  | [optional] [default to '']
**mongodb_uri** | **str** |  | [optional] [default to 'mongodb://localhost:27017']
**mongodb_database** | **str** |  | [optional] [default to 'biosimulations']
**mongodb_collection_omex** | **str** |  | [optional] [default to 'BiosimOmex']
**mongodb_collection_sims** | **str** |  | [optional] [default to 'BiosimSims']
**mongodb_collection_compare** | **str** |  | [optional] [default to 'BiosimCompare']
**postgres_user** | **str** |  | [optional] [default to '<USER>']
**postgres_password** | **str** |  | [optional] [default to '<PASSWORD>']
**postgres_database** | **str** |  | [optional] [default to 'sms']
**postgres_host** | **str** |  | [optional] [default to 'localhost']
**postgres_port** | **int** |  | [optional] [default to 5432]
**postgres_pool_size** | **int** |  | [optional] [default to 10]
**postgres_max_overflow** | **int** |  | [optional] [default to 5]
**postgres_pool_timeout** | **int** |  | [optional] [default to 30]
**postgres_pool_recycle** | **int** |  | [optional] [default to 1800]
**slurm_submit_host** | **str** |  | [optional] [default to '']
**slurm_submit_user** | **str** |  | [optional] [default to '']
**slurm_submit_key_path** | **str** |  | [optional] [default to '']
**slurm_partition** | **str** |  | [optional] [default to '']
**slurm_node_list** | **str** |  | [optional] [default to '']
**slurm_qos** | **str** |  | [optional] [default to '']
**slurm_log_base_path** | **str** |  | [optional] [default to '']
**hpc_image_base_path** | **str** |  | [optional] [default to '']
**hpc_parca_base_path** | **str** |  | [optional] [default to '']
**hpc_repo_base_path** | **str** |  | [optional] [default to '']
**hpc_sim_base_path** | **str** |  | [optional] [default to '']

## Example

```python
from sms_api.api.client.models.settings import Settings

# TODO update the JSON string below
json = "{}"
# create an instance of Settings from a JSON string
settings_instance = Settings.from_json(json)
# print the JSON string representation of the object
print(Settings.to_json())

# convert the object into a dict
settings_dict = settings_instance.to_dict()
# create an instance of Settings from a dict
settings_from_dict = Settings.from_dict(settings_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


