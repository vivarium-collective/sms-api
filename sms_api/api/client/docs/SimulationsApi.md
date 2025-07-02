# sms_api.api.client.SimulationsApi

All URIs are relative to _http://localhost_

| Method                                                                     | HTTP request                | Description                                                                 |
| -------------------------------------------------------------------------- | --------------------------- | --------------------------------------------------------------------------- |
| [**calculate_parameters**](SimulationsApi.md#calculate_parameters)         | **POST** /vecoli_parca      | Run a parameter calculation                                                 |
| [**get_results**](SimulationsApi.md#get_results)                           | **GET** /get-results        | Get Results                                                                 |
| [**get_simulator_version**](SimulationsApi.md#get_simulator_version)       | **GET** /simulator_version  | get the list of available simulator versions                                |
| [**insert_simulator_version**](SimulationsApi.md#insert_simulator_version) | **POST** /simulator_version | Upload a new simulator (vEcoli) version.                                    |
| [**run_simulation**](SimulationsApi.md#run_simulation)                     | **POST** /run-simulation    | Run a single vEcoli simulation with given parameter overrides               |
| [**submit_simulation**](SimulationsApi.md#submit_simulation)               | **POST** /vecoli_simulation | Submit to the db a single vEcoli simulation with given parameter overrides. |

# **calculate_parameters**

> ParcaDataset calculate_parameters(parca_dataset_request)

Run a parameter calculation

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.parca_dataset import ParcaDataset
from sms_api.api.client.models.parca_dataset_request import ParcaDatasetRequest
from sms_api.api.client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = sms_api.api.client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with sms_api.api.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = sms_api.api.client.SimulationsApi(api_client)
    parca_dataset_request = sms_api.api.client.ParcaDatasetRequest() # ParcaDatasetRequest |

    try:
        # Run a parameter calculation
        api_response = api_instance.calculate_parameters(parca_dataset_request)
        print("The response of SimulationsApi->calculate_parameters:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->calculate_parameters: %s\n" % e)
```

### Parameters

| Name                      | Type                                              | Description | Notes |
| ------------------------- | ------------------------------------------------- | ----------- | ----- |
| **parca_dataset_request** | [**ParcaDatasetRequest**](ParcaDatasetRequest.md) |             |

### Return type

[**ParcaDataset**](ParcaDataset.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

### HTTP response details

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |
| **422**     | Validation Error    | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_results**

> object get_results(database_id, git_commit_hash=git_commit_hash, settings=settings)

Get Results

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.settings import Settings
from sms_api.api.client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = sms_api.api.client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with sms_api.api.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = sms_api.api.client.SimulationsApi(api_client)
    database_id = 56 # int | Database Id returned from /submit-simulation
    git_commit_hash = 'd24e988' # str |  (optional) (default to 'd24e988')
    settings = sms_api.api.client.Settings() # Settings |  (optional)

    try:
        # Get Results
        api_response = api_instance.get_results(database_id, git_commit_hash=git_commit_hash, settings=settings)
        print("The response of SimulationsApi->get_results:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->get_results: %s\n" % e)
```

### Parameters

| Name                | Type                        | Description                                  | Notes                                     |
| ------------------- | --------------------------- | -------------------------------------------- | ----------------------------------------- |
| **database_id**     | **int**                     | Database Id returned from /submit-simulation |
| **git_commit_hash** | **str**                     |                                              | [optional] [default to &#39;d24e988&#39;] |
| **settings**        | [**Settings**](Settings.md) |                                              | [optional]                                |

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

### HTTP response details

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |
| **422**     | Validation Error    | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_simulator_version**

> List[SimulatorVersion] get_simulator_version()

get the list of available simulator versions

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.simulator_version import SimulatorVersion
from sms_api.api.client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = sms_api.api.client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with sms_api.api.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = sms_api.api.client.SimulationsApi(api_client)

    try:
        # get the list of available simulator versions
        api_response = api_instance.get_simulator_version()
        print("The response of SimulationsApi->get_simulator_version:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->get_simulator_version: %s\n" % e)
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**List[SimulatorVersion]**](SimulatorVersion.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

### HTTP response details

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **insert_simulator_version**

> SimulatorVersion insert_simulator_version(git_commit_hash=git_commit_hash, git_repo_url=git_repo_url, git_branch=git_branch)

Upload a new simulator (vEcoli) version.

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.simulator_version import SimulatorVersion
from sms_api.api.client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = sms_api.api.client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with sms_api.api.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = sms_api.api.client.SimulationsApi(api_client)
    git_commit_hash = 'git_commit_hash_example' # str | First 7 characters of git commit hash (optional)
    git_repo_url = 'https://github.com/CovertLab/vEcoli' # str |  (optional) (default to 'https://github.com/CovertLab/vEcoli')
    git_branch = 'master' # str |  (optional) (default to 'master')

    try:
        # Upload a new simulator (vEcoli) version.
        api_response = api_instance.insert_simulator_version(git_commit_hash=git_commit_hash, git_repo_url=git_repo_url, git_branch=git_branch)
        print("The response of SimulationsApi->insert_simulator_version:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->insert_simulator_version: %s\n" % e)
```

### Parameters

| Name                | Type    | Description                           | Notes                                                                 |
| ------------------- | ------- | ------------------------------------- | --------------------------------------------------------------------- |
| **git_commit_hash** | **str** | First 7 characters of git commit hash | [optional]                                                            |
| **git_repo_url**    | **str** |                                       | [optional] [default to &#39;https://github.com/CovertLab/vEcoli&#39;] |
| **git_branch**      | **str** |                                       | [optional] [default to &#39;master&#39;]                              |

### Return type

[**SimulatorVersion**](SimulatorVersion.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

### HTTP response details

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |
| **422**     | Validation Error    | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **run_simulation**

> EcoliSimulationRun run_simulation(ecoli_simulation_request)

Run a single vEcoli simulation with given parameter overrides

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.ecoli_simulation_request import EcoliSimulationRequest
from sms_api.api.client.models.ecoli_simulation_run import EcoliSimulationRun
from sms_api.api.client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = sms_api.api.client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with sms_api.api.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = sms_api.api.client.SimulationsApi(api_client)
    ecoli_simulation_request = sms_api.api.client.EcoliSimulationRequest() # EcoliSimulationRequest |

    try:
        # Run a single vEcoli simulation with given parameter overrides
        api_response = api_instance.run_simulation(ecoli_simulation_request)
        print("The response of SimulationsApi->run_simulation:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->run_simulation: %s\n" % e)
```

### Parameters

| Name                         | Type                                                    | Description | Notes |
| ---------------------------- | ------------------------------------------------------- | ----------- | ----- |
| **ecoli_simulation_request** | [**EcoliSimulationRequest**](EcoliSimulationRequest.md) |             |

### Return type

[**EcoliSimulationRun**](EcoliSimulationRun.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

### HTTP response details

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |
| **422**     | Validation Error    | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **submit_simulation**

> EcoliSimulation submit_simulation(ecoli_simulation_request)

Submit to the db a single vEcoli simulation with given parameter overrides.

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.ecoli_simulation import EcoliSimulation
from sms_api.api.client.models.ecoli_simulation_request import EcoliSimulationRequest
from sms_api.api.client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = sms_api.api.client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with sms_api.api.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = sms_api.api.client.SimulationsApi(api_client)
    ecoli_simulation_request = sms_api.api.client.EcoliSimulationRequest() # EcoliSimulationRequest |

    try:
        # Submit to the db a single vEcoli simulation with given parameter overrides.
        api_response = api_instance.submit_simulation(ecoli_simulation_request)
        print("The response of SimulationsApi->submit_simulation:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->submit_simulation: %s\n" % e)
```

### Parameters

| Name                         | Type                                                    | Description | Notes |
| ---------------------------- | ------------------------------------------------------- | ----------- | ----- |
| **ecoli_simulation_request** | [**EcoliSimulationRequest**](EcoliSimulationRequest.md) |             |

### Return type

[**EcoliSimulation**](EcoliSimulation.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

### HTTP response details

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |
| **422**     | Validation Error    | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
