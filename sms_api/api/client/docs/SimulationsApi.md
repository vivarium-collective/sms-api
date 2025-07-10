# sms_api.api.client.SimulationsApi

All URIs are relative to _http://localhost_

| Method                                                                                         | HTTP request                             | Description                                                                 |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------- |
| [**get_antibiotics_simulator_versions**](SimulationsApi.md#get_antibiotics_simulator_versions) | **GET** /antibiotic/simulation/run       | Run Antibiotics                                                             |
| [**get_parca_versions**](SimulationsApi.md#get_parca_versions)                                 | **POST** /core/simulation/parca/versions | Run a parameter calculation                                                 |
| [**get_simulation_results**](SimulationsApi.md#get_simulation_results)                         | **POST** /core/simulation/results        | Get Results                                                                 |
| [**get_simulation_status**](SimulationsApi.md#get_simulation_status)                           | **GET** /core/simulation/status          | Get Simulation Status                                                       |
| [**run_parca**](SimulationsApi.md#run_parca)                                                   | **POST** /core/simulation/parca          | Run a parameter calculation                                                 |
| [**run_simulation**](SimulationsApi.md#run_simulation)                                         | **POST** /core/simulation/run            | Run Vecoli Simulation                                                       |
| [**submit_simulation**](SimulationsApi.md#submit_simulation)                                   | **POST** /core/simulation/submit         | Submit to the db a single vEcoli simulation with given parameter overrides. |

# **get_antibiotics_simulator_versions**

> EcoliExperiment get_antibiotics_simulator_versions(ecoli_simulation_request)

Run Antibiotics

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.ecoli_experiment import EcoliExperiment
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
        # Run Antibiotics
        api_response = api_instance.get_antibiotics_simulator_versions(ecoli_simulation_request)
        print("The response of SimulationsApi->get_antibiotics_simulator_versions:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->get_antibiotics_simulator_versions: %s\n" % e)
```

### Parameters

| Name                         | Type                                                    | Description | Notes |
| ---------------------------- | ------------------------------------------------------- | ----------- | ----- |
| **ecoli_simulation_request** | [**EcoliSimulationRequest**](EcoliSimulationRequest.md) |             |

### Return type

[**EcoliExperiment**](EcoliExperiment.md)

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

# **get_parca_versions**

> ParcaDataset get_parca_versions()

Run a parameter calculation

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.parca_dataset import ParcaDataset
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
        # Run a parameter calculation
        api_response = api_instance.get_parca_versions()
        print("The response of SimulationsApi->get_parca_versions:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->get_parca_versions: %s\n" % e)
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**ParcaDataset**](ParcaDataset.md)

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

# **get_simulation_results**

> object get_simulation_results(database_id, body_get_simulation_results, experiment_id=experiment_id, git_commit_hash=git_commit_hash)

Get Results

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.body_get_simulation_results import BodyGetSimulationResults
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
    body_get_simulation_results = sms_api.api.client.BodyGetSimulationResults() # BodyGetSimulationResults |
    experiment_id = 'experiment_96bb7a2_id_1_20250620-181422' # str |  (optional) (default to 'experiment_96bb7a2_id_1_20250620-181422')
    git_commit_hash = '2bcedc4' # str |  (optional) (default to '2bcedc4')

    try:
        # Get Results
        api_response = api_instance.get_simulation_results(database_id, body_get_simulation_results, experiment_id=experiment_id, git_commit_hash=git_commit_hash)
        print("The response of SimulationsApi->get_simulation_results:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->get_simulation_results: %s\n" % e)
```

### Parameters

| Name                            | Type                                                        | Description                                  | Notes                                                                     |
| ------------------------------- | ----------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------- |
| **database_id**                 | **int**                                                     | Database Id returned from /submit-simulation |
| **body_get_simulation_results** | [**BodyGetSimulationResults**](BodyGetSimulationResults.md) |                                              |
| **experiment_id**               | **str**                                                     |                                              | [optional] [default to &#39;experiment_96bb7a2_id_1_20250620-181422&#39;] |
| **git_commit_hash**             | **str**                                                     |                                              | [optional] [default to &#39;2bcedc4&#39;]                                 |

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

# **get_simulation_status**

> WorkerEvent get_simulation_status(simulation_id, num_events=num_events)

Get Simulation Status

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.worker_event import WorkerEvent
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
    simulation_id = 56 # int |
    num_events = 56 # int |  (optional)

    try:
        # Get Simulation Status
        api_response = api_instance.get_simulation_status(simulation_id, num_events=num_events)
        print("The response of SimulationsApi->get_simulation_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->get_simulation_status: %s\n" % e)
```

### Parameters

| Name              | Type    | Description | Notes      |
| ----------------- | ------- | ----------- | ---------- |
| **simulation_id** | **int** |             |
| **num_events**    | **int** |             | [optional] |

### Return type

[**WorkerEvent**](WorkerEvent.md)

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

# **run_parca**

> ParcaDataset run_parca(parca_dataset_request)

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
        api_response = api_instance.run_parca(parca_dataset_request)
        print("The response of SimulationsApi->run_parca:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulationsApi->run_parca: %s\n" % e)
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

# **run_simulation**

> EcoliExperiment run_simulation(ecoli_simulation_request)

Run Vecoli Simulation

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.ecoli_experiment import EcoliExperiment
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
        # Run Vecoli Simulation
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

[**EcoliExperiment**](EcoliExperiment.md)

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
