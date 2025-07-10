# sms_api.api.client.SimulatorsApi

All URIs are relative to _http://localhost_

| Method                                                                              | HTTP request                     | Description                                  |
| ----------------------------------------------------------------------------------- | -------------------------------- | -------------------------------------------- |
| [**get_core_simulator_version**](SimulatorsApi.md#get_core_simulator_version)       | **GET** /core/simulator/versions | get the list of available simulator versions |
| [**insert_core_simulator_version**](SimulatorsApi.md#insert_core_simulator_version) | **POST** /core/simulator/upload  | Upload a new simulator (vEcoli) version.     |
| [**latest_simulator_hash**](SimulatorsApi.md#latest_simulator_hash)                 | **GET** /core/simulator/latest   | Get Latest Simulator                         |

# **get_core_simulator_version**

> RegisteredSimulators get_core_simulator_version()

get the list of available simulator versions

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.registered_simulators import RegisteredSimulators
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
    api_instance = sms_api.api.client.SimulatorsApi(api_client)

    try:
        # get the list of available simulator versions
        api_response = api_instance.get_core_simulator_version()
        print("The response of SimulatorsApi->get_core_simulator_version:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulatorsApi->get_core_simulator_version: %s\n" % e)
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**RegisteredSimulators**](RegisteredSimulators.md)

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

# **insert_core_simulator_version**

> SimulatorVersion insert_core_simulator_version(simulator)

Upload a new simulator (vEcoli) version.

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.simulator import Simulator
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
    api_instance = sms_api.api.client.SimulatorsApi(api_client)
    simulator = sms_api.api.client.Simulator() # Simulator |

    try:
        # Upload a new simulator (vEcoli) version.
        api_response = api_instance.insert_core_simulator_version(simulator)
        print("The response of SimulatorsApi->insert_core_simulator_version:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulatorsApi->insert_core_simulator_version: %s\n" % e)
```

### Parameters

| Name          | Type                          | Description | Notes |
| ------------- | ----------------------------- | ----------- | ----- |
| **simulator** | [**Simulator**](Simulator.md) |             |

### Return type

[**SimulatorVersion**](SimulatorVersion.md)

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

# **latest_simulator_hash**

> Simulator latest_simulator_hash(git_repo_url=git_repo_url, git_branch=git_branch)

Get Latest Simulator

### Example

```python
import sms_api.api.client
from sms_api.api.client.models.simulator import Simulator
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
    api_instance = sms_api.api.client.SimulatorsApi(api_client)
    git_repo_url = 'https://github.com/vivarium-collective/vEcoli' # str |  (optional) (default to 'https://github.com/vivarium-collective/vEcoli')
    git_branch = 'messages' # str |  (optional) (default to 'messages')

    try:
        # Get Latest Simulator
        api_response = api_instance.latest_simulator_hash(git_repo_url=git_repo_url, git_branch=git_branch)
        print("The response of SimulatorsApi->latest_simulator_hash:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SimulatorsApi->latest_simulator_hash: %s\n" % e)
```

### Parameters

| Name             | Type    | Description | Notes                                                                           |
| ---------------- | ------- | ----------- | ------------------------------------------------------------------------------- |
| **git_repo_url** | **str** |             | [optional] [default to &#39;https://github.com/vivarium-collective/vEcoli&#39;] |
| **git_branch**   | **str** |             | [optional] [default to &#39;messages&#39;]                                      |

### Return type

[**Simulator**](Simulator.md)

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
